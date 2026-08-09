import re

with open("backend/main.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. LocalSearchIndex.add_chunks
code = code.replace(
    "self.embeddings = np.array(all_embeddings)",
    "self.embeddings = np.array(all_embeddings)\n        \n        # Clear content to save memory\n        for c in self.chunks:\n            c.content = \"\""
)

# 2. generate_repo_map signature and logic
code = code.replace(
    "def generate_repo_map(files_data: Dict[str, Any], G: nx.DiGraph) -> str:",
    "def generate_repo_map(files_data: Dict[str, Any], G: nx.DiGraph, extract_dir: str) -> str:"
)
code = code.replace(
    """    # 1. Project Overview (Search for README)
    overview = "No README found."
    for path, data in files_data.items():
        if path.lower() == 'readme.md':
            content = data['content']
            # Take first 500 chars as summary
            overview = content[:500] + ("..." if len(content) > 500 else "")
            break""",
    """    # 1. Project Overview (Search for README)
    overview = "No README found."
    for path, data in files_data.items():
        if path.lower() == 'readme.md':
            try:
                with open(os.path.join(extract_dir, path), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                overview = content[:500] + ("..." if len(content) > 500 else "")
            except Exception:
                pass
            break"""
)
code = code.replace(
    """    for path, data in files_data.items():
        role = classify_role(path, data['content'])
        if role in roles:
            roles[role].append(path)""",
    """    for path, data in files_data.items():
        role = data.get('role', 'Other')
        if role in roles:
            roles[role].append(path)"""
)

# 3. process_file_task
code = code.replace(
    """        return node_id, os.path.basename(filepath), content, file_chunks, imports
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return node_id, os.path.basename(filepath), "", [], []""",
    """        role = classify_role(filepath, content)
        return node_id, os.path.basename(filepath), file_chunks, imports, role, len(content)
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return node_id, os.path.basename(filepath), [], [], "Other", 0"""
)

# 4. analyze_directory results processing
code = code.replace(
    """    for res in results:
        node_id, label, content, file_chunks, imports = res
        all_chunks.extend(file_chunks)
        files_data[node_id] = {
            "label": label,
            "imports": imports,
            "content": content
        }
        G.add_node(node_id, label=label, type="customNode")""",
    """    for res in results:
        node_id, label, file_chunks, imports, role, size = res
        all_chunks.extend(file_chunks)
        files_data[node_id] = {
            "label": label,
            "imports": imports,
            "role": role,
            "size": size
        }
        G.add_node(node_id, label=label, type="customNode")"""
)

# 5. extract_and_analyze_zip
code = code.replace(
    "repo_map = generate_repo_map(files_data, G)",
    "repo_map = generate_repo_map(files_data, G, extract_dir)"
)

# 6. process_upload_task session save
code = code.replace(
    """        # Create session context
        sessions[session_id] = {
            "files": files_data,
            "graph": G,
            "search_index": LocalSearchIndex(),
            "repo_map": repo_map
        }""",
    """        # Create session context
        sessions[session_id] = {
            "extract_dir": extract_dir,
            "tmpdirname": tmpdirname,
            "files": files_data,
            "graph": G,
            "search_index": LocalSearchIndex(),
            "repo_map": repo_map
        }"""
)

# 7. cleanup removal
code = code.replace(
    """    finally:
        try:
            shutil.rmtree(tmpdirname)
        except Exception as e:
            print(f"Failed to cleanup temp directory {tmpdirname}: {str(e)}")""",
    """    finally:
        pass # Intentionally keep the tmpdirname on disk for /api/chat disk reads"""
)

# 8. chat_with_repo
code = code.replace(
    """    files_data = repo_context["files"]
    total_repo_size = sum(len(data['content']) for data in files_data.values())
    MAX_CONTEXT_CHARS = 500_000 # Safe token limit for Gemini 1.5/2.5 Flash
    
    context_str = ""
    use_rag = True
    relevant_chunks = []
    
    # 2. Dynamic Context Assembly
    if total_repo_size <= MAX_CONTEXT_CHARS:
        # Whole-Repo Context for Small Repositories
        use_rag = False
        context_str += "### FULL REPOSITORY CONTEXT\\n"
        context_str += "The repository is small enough to include entirely. Here are all the files:\\n\\n"
        for path, data in files_data.items():
            context_str += f"--- FILE: {path} ---\\n{data['content']}\\n\\n"
            
    elif is_architectural:
        # Dynamic Context Assembly for Large Repositories on Architectural Queries
        use_rag = False
        context_str += "### CRITICAL ARCHITECTURAL FILES\\n"
        context_str += "The following files represent the core architecture of the system:\\n\\n"
        
        current_chars = 0
        for path, data in files_data.items():
            role = classify_role(path, data['content'])
            if role in ["Entry Points", "Routing & Controllers", "Data Models & Persistence"]:
                content_len = len(data['content'])
                if current_chars + content_len <= MAX_CONTEXT_CHARS:
                    context_str += f"--- FILE: {path} ({role}) ---\\n{data['content']}\\n\\n"
                    current_chars += content_len""",
    """    files_data = repo_context["files"]
    extract_dir = repo_context.get("extract_dir", "")
    total_repo_size = sum(data.get('size', 0) for data in files_data.values())
    MAX_CONTEXT_CHARS = 500_000 # Safe token limit for Gemini 1.5/2.5 Flash
    
    context_str = ""
    use_rag = True
    relevant_chunks = []
    
    # 2. Dynamic Context Assembly
    if total_repo_size <= MAX_CONTEXT_CHARS:
        # Whole-Repo Context for Small Repositories
        use_rag = False
        context_str += "### FULL REPOSITORY CONTEXT\\n"
        context_str += "The repository is small enough to include entirely. Here are all the files:\\n\\n"
        for path, data in files_data.items():
            try:
                with open(os.path.join(extract_dir, path), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                context_str += f"--- FILE: {path} ---\\n{content}\\n\\n"
            except Exception:
                pass
            
    elif is_architectural:
        # Dynamic Context Assembly for Large Repositories on Architectural Queries
        use_rag = False
        context_str += "### CRITICAL ARCHITECTURAL FILES\\n"
        context_str += "The following files represent the core architecture of the system:\\n\\n"
        
        current_chars = 0
        for path, data in files_data.items():
            role = data.get('role', 'Other')
            if role in ["Entry Points", "Routing & Controllers", "Data Models & Persistence"]:
                content_len = data.get('size', 0)
                if current_chars + content_len <= MAX_CONTEXT_CHARS:
                    try:
                        with open(os.path.join(extract_dir, path), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        context_str += f"--- FILE: {path} ({role}) ---\\n{content}\\n\\n"
                        current_chars += content_len
                    except Exception:
                        pass"""
)

code = code.replace(
    """                if node in files_data:
                    role = classify_role(node, files_data[node]['content'])
                    if role not in ["Entry Points", "Routing & Controllers", "Data Models & Persistence"]:
                        content = files_data[node]['content']
                        if current_chars + len(content[:1500]) <= MAX_CONTEXT_CHARS:
                            context_str += f"--- CENTRAL FILE: {node} (Referenced {degree} times) ---\\n"
                            out_edges = list(G.successors(node))
                            if out_edges:
                                context_str += f"Dependencies: {', '.join(out_edges[:5])}\\n"
                            context_str += f"Content Snippet:\\n{content[:1500]}\\n\\n"
                            current_chars += len(content[:1500])""",
    """                if node in files_data:
                    role = files_data[node].get('role', 'Other')
                    if role not in ["Entry Points", "Routing & Controllers", "Data Models & Persistence"]:
                        try:
                            with open(os.path.join(extract_dir, node), 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                            if current_chars + len(content[:1500]) <= MAX_CONTEXT_CHARS:
                                context_str += f"--- CENTRAL FILE: {node} (Referenced {degree} times) ---\\n"
                                out_edges = list(G.successors(node))
                                if out_edges:
                                    context_str += f"Dependencies: {', '.join(out_edges[:5])}\\n"
                                context_str += f"Content Snippet:\\n{content[:1500]}\\n\\n"
                                current_chars += len(content[:1500])
                        except Exception:
                            pass"""
)

code = code.replace(
    """            context_str += "### CODE SNIPPETS\\nHere are the relevant snippets from the repository.\\n\\n"
            for chunk in relevant_chunks:
                context_str += f"--- FILE: {chunk.file_path} (Lines {chunk.start_line}-{chunk.end_line}) ---\\n{chunk.content}\\n\\n" """,
    """            context_str += "### CODE SNIPPETS\\nHere are the relevant snippets from the repository.\\n\\n"
            for chunk in relevant_chunks:
                try:
                    with open(os.path.join(extract_dir, chunk.file_path), 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        chunk_content = "".join(lines[chunk.start_line - 1 : chunk.end_line])
                    context_str += f"--- FILE: {chunk.file_path} (Lines {chunk.start_line}-{chunk.end_line}) ---\\n{chunk_content}\\n\\n"
                except Exception:
                    pass"""
)

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated main.py")
