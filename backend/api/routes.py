import os
import uuid
import shutil
import tempfile
import zipfile
import asyncio
import time
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Dict, Any

from utils.state import sessions, tasks
from utils.models import ChatRequest, DocsRequest
from services.ai_service import VectorSearchIndex, call_gemini_async, detect_architectural_intent, client
from services.graph_service import analyze_directory, generate_repo_map
from services.parser_service import build_file_tree
from services.docs_service import generate_project_docs

router = APIRouter()
MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB

def extract_and_analyze_zip(zip_path: str, extract_dir: str):
    MAX_EXTRACTED_SIZE = 250 * 1024 * 1024 # 250MB limit
    MAX_FILES = 15000
    MAX_FILE_SIZE = 50 * 1024 * 1024 # 50MB per file max
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
        if not session_created and os.path.exists(tmpdirname):
            try:
                shutil.rmtree(tmpdirname)
            except Exception:
                pass

@router.post("/api/upload")
async def upload_repo(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .zip files are allowed.")
        
    if file.content_type not in ["application/zip", "application/x-zip-compressed"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only .zip files are allowed.")
        
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
            "error": None,
            "created_at": time.time()
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

@router.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]

@router.get("/api/file/{session_id}")
async def get_file_content(session_id: str, filepath: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    sessions[session_id]["last_accessed"] = time.time()
    session_data = sessions[session_id]
    extract_dir = session_data.get("extract_dir")
    
    if not extract_dir or not os.path.isdir(extract_dir):
        raise HTTPException(status_code=500, detail="Repository not found or extracted")
        
    if not filepath:
        raise HTTPException(status_code=400, detail="Filepath query parameter is required")
        
    try:
        requested_path = os.path.abspath(os.path.join(extract_dir, filepath))
        
        if os.path.commonpath([extract_dir, requested_path]) != extract_dir:
            raise HTTPException(status_code=403, detail="Access denied: Invalid file path")
            
        if not os.path.exists(requested_path):
            raise HTTPException(status_code=404, detail="File not found")
            
        if not os.path.isfile(requested_path):
            raise HTTPException(status_code=400, detail="Requested path is not a file")
            
        MAX_READ_SIZE = 10 * 1024 * 1024
        file_size = os.path.getsize(requested_path)
        if file_size > MAX_READ_SIZE:
            raise HTTPException(status_code=400, detail="File is too large to display")
            
        with open(requested_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        return {"content": content}
        
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Cannot read binary or unsupported file format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while reading the file")

@router.post("/api/chat")
async def chat_with_repo(request: ChatRequest):
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API key is missing. Please check your .env file.")
    
    session_id = request.session_id
    if session_id not in sessions:
        raise HTTPException(status_code=400, detail="Session not found. Please upload a repository first.")
        
    sessions[session_id]["last_accessed"] = time.time()
    repo_context = sessions[session_id]

    if not repo_context["files"]:
        raise HTTPException(status_code=400, detail="Please upload a repository first so I can analyze it and answer your questions.")

    is_architectural = detect_architectural_intent(request.message)
    files_data = repo_context["files"]
    extract_dir = repo_context.get("extract_dir", "")
    total_repo_size = sum(data.get('size', 0) for data in files_data.values())
    MAX_CONTEXT_CHARS = 500_000
    
    context_str = ""
    use_rag = True
    relevant_chunks = []
    
    if total_repo_size <= MAX_CONTEXT_CHARS:
        use_rag = False
        context_str += "### FULL REPOSITORY CONTEXT\n"
        context_str += "The repository is small enough to include entirely. Here are all the files:\n\n"
        for path, data in files_data.items():
            try:
                with open(os.path.join(extract_dir, path), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                context_str += f"--- FILE: {path} ---\n{content}\n\n"
            except Exception:
                pass
            
    elif is_architectural:
        use_rag = False
        context_str += "### CRITICAL ARCHITECTURAL FILES\n"
        context_str += "The following files represent the core architecture of the system:\n\n"
        
        current_chars = 0
        for path, data in files_data.items():
            role = data.get('role', 'Other')
            if role in ["Entry Points", "Routing & Controllers", "Data Models & Persistence"]:
                content_len = data.get('size', 0)
                if current_chars + content_len <= MAX_CONTEXT_CHARS:
                    try:
                        with open(os.path.join(extract_dir, path), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        context_str += f"--- FILE: {path} ({role}) ---\n{content}\n\n"
                        current_chars += content_len
                    except Exception:
                        pass

        G = repo_context["graph"]
        in_degrees = dict(G.in_degree())
        top_central_files = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:3]
        
        if top_central_files:
            context_str += "### CRITICAL ARCHITECTURAL COMPONENTS (GRAPH DEPENDENCIES)\n"
            for node, degree in top_central_files:
                if node in files_data:
                    role = files_data[node].get('role', 'Other')
                    if role not in ["Entry Points", "Routing & Controllers", "Data Models & Persistence"]:
                        try:
                            with open(os.path.join(extract_dir, node), 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            if current_chars + len(content[:1500]) <= MAX_CONTEXT_CHARS:
                                context_str += f"--- CENTRAL FILE: {node} (Referenced {degree} times) ---\n"
                                out_edges = list(G.successors(node))
                                if out_edges:
                                    context_str += f"Dependencies: {', '.join(out_edges[:5])}\n"
                                context_str += f"Content Snippet:\n{content[:1500]}\n\n"
                                current_chars += len(content[:1500])
                        except Exception:
                            pass

    if use_rag:
        top_k = 8
        relevant_chunks = await repo_context["search_index"].search_async(request.message, top_k=top_k)

    selected_file = request.context.get("selectedFile")
    if selected_file:
        context_str += "### ACTIVE FILE CONTEXT\n"
        context_str += f"The user is currently inspecting the following file: {selected_file.get('path')}\n"
        context_str += f"Imports: {', '.join(selected_file.get('imports', []))}\n"
        context_str += f"Content:\n{selected_file.get('content', '')}\n\n"
        context_str += "IMPORTANT: If the user says 'this file', 'here', or asks to summarize/explain without naming a file, assume they are talking about the ACTIVE FILE above. Analyze this specific file in priority.\n\n"

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
        response = await call_gemini_async(
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


@router.post("/api/generate-docs")
async def generate_docs(request: DocsRequest):
    if request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    
    sessions[request.session_id]["last_accessed"] = time.time()
    
    try:
        docs = await generate_project_docs(request.session_id)
        return {"docs": docs}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Docs Generation Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate documentation.")
