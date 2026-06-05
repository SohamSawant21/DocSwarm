import os
import zipfile
import tempfile
import re
import asyncio
import networkx as nx
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini Client
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

# --- RAG UTILITIES ---

class CodeChunk:
    def __init__(self, file_path: str, content: str, start_line: int, end_line: int):
        self.file_path = file_path
        self.content = content
        self.start_line = start_line
        self.end_line = end_line

class LocalSearchIndex:
    def __init__(self):
        self.chunks: List[CodeChunk] = []
        self.vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
        self.tfidf_matrix = None

    def add_chunks(self, chunks: List[CodeChunk]):
        self.chunks = chunks
        if not chunks:
            return
        
        # Combine file path and content for better context matching
        corpus = [f"FILE: {c.file_path}\n{c.content}" for c in chunks]
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 5) -> List[CodeChunk]:
        if not self.chunks or self.tfidf_matrix is None:
            return []
        
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        # Return chunks with similarity > 0
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                results.append(self.chunks[idx])
        return results

def chunk_file(file_path: str, content: str, chunk_size: int = 50, overlap: int = 10) -> List[CodeChunk]:
    lines = content.splitlines()
    chunks = []
    
    if len(lines) <= chunk_size:
        chunks.append(CodeChunk(file_path, content, 1, len(lines)))
        return chunks

    start = 0
    while start < len(lines):
        end = min(start + chunk_size, len(lines))
        chunk_content = "\n".join(lines[start:end])
        chunks.append(CodeChunk(file_path, chunk_content, start + 1, end))
        start += (chunk_size - overlap)
        
    return chunks

# In-memory storage for the latest uploaded repository context
repo_context = {
    "files": {},
    "graph": None,
    "search_index": LocalSearchIndex(),
    "repo_map": "",
    "intelligence_summary": ""
}

class ChatRequest(BaseModel):
    message: str
    context: Dict[str, Any] = {}

app = FastAPI(title="DocSwarm GraphOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def generate_intelligence_report(files_data: Dict[str, Any], repo_map: str) -> str:
    """
    Generates a structured Evidence-Based Engineering Review during the upload phase.
    """
    if not client:
        return "Intelligence report generation skipped: Gemini API key missing."

    # 1. Identify Critical Files for Context
    critical_files = {}
    priority_patterns = [
        'readme.md', 'package.json', 'requirements.txt', 'main.py', 
        'index.js', 'app.tsx', 'next.config', 'tsconfig.json', 'dockerfile'
    ]
    
    for path, data in files_data.items():
        name = os.path.basename(path).lower()
        if any(p in name for p in priority_patterns):
            # Limit content to first 3000 chars per critical file to control tokens
            critical_files[path] = data['content'][:3000]

    # 2. Prepare the prompt for the "Architect's Pass"
    analysis_prompt = f"""You are a Senior Principal Software Architect performing a deep-dive analysis of a repository.
    
### INPUT DATA
1. REPOSITORY BLUEPRINT (Structure & Dependencies):
{repo_map}

2. CRITICAL FILE CONTENTS:
{chr(10).join([f"--- FILE: {p} ---\n{c}\n" for p, c in critical_files.items()])}

### TASK
Generate a concise, structured 'Evidence-Based Engineering Review' (500-1500 words).
Focus ONLY on facts supported by the provided data.

### REQUIRED SECTIONS
1. TECHNOLOGY STACK: List languages, frameworks, and versions.
2. MAJOR COMPONENTS: Identify the core modules and their responsibilities.
3. DATA FLOW: Trace the lifecycle of data (e.g., UI -> API -> Logic).
4. ARCHITECTURAL PATTERNS: Classify the design (e.g., Monolith, Client-Server, RAG).
5. EVIDENCE-BASED STRENGTHS: List what is well-implemented (cite files).
6. EVIDENCE-BASED RISKS: Identify specific technical risks (cite files and explain evidence).
7. IMPROVEMENT OPPORTUNITIES: Suggest specific refactors (cite files and provide rationale).

### CONSTRAINTS
- Be extremely specific. Use file names and code patterns.
- Avoid generic praise or criticism.
- If you cite a risk, you MUST explain the evidence (e.g., "File X uses global state which prevents Y").
"""

    try:
        # Use a slightly higher temperature (0.2) for creative architectural synthesis
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[analysis_prompt],
            config=types.GenerateContentConfig(
                system_instruction="You are an expert software reviewer. Provide a high-density, evidence-based technical report.",
                temperature=0.2,
            )
        )
        return response.text or "Failed to generate report."
    except Exception as e:
        print(f"Intelligence Generation Error: {str(e)}")
        return f"Error generating intelligence report: {str(e)}"

def classify_role(file_path: str, content: str) -> str:
    path_lower = file_path.lower()
    name = os.path.basename(path_lower)
    
    if name in ['main.py', 'index.js', 'app.tsx', 'app.ts', 'server.js']:
        return "Entry Points"
    if any(k in path_lower for k in ['route', 'api', 'endpoint', 'controller']):
        return "Routing & Controllers"
    if any(k in path_lower for k in ['model', 'schema', 'db', 'database', 'entity']):
        return "Data Models & Persistence"
    if any(k in path_lower for k in ['service', 'logic', 'manager', 'util', 'helper']):
        return "Services & Utilities"
    if any(k in path_lower for k in ['component', 'ui', 'view', 'page', 'screen']):
        return "UI Components"
    if name.endswith(('.json', '.yaml', '.yml', '.env', 'config.js', 'config.ts', 'requirements.txt')):
        return "Configuration"
    if name.endswith(('.md', '.txt')):
        return "Documentation"
    return "Other"

def generate_repo_map(files_data: Dict[str, Any], G: nx.DiGraph) -> str:
    blueprint = "### REPOSITORY ARCHITECTURE BLUEPRINT\n\n"
    
    # 1. Project Overview (Search for README)
    overview = "No README found."
    for path, data in files_data.items():
        if path.lower() == 'readme.md':
            content = data['content']
            # Take first 500 chars as summary
            overview = content[:500] + ("..." if len(content) > 500 else "")
            break
    blueprint += f"#### 1. PROJECT OVERVIEW\n{overview}\n\n"
    
    # 2. Architectural Roles
    roles = {
        "Entry Points": [],
        "Routing & Controllers": [],
        "Data Models & Persistence": [],
        "Services & Utilities": [],
        "UI Components": [],
        "Configuration": [],
        "Documentation": []
    }
    
    for path, data in files_data.items():
        role = classify_role(path, data['content'])
        if role in roles:
            roles[role].append(path)
            
    blueprint += "#### 2. ARCHITECTURAL ROLES\n"
    for role, paths in roles.items():
        if paths:
            file_list = ", ".join(paths[:10]) + ("..." if len(paths) > 10 else "")
            blueprint += f"- **{role}**: {file_list}\n"
    blueprint += "\n"
    
    # 3. Logical Dependency Graph (Top Relationships)
    blueprint += "#### 3. LOGICAL DEPENDENCY GRAPH (TOP RELATIONSHIPS)\n"
    edges = list(G.edges())
    for u, v in edges[:20]:
        blueprint += f"- `{u}` --> depends on --> `{v}`\n"
    if len(edges) > 20:
        blueprint += f"- ... (total {len(edges)} relationships)\n"
    blueprint += "\n"
    
    # 4. Directory Tree
    blueprint += "#### 4. DIRECTORY TREE\n"
    dirs = set()
    for path in files_data.keys():
        parts = path.split('/')
        if len(parts) > 1:
            dirs.add(f"- {parts[0]}/")
            if len(parts) > 2:
                dirs.add(f"  - {parts[0]}/{parts[1]}/")
    blueprint += "\n".join(sorted(list(dirs))[:30])
    
    return blueprint

def detect_architectural_intent(query: str) -> bool:
    arch_keywords = {
        "architecture", "structure", "design", "flow", "work", "explain", 
        "summarize", "overview", "project", "how does", "alternative", 
        "improvement", "weakness", "pattern", "layout", "purpose"
    }
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in arch_keywords)

def parse_js_ts(file_content: str):
    imports = []
    import_pattern = re.compile(r'(?:import|export)\s+.*?\s+from\s+[\'"](.*?)[\'"]', re.MULTILINE | re.DOTALL)
    dynamic_pattern = re.compile(r'(?:require|import)\([\'"](.*?)[\'"]\)', re.MULTILINE)
    
    for match in import_pattern.findall(file_content):
        imports.append(match)
    for match in dynamic_pattern.findall(file_content):
        imports.append(match)
        
    return imports

def parse_python(file_content: str):
    import ast
    imports = []
    try:
        tree = ast.parse(file_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except Exception:
        pass
    return imports

def analyze_directory(extract_dir: str):
    G = nx.DiGraph()
    files_data = {}
    all_chunks = []
    
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.md', '.txt', '.json')):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, extract_dir)
                node_id = rel_path.replace('\\', '/')
                
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Chunking for RAG
                file_chunks = chunk_file(node_id, content)
                all_chunks.extend(file_chunks)

                imports = []
                icon = "description"
                if file.endswith('.py'):
                    imports = parse_python(content)
                    icon = "data_object"
                elif file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    imports = parse_js_ts(content)
                    icon = "code"
                elif file.endswith('.md'):
                    icon = "article"
                elif file.endswith('.json'):
                    icon = "settings"
                
                if "middleware" in file.lower():
                    icon = "lock"
                elif "db" in file.lower() or "store" in file.lower():
                    icon = "database"
                elif "api" in file.lower() or "route" in file.lower():
                    icon = "api"
                elif "service" in file.lower():
                    icon = "group"
                    
                files_data[node_id] = {
                    "label": file,
                    "imports": imports,
                    "icon": icon,
                    "content": content
                }
                
                G.add_node(node_id, label=file, type="customNode", icon=icon)

    # Build edges
    for node_id, data in files_data.items():
        for imp in data["imports"]:
            clean_imp = re.sub(r'^(\./|\.\./|@/)+', '', imp)
            for target_id, _ in files_data.items():
                target_id_no_ext = os.path.splitext(target_id)[0]
                if target_id_no_ext.endswith(f"/{clean_imp}") or \
                   target_id_no_ext == clean_imp or \
                   target_id_no_ext.endswith(f"/{clean_imp}/index"):
                    G.add_edge(node_id, target_id)
                    break
    
    return G, files_data, all_chunks

@app.post("/api/upload")
async def upload_repo(file: UploadFile = File(...)):
    if not file.filename.endswith('.zip'):
        return {"error": "Only .zip files are supported"}
    
    with tempfile.TemporaryDirectory() as tmpdirname:
        zip_path = os.path.join(tmpdirname, "repo.zip")
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        extract_dir = os.path.join(tmpdirname, "extracted")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        G, files_data, all_chunks = analyze_directory(extract_dir)
        
        # Generate Architectural Blueprint
        repo_map = generate_repo_map(files_data, G)

        # Generate Evidence-Based Engineering Review
        intelligence_summary = await generate_intelligence_report(files_data, repo_map)
        
        # Update global context
        repo_context["files"] = files_data
        repo_context["graph"] = G
        repo_context["search_index"].add_chunks(all_chunks)
        repo_context["repo_map"] = repo_map
        repo_context["intelligence_summary"] = intelligence_summary
        
        try:
            pos = nx.spring_layout(G, scale=400)
        except Exception:
            pos = {}
            
        rf_nodes = []
        for node, data in G.nodes(data=True):
            p = pos.get(node, [0,0])
            rf_nodes.append({
                "id": node,
                "position": {"x": int(p[0]) + 400, "y": int(p[1]) + 300},
                "data": {"label": data.get("label", node), "icon": data.get("icon", "description")},
                "type": "customNode"
            })
            
        rf_edges = []
        for idx, (u, v) in enumerate(G.edges()):
            rf_edges.append({
                "id": f"e{idx}",
                "source": u,
                "target": v,
                "animated": True
            })
            
        return {
            "message": "Upload successful",
            "graph": {
                "nodes": rf_nodes,
                "edges": rf_edges,
            },
            "files": files_data
        }

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception)
)
def call_gemini(model_name: str, contents: list, system_instruction: str):
    return client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
        )
    )

@app.post("/api/chat")
async def chat_with_repo(request: ChatRequest):
    if not client:
        return {"reply": "Error: Gemini API key is missing. Please check your .env file."}
    
    if not repo_context["files"]:
        return {"reply": "Please upload a repository first so I can analyze it and answer your questions."}

    # 1. Intent Detection
    is_architectural = detect_architectural_intent(request.message)
    
    # 2. RAG: Retrieve relevant chunks
    # We increase top_k for architectural questions to give more breadth
    top_k = 12 if is_architectural else 8
    relevant_chunks = repo_context["search_index"].search(request.message, top_k=top_k)
    
    # 3. Build Context
    context_str = ""
    
    # Inject Repository Blueprint
    if repo_context["repo_map"]:
        context_str += f"{repo_context['repo_map']}\n\n"

    # Inject Evidence-Based Engineering Review
    if repo_context["intelligence_summary"]:
        context_str += "### EVIDENCE-BASED ENGINEERING REVIEW\n"
        context_str += f"{repo_context['intelligence_summary']}\n\n"
    
    if not relevant_chunks:
        # Fallback to some generic info if search returns nothing but we have files
        context_str += "CODE SNIPPETS: No direct matches found, but here is a list of available files:\n"
        context_str += "\n".join(list(repo_context["files"].keys())[:20])
    else:
        context_str += "CODE SNIPPETS: Here are the relevant snippets from the repository.\n\n"
        for chunk in relevant_chunks:
            context_str += f"--- FILE: {chunk.file_path} (Lines {chunk.start_line}-{chunk.end_line}) ---\n{chunk.content}\n\n"

    if is_architectural:
        context_str += "\nNOTE: The user is asking a structural or architectural question. Prioritize the REPOSITORY ARCHITECTURE BLUEPRINT and ENGINEERING REVIEW above for your reasoning.\n"

    system_instruction = """You are DocSwarm AI, a Senior Software Architect and Repository Intelligence Assistant.
Your goal is to answer questions about the provided codebase using the provided context.

### YOUR KNOWLEDGE SOURCE
You have three primary sources of truth in the CONTEXT:
1. REPOSITORY ARCHITECTURE BLUEPRINT: Use this for mapping file roles and dependencies.
2. EVIDENCE-BASED ENGINEERING REVIEW: Use this for high-level questions about project purpose, tech stack, data flow, architectural patterns, and identifying strengths/risks.
3. CODE SNIPPETS: Use these for specific implementation details, function lookups, and bug analysis.

### STRICT RULES:
1. Use the provided context as your EXCLUSIVE knowledge source.
2. For ARCHITECTURAL and STRATEGIC questions (overview, flow, design, risks, improvements), synthesize your answer primarily from the BLUEPRINT and ENGINEERING REVIEW.
3. For IMPLEMENTATION questions (how X works, where is Y), use the CODE SNIPPETS.
4. If the answer is not in any source, say: "I could not find that information in the uploaded documents."
5. Mention file names when referring to code or structure.
6. Keep responses factual, professional, and grounded.
7. Do NOT use general external knowledge about unrelated projects."""

    try:
        response = call_gemini(
            model_name="gemini-2.5-flash",
            contents=[context_str + f"\n\nUSER QUESTION: {request.message}"],
            system_instruction=system_instruction
        )
        
        if not response.text:
            return {"reply": "I could not find that information in the uploaded documents."}
            
        return {"reply": response.text}

    except Exception as e:
        print(f"Gemini API Error: {str(e)}")
        error_msg = str(e).lower()
        detailed_error = str(e)
        if hasattr(e, 'message'): detailed_error = e.message
        
        if "api_key" in error_msg or "401" in error_msg:
            return {"reply": f"Error: Invalid Gemini API key. ({detailed_error})"}
        elif "quota" in error_msg or "429" in error_msg:
            return {"reply": f"Error: Gemini API quota exceeded or high demand. Please wait a moment and try again. ({detailed_error})"}
        elif "connection" in error_msg:
            return {"reply": f"Error: Failed to connect to Gemini API. ({detailed_error})"}
        else:
            return {"reply": f"Error: {type(e).__name__}: {detailed_error}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
