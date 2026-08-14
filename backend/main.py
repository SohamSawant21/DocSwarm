import time
import os
import shutil
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from utils.state import sessions, tasks, SESSION_TTL
from services.ai_service import delete_session_chunks
from api.routes import router

def cleanup_session(session_id: str):
    if session_id in sessions:
        session_data = sessions.pop(session_id)
        # Cleanup temp dir
        tmpdirname = session_data.get("tmpdirname")
        if tmpdirname and os.path.exists(tmpdirname):
            try:
                shutil.rmtree(tmpdirname)
            except Exception as e:
                print(f"Failed to delete temp dir {tmpdirname}: {e}")
                
        # Cleanup ChromaDB
        try:
            delete_session_chunks(session_id)
        except Exception as e:
            print(f"Failed to delete chroma docs for {session_id}: {e}")

async def session_cleanup_task():
    while True:
        try:
            now = time.time()
            expired = [sid for sid, data in sessions.items() if now - data.get("last_accessed", now) > SESSION_TTL]
            for sid in expired:
                print(f"Cleaning up expired session {sid}")
                cleanup_session(sid)
                
            # Also clean up old tasks to prevent memory leak there
            expired_tasks = [tid for tid, tdata in tasks.items() if now - tdata.get("created_at", now) > SESSION_TTL * 2]
            for tid in expired_tasks:
                tasks.pop(tid, None)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Cleanup task error: {e}")
        await asyncio.sleep(60)  # Run every minute

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(session_cleanup_task())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    # On shutdown, clean up ALL sessions to not leave dangling temp dirs
    for sid in list(sessions.keys()):
        cleanup_session(sid)

app = FastAPI(title="DocSwarm GraphOS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
