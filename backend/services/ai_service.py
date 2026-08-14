import os
import uuid
import chromadb
from typing import List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from utils.models import CodeChunk

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

chroma_client = chromadb.PersistentClient(path='./chroma_db')
collection = chroma_client.get_or_create_collection(name='docswarm_chunks')

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

class VectorSearchIndex:
    def __init__(self, session_id: str):
        self.session_id = session_id

    def add_chunks(self, chunks: List[CodeChunk]):
        if not chunks:
            return
            
        corpus = [f"FILE: {c.file_path}\n{c.content}" for c in chunks]
        
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
                
        return found_chunks

def delete_session_chunks(session_id: str):
    try:
        collection.delete(where={"session_id": session_id})
    except Exception as e:
        print(f"Failed to delete chroma docs for {session_id}: {e}")

def detect_architectural_intent(query: str) -> bool:
    arch_keywords = {
        "architecture", "structure", "design", "flow", "work", "explain", 
        "summarize", "overview", "project", "how does", "alternative", 
        "improvement", "weakness", "pattern", "layout", "purpose"
    }
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in arch_keywords)

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
