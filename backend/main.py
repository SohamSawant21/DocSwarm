import os
import zipfile
import tempfile
import re
import asyncio
import networkx as nx
import numpy as np
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception)
)
def get_embeddings(texts: List[str]) -> List[List[float]]:
    if not client:
        return [[0.0] * 768] * len(texts)
    response = client.models.embed_content(
        model="text-embedding-004",
        contents=texts
    )
    return [e.values for e in response.embeddings]

class LocalSearchIndex:
    def __init__(self):
        self.chunks: List[CodeChunk] = []
        self.embeddings = None

    def add_chunks(self, chunks: List[CodeChunk]):
        self.chunks = chunks
        if not chunks:
            return
        
        corpus = [f"FILE: {c.file_path}\n{c.content}" for c in chunks]
        
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(corpus), batch_size):
            batch = corpus[i:i+batch_size]
            try:
                emb = get_embeddings(batch)
                all_embeddings.extend(emb)
            except Exception as e:
                print(f"Embedding error: {e}")
                all_embeddings.extend([[0.0] * 768] * len(batch))
                
        self.embeddings = np.array(all_embeddings)

    def search(self, query: str, top_k: int = 5) -> List[CodeChunk]:
        if not self.chunks or self.embeddings is None or len(self.embeddings) == 0:
            return []
        
        try:
            query_emb = get_embeddings([query])
            query_vec = np.array(query_emb[0]).reshape(1, -1)
        except Exception as e:
            print(f"Query embedding error: {e}")
            return []
            
        similarities = cosine_similarity(query_vec, self.embeddings).flatten()
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
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

# In-memory storage for uploaded repository contexts per session
sessions: Dict[str, Dict[str, Any]] = {}

# In-memory storage for background task status
tasks: Dict[str, Any] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str
    context: Dict[str, Any] = {}

app = FastAPI(title="DocSwarm GraphOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



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

def process_file_task(task):
    node_id, filepath = task
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        file_chunks = chunk_file(node_id, content)
        
        imports = []
        if filepath.endswith('.py'):
            imports = parse_python(content)
        elif filepath.endswith(('.js', '.jsx', '.ts', '.tsx')):
            imports = parse_js_ts(content)
            
        return node_id, os.path.basename(filepath), content, file_chunks, imports
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return node_id, os.path.basename(filepath), "", [], []

def build_file_tree(file_paths: List[str]) -> List[Dict[str, Any]]:
    tree = {}

    for path in file_paths:
        parts = path.replace('\\', '/').split('/')
        current_level = tree
        
        for i, part in enumerate(parts):
            is_file = (i == len(parts) - 1)
            
            if part not in current_level:
                current_level[part] = {
                    "name": part,
                    "type": "file" if is_file else "folder",
                    "path": path if is_file else None,
                    "children": {} if not is_file else None
                }
            
            if not is_file:
                current_level = current_level[part]["children"]

    def format_tree(node_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = []
        for key, node in node_dict.items():
            formatted_node = {
                "name": node["name"],
                "type": node["type"],
            }
            if node["type"] == "file":
                formatted_node["path"] = node["path"]
            if node["type"] == "folder":
                formatted_node["children"] = format_tree(node["children"])
            result.append(formatted_node)
        
        result.sort(key=lambda x: (0 if x["type"] == "folder" else 1, x["name"].lower()))
        return result

    return format_tree(tree)

def analyze_directory(extract_dir: str):
    import concurrent.futures
    
    G = nx.DiGraph()
    files_data = {}
    all_chunks = []
    
    file_tasks = []
    
    for root, dirs, files in os.walk(extract_dir):
        # Exclude common build, environment, and system directories
        dirs[:] = [d for d in dirs if d not in {
            '.git', 'node_modules', 'venv', '.venv', 'env', '.env', 
            '__pycache__', '.next', 'dist', 'build', 'out', 'target', 
            '__MACOSX', '.idea', '.vscode'
        }]
        
        for file in files:
            # Ignore hidden files and macOS resource forks
            if file.startswith('.') or file.startswith('._'):
                continue
                
            if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx', '.md', '.txt', '.json')):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, extract_dir)
                node_id = rel_path.replace('\\', '/')
                file_tasks.append((node_id, filepath))

    # Parallelize CPU-intensive AST parsing
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(process_file_task, file_tasks)
        
    for res in results:
        node_id, label, content, file_chunks, imports = res
        all_chunks.extend(file_chunks)
        files_data[node_id] = {
            "label": label,
            "imports": imports,
            "content": content
        }
        G.add_node(node_id, label=label, type="customNode")

    # Build edges
    existing_files = set(files_data.keys())
    
    # Pre-build lookup map for O(1) fallback resolution
    suffix_map = {}
    for target_id in existing_files:
        target_id_no_ext = os.path.splitext(target_id)[0]
        parts = target_id_no_ext.split('/')
        for i in range(len(parts)):
            suffix = "/".join(parts[i:])
            if suffix not in suffix_map:
                suffix_map[suffix] = target_id
            
            if target_id_no_ext.endswith("/index") and not target_id.endswith(".py"):
                if suffix.endswith("/index"):
                    dir_suffix = suffix[:-6]
                    if dir_suffix and dir_suffix not in suffix_map:
                        suffix_map[dir_suffix] = target_id
            elif target_id_no_ext.endswith("/__init__") and target_id.endswith(".py"):
                if suffix.endswith("/__init__"):
                    dir_suffix = suffix[:-9]
                    if dir_suffix and dir_suffix not in suffix_map:
                        suffix_map[dir_suffix] = target_id

    for node_id, data in files_data.items():
        node_dir = os.path.dirname(node_id)
        is_python = node_id.endswith('.py')
        
        for imp in data["imports"]:
            resolved_targets = []
            
            if is_python:
                clean_imp = imp.replace('.', '/')
                resolved_targets.append(clean_imp)
            else:
                if imp.startswith('.'):
                    resolved_path = os.path.normpath(os.path.join(node_dir, imp)).replace('\\', '/')
                    resolved_targets.append(resolved_path)
                else:
                    clean_imp = re.sub(r'^[@~]/?', '', imp)
                    resolved_targets.append(clean_imp)
            
            found_target = None
            for target_base in resolved_targets:
                if target_base in existing_files:
                    found_target = target_base
                    break
                
                possible_paths = [
                    f"{target_base}.js", f"{target_base}.ts", 
                    f"{target_base}.jsx", f"{target_base}.tsx",
                    f"{target_base}.mjs", f"{target_base}.cjs",
                    f"{target_base}.py",
                    f"{target_base}/index.js", f"{target_base}/index.ts", 
                    f"{target_base}/index.jsx", f"{target_base}/index.tsx",
                    f"{target_base}/__init__.py"
                ]
                
                for p in possible_paths:
                    if p in existing_files:
                        found_target = p
                        break
                
                if found_target:
                    break
            
            if found_target:
                G.add_edge(node_id, found_target)
            else:
                # Optimized O(1) fallback heuristic
                if is_python:
                    clean_imp = imp.replace('.', '/')
                else:
                    clean_imp = re.sub(r'^(\./|\.\./)+', '', imp)
                    clean_imp = re.sub(r'^[@~]/?', '', clean_imp)
                    clean_imp = re.sub(r'\.(js|ts|jsx|tsx|mjs|cjs|py)$', '', clean_imp)
                
                if clean_imp in suffix_map:
                    G.add_edge(node_id, suffix_map[clean_imp])
    
    return G, files_data, all_chunks

def extract_and_analyze_zip(zip_path: str, extract_dir: str):
    MAX_EXTRACTED_SIZE = 250 * 1024 * 1024 # 250MB limit
    total_extracted_size = 0
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        if not zip_ref.infolist():
            raise ValueError("The uploaded ZIP file is empty.")
            
        for member in zip_ref.infolist():
            total_extracted_size += member.file_size
            if total_extracted_size > MAX_EXTRACTED_SIZE:
                raise ValueError("The repository is too large when extracted (exceeds 250MB). Please upload a smaller project.")
                
            target_path = os.path.abspath(os.path.join(extract_dir, member.filename))
            if not target_path.startswith(extract_dir + os.sep) and target_path != extract_dir:
                raise ValueError("Malicious archive detected: Path traversal attempt")
            zip_ref.extract(member, extract_dir)
            
    G, files_data, all_chunks = analyze_directory(extract_dir)
    
    if not files_data:
        raise ValueError("The uploaded archive does not contain any supported source code files (e.g., .py, .js, .ts, .md). It may be empty, contain only unsupported formats, or only folders.")
        
    repo_map = generate_repo_map(files_data, G)
    file_tree = build_file_tree(list(files_data.keys()))
    
    return G, files_data, all_chunks, repo_map, file_tree

MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB

def process_upload_task(task_id: str, session_id: str, tmpdirname: str, extract_dir: str, zip_path: str):
    try:
        tasks[task_id]["message"] = "Extracting and analyzing files..."
        G, files_data, all_chunks, repo_map, file_tree = extract_and_analyze_zip(zip_path, extract_dir)
        
        # Create session context
        sessions[session_id] = {
            "files": files_data,
            "graph": G,
            "search_index": LocalSearchIndex(),
            "repo_map": repo_map
        }
        
        tasks[task_id]["message"] = "Building search index..."
        # Add chunks in the same thread (we are already in a background task)
        sessions[session_id]["search_index"].add_chunks(all_chunks)
        
        rf_nodes = []
        for node, data in G.nodes(data=True):
            rf_nodes.append({
                "id": node,
                "position": {"x": 0, "y": 0},
                "data": {"label": data.get("label", node)},
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
            
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = "Processing complete"
        tasks[task_id]["result"] = {
            "message": "Upload successful",
            "session_id": session_id,
            "graph": {
                "nodes": rf_nodes,
                "edges": rf_edges,
            },
            "files": files_data,
            "file_tree": file_tree
        }
    except ValueError as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
    except zipfile.BadZipFile:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = "Invalid or corrupted ZIP file."
    except Exception as e:
        print(f"Background Task Error: {str(e)}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = f"Failed to process upload: {str(e)}"
    finally:
        try:
            shutil.rmtree(tmpdirname)
        except Exception as e:
            print(f"Failed to cleanup temp directory {tmpdirname}: {str(e)}")

@app.post("/api/upload")
async def upload_repo(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .zip files are allowed.")
        
    if file.content_type not in ["application/zip", "application/x-zip-compressed"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only .zip files are allowed.")
        
    # Check file size limitation
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Payload Too Large. Maximum file size is 50MB.")
    
    try:
        tmpdirname = tempfile.mkdtemp()
        zip_path = os.path.join(tmpdirname, "repo.zip")
        with open(zip_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        extract_dir = os.path.abspath(os.path.join(tmpdirname, "extracted"))
        os.makedirs(extract_dir, exist_ok=True)
        
        session_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        
        tasks[task_id] = {
            "status": "processing",
            "message": "Upload saved, starting analysis...",
            "session_id": session_id,
            "result": None,
            "error": None
        }
        
        background_tasks.add_task(process_upload_task, task_id, session_id, tmpdirname, extract_dir, zip_path)
        
        return {
            "message": "Upload successful, processing started",
            "task_id": task_id,
            "session_id": session_id
        }
        
    except Exception as e:
        print(f"Upload Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate upload processing: {str(e)}")

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

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
        raise HTTPException(status_code=500, detail="Gemini API key is missing. Please check your .env file.")
    
    session_id = request.session_id
    if session_id not in sessions:
        raise HTTPException(status_code=400, detail="Session not found. Please upload a repository first.")
        
    repo_context = sessions[session_id]

    if not repo_context["files"]:
        raise HTTPException(status_code=400, detail="Please upload a repository first so I can analyze it and answer your questions.")

    # 1. Intent Detection
    is_architectural = detect_architectural_intent(request.message)
    
    files_data = repo_context["files"]
    total_repo_size = sum(len(data['content']) for data in files_data.values())
    MAX_CONTEXT_CHARS = 500_000 # Safe token limit for Gemini 1.5/2.5 Flash
    
    context_str = ""
    use_rag = True
    relevant_chunks = []
    
    # 2. Dynamic Context Assembly
    if total_repo_size <= MAX_CONTEXT_CHARS:
        # Whole-Repo Context for Small Repositories
        use_rag = False
        context_str += "### FULL REPOSITORY CONTEXT\n"
        context_str += "The repository is small enough to include entirely. Here are all the files:\n\n"
        for path, data in files_data.items():
            context_str += f"--- FILE: {path} ---\n{data['content']}\n\n"
            
    elif is_architectural:
        # Dynamic Context Assembly for Large Repositories on Architectural Queries
        use_rag = False
        context_str += "### CRITICAL ARCHITECTURAL FILES\n"
        context_str += "The following files represent the core architecture of the system:\n\n"
        
        current_chars = 0
        for path, data in files_data.items():
            role = classify_role(path, data['content'])
            if role in ["Entry Points", "Routing & Controllers", "Data Models & Persistence"]:
                content_len = len(data['content'])
                if current_chars + content_len <= MAX_CONTEXT_CHARS:
                    context_str += f"--- FILE: {path} ({role}) ---\n{data['content']}\n\n"
                    current_chars += content_len

        # Step B GraphRAG Fallback
        G = repo_context["graph"]
        in_degrees = dict(G.in_degree())
        top_central_files = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:3]
        
        if top_central_files:
            context_str += "### CRITICAL ARCHITECTURAL COMPONENTS (GRAPH DEPENDENCIES)\n"
            for node, degree in top_central_files:
                if node in files_data:
                    role = classify_role(node, files_data[node]['content'])
                    if role not in ["Entry Points", "Routing & Controllers", "Data Models & Persistence"]:
                        content = files_data[node]['content']
                        if current_chars + len(content[:1500]) <= MAX_CONTEXT_CHARS:
                            context_str += f"--- CENTRAL FILE: {node} (Referenced {degree} times) ---\n"
                            out_edges = list(G.successors(node))
                            if out_edges:
                                context_str += f"Dependencies: {', '.join(out_edges[:5])}\n"
                            context_str += f"Content Snippet:\n{content[:1500]}\n\n"
                            current_chars += len(content[:1500])

    if use_rag:
        # 3. Standard RAG (Semantic Search) for specific implementation questions
        top_k = 8
        relevant_chunks = await asyncio.to_thread(
            repo_context["search_index"].search, request.message, top_k=top_k
        )

    # Inject Selected File Context
    selected_file = request.context.get("selectedFile")
    if selected_file:
        context_str += "### ACTIVE FILE CONTEXT\n"
        context_str += f"The user is currently inspecting the following file: {selected_file.get('path')}\n"
        context_str += f"Imports: {', '.join(selected_file.get('imports', []))}\n"
        context_str += f"Content:\n{selected_file.get('content', '')}\n\n"
        context_str += "IMPORTANT: If the user says 'this file', 'here', or asks to summarize/explain without naming a file, assume they are talking about the ACTIVE FILE above. Analyze this specific file in priority.\n\n"

    # Inject Repository Blueprint
    if repo_context["repo_map"]:
        context_str += f"{repo_context['repo_map']}\n\n"

    if use_rag:
        if not relevant_chunks:
            context_str += "### CODE SNIPPETS\nNo direct matches found, but here is a list of available files:\n"
            context_str += "\n".join(list(repo_context["files"].keys())[:20]) + "\n\n"
        else:
            context_str += "### CODE SNIPPETS\nHere are the relevant snippets from the repository.\n\n"
            for chunk in relevant_chunks:
                context_str += f"--- FILE: {chunk.file_path} (Lines {chunk.start_line}-{chunk.end_line}) ---\n{chunk.content}\n\n"

    if is_architectural:
        context_str += "\nNOTE: The user is asking a structural or architectural question. Prioritize the REPOSITORY ARCHITECTURE BLUEPRINT and the provided full files/snippets to deduce potential flaws or architectural patterns.\n"


    system_instruction = """You are DocSwarm AI, an elite Senior Software Architect and Repository Intelligence Assistant.
Your primary objective is to deliver deep, analytical, and highly accurate insights into the user's codebase.

### AVAILABLE CONTEXT SOURCES
Depending on the size of the repository and the user's query, you will receive a combination of the following context blocks:
1. REPOSITORY ARCHITECTURE BLUEPRINT: A structural map of the codebase, including file roles, directory trees, and top-level graph dependencies.
2. ACTIVE FILE CONTEXT: The file the user is currently looking at. Prioritize this if the user uses implicit pronouns (e.g., "this file", "here").
3. FULL REPOSITORY CONTEXT: The complete source code of the repository (provided for small projects).
4. CRITICAL ARCHITECTURAL FILES / COMPONENTS: The full source code of heavily imported or structurally significant files (Entry Points, Data Models, Routes).
5. CODE SNIPPETS (RAG): Semantically retrieved chunks of code specifically relevant to the user's query.

### ARCHITECTURAL ANALYSIS PROTOCOL
When asked to evaluate architecture, find flaws, suggest improvements, or explain patterns:
- Synthesize the BLUEPRINT with the raw code provided in FULL/CRITICAL files or SNIPPETS.
- Identify common anti-patterns natively (e.g., God objects, tight coupling, hardcoded secrets, lack of error handling, sprawling state, circular dependencies).
- DO NOT rely on pre-generated summaries. You are expected to ACT as the architect and deduce these flaws yourself using the raw code evidence.
- State your inferences confidently. If the provided context lacks sufficient evidence for a definitive claim, clearly articulate what you suspect and what files you would need to confirm it.

### STRICT RULES:
1. Ground every claim in the provided codebase context. Always cite specific file names, classes, or function names when making a point.
2. For IMPLEMENTATION questions, rely on ACTIVE FILE CONTEXT or CODE SNIPPETS.
3. If the answer cannot be reasonably inferred from any provided source, clearly state: "I could not find sufficient evidence in the uploaded documents to answer that." Do not hallucinate external details.
4. Format your responses elegantly using Markdown, bullet points, and code blocks for readability. Maintain a professional, authoritative, yet helpful tone."""

    try:
        response = await asyncio.to_thread(
            call_gemini,
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
            raise HTTPException(status_code=401, detail=f"Invalid Gemini API key. ({detailed_error})")
        elif "quota" in error_msg or "429" in error_msg:
            raise HTTPException(status_code=429, detail=f"Gemini API quota exceeded or high demand. Please wait a moment and try again. ({detailed_error})")
        elif "connection" in error_msg:
            raise HTTPException(status_code=503, detail=f"Failed to connect to Gemini API. ({detailed_error})")
        else:
            raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {detailed_error}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
