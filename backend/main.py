import os
import zipfile
import tempfile
import re
import networkx as nx
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List

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

def parse_js_ts(file_content: str):
    imports = []
    # match `import { X } from './path'` or `import X from "path"`
    import_pattern = re.compile(r'import\s+.*?\s+from\s+[\'"](.*?)[\'"]', re.MULTILINE | re.DOTALL)
    require_pattern = re.compile(r'require\([\'"](.*?)[\'"]\)', re.MULTILINE)
    
    for match in import_pattern.findall(file_content):
        imports.append(match)
    for match in require_pattern.findall(file_content):
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
    
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, extract_dir)
                # Normalize path for ID
                node_id = rel_path.replace('\\', '/')
                
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                imports = []
                icon = "description"
                if file.endswith('.py'):
                    imports = parse_python(content)
                    icon = "data_object"
                elif file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    imports = parse_js_ts(content)
                    icon = "code"
                
                # Simple heuristic for icon
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
            imp_base = imp.split('/')[-1]
            for target_id, target_data in files_data.items():
                if target_data["label"].startswith(imp_base):
                    G.add_edge(node_id, target_id)
                    break
    
    return G, files_data

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
        
        G, files_data = analyze_directory(extract_dir)
        
        # Position nodes using spring layout for MVP
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

@app.post("/api/chat")
async def chat_with_repo(request: ChatRequest):
    # For the MVP, we are mocking the AI response.
    # In a real implementation, this would connect to OpenAI/Claude
    # and pass `request.context` (the graph data) as part of the system prompt.
    query = request.message.lower()
    
    if "architecture" in query or "structure" in query:
        response = "Based on the repository context, the architecture follows a standard layered approach. You can see the main modules separated by concerns. Use the graph visualization on the left to see exactly how they depend on each other."
    elif "middleware" in query or "auth" in query:
        response = "The authentication logic is primarily handled in the middleware layer. This ensures that all incoming API requests are verified before reaching the core services."
    elif "database" in query or "store" in query:
        response = "I detected database connection patterns. The application appears to use a central store or repository pattern. Look for nodes with the 'database' icon in the graph."
    else:
        response = f"This JavaScript file demonstrates the use of the `filter()` method to create new arrays based on specific conditions.Part 1 filters ages to return only adults (values greater than or equal to 18), while Part 2 filters words whose length exceeds 6 characters. It showcases concise arrow function syntax and practical array filtering operations in JavaScript."
        
    import asyncio
    await asyncio.sleep(1) # simulate network latency
    return {"reply": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
