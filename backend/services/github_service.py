import os
import httpx
from typing import Optional

MAX_GITHUB_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

async def download_github_repo(owner: str, repo: str, dest_path: str) -> None:
    """
    Downloads a GitHub repository as a ZIP file.
    Enforces a strict 50 MB streaming abort constraint.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    default_branch = "master" # Fallback
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # 1. Fetch repository metadata to determine the default branch
            try:
                meta_response = await client.get(api_url, timeout=10.0)
                if meta_response.status_code == 404:
                    raise Exception("Repository not found or is private.")
                if meta_response.status_code == 403:
                    raise Exception("GitHub API rate limit exceeded or repository is inaccessible.")
                
                if meta_response.status_code == 200:
                    meta_data = meta_response.json()
                    default_branch = meta_data.get("default_branch", "master")
                else:
                    # Fallback for unexpected non-success codes
                    default_branch = "master"
            except Exception as e:
                if str(e) in ["Repository not found or is private.", "GitHub API rate limit exceeded or repository is inaccessible."]:
                    raise e
                # Fallback on network timeout or connection failure during metadata fetch
                default_branch = "master"
            
            # 2. Construct archive URL using the determined branch
            archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{default_branch}.zip"
            
            async with client.stream("GET", archive_url, timeout=30.0) as response:
                if response.status_code == 404:
                    raise Exception("Repository not found or is private.")
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
