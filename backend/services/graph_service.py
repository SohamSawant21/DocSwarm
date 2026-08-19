import os
import re
import networkx as nx
from typing import Dict, Any, List
from .parser_service import process_file_task


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
        node_id, label, file_chunks, imports, role, size, audit_flags, file_hash = res
        all_chunks.extend(file_chunks)
        files_data[node_id] = {
            "label": label,
            "imports": imports,
            "role": role,
            "size": size,
            "audit_flags": audit_flags,
            "file_hash": file_hash
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
