import os
import uuid
import shutil
import tempfile
import zipfile
import asyncio
import time
from typing import Dict, Any

from utils.state import sessions, tasks
from services.ai_service import VectorSearchIndex
from services.graph_service import analyze_directory
from services.parser_service import build_file_tree, generate_repo_map

MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB

def extract_and_analyze_zip(zip_path: str, extract_dir: str):
    MAX_EXTRACTED_SIZE = 250 * 1024 * 1024 # 250MB limit
    MAX_FILES = 15000
    total_extracted_size = 0
    file_count = 0
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        if not zip_ref.infolist():
            raise ValueError("The uploaded ZIP file is empty.")
            
        for member in zip_ref.infolist():
            file_count += 1
            if file_count > MAX_FILES:
                raise ValueError(f"The archive contains too many files (exceeds {MAX_FILES}).")
                
            if member.file_size > MAX_FILE_SIZE:
                raise ValueError(f"File {member.filename} is too large (exceeds 50MB).")
                
            total_extracted_size += member.file_size
            if total_extracted_size > MAX_EXTRACTED_SIZE:
                raise ValueError("The repository is too large when extracted (exceeds 250MB). Please upload a smaller project.")
                
            target_path = os.path.abspath(os.path.join(extract_dir, member.filename))
            if not target_path.startswith(extract_dir + os.sep) and target_path != extract_dir:
                raise ValueError("Malicious archive detected: Path traversal attempt")
            
            if member.is_dir():
                os.makedirs(target_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zip_ref.open(member, 'r') as source, open(target_path, 'wb') as target:
                    shutil.copyfileobj(source, target, length=65536)
            
    G, files_data, all_chunks = analyze_directory(extract_dir)
    
    if not files_data:
        raise ValueError("The uploaded archive does not contain any supported source code files. It may be empty, contain only unsupported formats, or only folders.")
        
    repo_map = generate_repo_map(files_data, G, extract_dir)
    file_tree = build_file_tree(list(files_data.keys()))
    
    return G, files_data, all_chunks, repo_map, file_tree

async def process_upload_task(task_id: str, session_id: str, tmpdirname: str, extract_dir: str, zip_path: str):
    session_created = False
    try:
        tasks[task_id]["message"] = "Extracting and analyzing files..."
        
        # Run blocking ZIP extraction and multi-process AST parsing in a separate thread pool
        def _run_extract():
            return extract_and_analyze_zip(zip_path, extract_dir)
            
        G, files_data, all_chunks, repo_map, file_tree = await asyncio.to_thread(_run_extract)
        
        sessions[session_id] = {
            "extract_dir": extract_dir,
            "tmpdirname": tmpdirname,
            "files": files_data,
            "graph": G,
            "search_index": VectorSearchIndex(session_id),
            "repo_map": repo_map,
            "last_accessed": time.time()
        }
        
        tasks[task_id]["message"] = "Building search index..."
        await sessions[session_id]["search_index"].add_chunks_async(all_chunks)
        
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
            
        session_created = True
        
        tasks[task_id]["message"] = "Running code audit..."
        from services.ai_service import run_audit_pipeline
        audit_results = await run_audit_pipeline(extract_dir, files_data)
        
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
            "file_tree": file_tree,
            "audit_results": audit_results
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
        if not session_created and os.path.exists(tmpdirname):
            try:
                shutil.rmtree(tmpdirname)
            except Exception:
                pass
