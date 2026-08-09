import re

with open("backend/main.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add imports at the top
if "import chromadb" not in code:
    code = code.replace("import uuid", "import uuid\nimport chromadb\n\nchroma_client = chromadb.PersistentClient(path='./chroma_db')\ncollection = chroma_client.get_or_create_collection(name='docswarm_chunks')\n")

# 2. Replace LocalSearchIndex with VectorSearchIndex
old_class = """class LocalSearchIndex:
    def __init__(self):
        self.chunks: List[CodeChunk] = []
        self.embeddings = None

    def add_chunks(self, chunks: List[CodeChunk]):
        self.chunks = chunks
        if not chunks:
            return
        
        corpus = [f"FILE: {c.file_path}\\n{c.content}" for c in chunks]
        
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
        
        # Clear content to save memory
        for c in self.chunks:
            c.content = ""

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
        return results"""

new_class = """class VectorSearchIndex:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def add_chunks(self, chunks: List[CodeChunk]):
        if not chunks:
            return
            
        corpus = [f"FILE: {c.file_path}\\n{c.content}" for c in chunks]
        
        batch_size = 100
        for i in range(0, len(corpus), batch_size):
            batch = corpus[i:i+batch_size]
            batch_chunks = chunks[i:i+batch_size]
            
            try:
                emb = get_embeddings(batch)
            except Exception as e:
                print(f"Embedding error: {e}")
                emb = [[0.0] * 768] * len(batch)
                
            ids = [str(uuid.uuid4()) for _ in batch]
            metadatas = [{
                "session_id": self.session_id,
                "file_path": c.file_path,
                "start_line": c.start_line,
                "end_line": c.end_line
            } for c in batch_chunks]
            
            collection.upsert(
                ids=ids,
                embeddings=emb,
                metadatas=metadatas
            )

    def search(self, query: str, top_k: int = 5) -> List[CodeChunk]:
        try:
            query_emb = get_embeddings([query])
        except Exception as e:
            print(f"Query embedding error: {e}")
            return []
            
        try:
            results = collection.query(
                query_embeddings=query_emb,
                n_results=top_k,
                where={"session_id": self.session_id}
            )
        except Exception as e:
            print(f"ChromaDB query error: {e}")
            return []
            
        found_chunks = []
        if results and results.get('metadatas') and len(results['metadatas']) > 0:
            for meta in results['metadatas'][0]:
                chunk = CodeChunk(
                    file_path=meta['file_path'],
                    content="", # Will be loaded from disk in chat logic
                    start_line=meta['start_line'],
                    end_line=meta['end_line']
                )
                found_chunks.append(chunk)
                
        return found_chunks"""

if old_class in code:
    code = code.replace(old_class, new_class)
else:
    print("Warning: Could not find old LocalSearchIndex class block to replace")

# 3. Replace usage in process_upload_task
code = code.replace("LocalSearchIndex()", "VectorSearchIndex(session_id)")

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Updated main.py for Phase 4")
