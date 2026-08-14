import os
import uuid
import asyncio
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

embed_semaphore = asyncio.Semaphore(5)
chat_semaphore = asyncio.Semaphore(10)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(Exception)
)
async def get_embeddings_async(texts: List[str]) -> List[List[float]]:
    if not client:
        return [[0.0] * 768] * len(texts)
        
    def _call():
        return client.models.embed_content(
            model="text-embedding-004",
            contents=texts
        )
        
    response = await asyncio.to_thread(_call)
    return [e.values for e in response.embeddings]

class VectorSearchIndex:
    def __init__(self, session_id: str):
        self.session_id = session_id

    async def add_chunks_async(self, chunks: List[CodeChunk]):
        if not chunks:
            return
            
        corpus = [f"FILE: {c.file_path}\n{c.content}" for c in chunks]
        batch_size = 100
        
        async def process_batch(batch_idx, batch_texts, batch_chunks):
            async with embed_semaphore:
                try:
                    emb = await get_embeddings_async(batch_texts)
                except Exception as e:
                    print(f"Embedding error for batch {batch_idx}: {e}")
                    emb = [[0.0] * 768] * len(batch_texts)
                    
                ids = [str(uuid.uuid4()) for _ in batch_texts]
                metadatas = [{
                    "session_id": self.session_id,
                    "file_path": c.file_path,
                    "start_line": c.start_line,
                    "end_line": c.end_line
                } for c in batch_chunks]
                
                def _upsert():
                    collection.upsert(
                        ids=ids,
                        embeddings=emb,
                        metadatas=metadatas
                    )
                await asyncio.to_thread(_upsert)

        tasks = []
        for i in range(0, len(corpus), batch_size):
            batch = corpus[i:i+batch_size]
            batch_chunks_sub = chunks[i:i+batch_size]
            tasks.append(process_batch(i, batch, batch_chunks_sub))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):
                print(f"Batch processing error: {res}")

    async def search_async(self, query: str, top_k: int = 5) -> List[CodeChunk]:
        try:
            query_emb = await get_embeddings_async([query])
        except Exception as e:
            print(f"Query embedding error: {e}")
            return []
            
        def _query():
            return collection.query(
                query_embeddings=query_emb,
                n_results=top_k,
                where={"session_id": self.session_id}
            )
            
        try:
            results = await asyncio.to_thread(_query)
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
async def call_gemini_async(model_name: str, contents: list, system_instruction: str):
    async with chat_semaphore:
        def _call():
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                )
            )
        return await asyncio.to_thread(_call)
