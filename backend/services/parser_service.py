import networkx as nx
import os
import re
from typing import List, Dict, Any
from utils.models import CodeChunk

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
        from services.audit_service import scan_file_content
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        file_chunks = chunk_file(node_id, content)
        
        imports = []
        if filepath.endswith('.py'):
            imports = parse_python(content)
        elif filepath.endswith(('.js', '.jsx', '.ts', '.tsx')):
            imports = parse_js_ts(content)
            
        role = classify_role(filepath, content)
        audit_flags = scan_file_content(filepath, content)
        
        return node_id, os.path.basename(filepath), file_chunks, imports, role, len(content), audit_flags
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return node_id, os.path.basename(filepath), [], [], "Other", 0, {}

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


def generate_repo_map(files_data: Dict[str, Any], G: nx.DiGraph, extract_dir: str) -> str:
    blueprint = "### REPOSITORY ARCHITECTURE BLUEPRINT\n\n"
    
    # 1. Project Overview (Search for README)
    overview = "No README found."
    for path, data in files_data.items():
        if path.lower() == 'readme.md':
            try:
                with open(os.path.join(extract_dir, path), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                overview = content[:500] + ("..." if len(content) > 500 else "")
            except Exception:
                pass
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
        role = data.get('role', 'Other')
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
