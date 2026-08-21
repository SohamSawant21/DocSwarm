import os
import httpx
from typing import Optional

MAX_GITHUB_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

async def download_github_repo(owner: str, repo: str, dest_path: str) -> None:
    """
    Downloads a GitHub repository as a ZIP file.
    Enforces a strict 50 MB streaming abort constraint.
    """
    url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async with client.stream("GET", url, timeout=30.0) as response:
                if response.status_code == 404:
                    raise Exception("GitHub repository not found or is private.")
                response.raise_for_status()

                downloaded_size = 0
                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        downloaded_size += len(chunk)
                        if downloaded_size > MAX_GITHUB_DOWNLOAD_SIZE:
                            raise Exception("Repository exceeds the 50 MB limit.")
                        f.write(chunk)
    except Exception as e:
        # Clean up partial download
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise e

async def process_github_task(task_id: str, session_id: str, tmpdirname: str, extract_dir: str, zip_path: str, owner: str, repo: str):
    from utils.state import tasks, sessions
    from services.upload_service import process_upload_task
    import shutil
    try:
        tasks[task_id]["message"] = "Downloading repository from GitHub..."
        await download_github_repo(owner, repo, zip_path)
        
        # Once downloaded, hand over to the existing process_upload_task
        await process_upload_task(task_id, session_id, tmpdirname, extract_dir, zip_path)
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        if os.path.exists(tmpdirname):
            try:
                shutil.rmtree(tmpdirname)
            except Exception:
                pass
