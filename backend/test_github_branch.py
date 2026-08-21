import asyncio
from services.github_service import download_github_repo
import os

async def test_download():
    dest = "test_download.zip"
    try:
        print("Testing fastAPI (uses master)...")
        await download_github_repo("tiangolo", "fastapi", dest)
        print("Success! Size:", os.path.getsize(dest))
        if os.path.exists(dest): os.remove(dest)
        
        print("Testing checkout (uses main)...")
        await download_github_repo("actions", "checkout", dest)
        print("Success! Size:", os.path.getsize(dest))
        if os.path.exists(dest): os.remove(dest)
        
        print("Testing invalid repo...")
        try:
            await download_github_repo("invalid123", "invalid123", dest)
            print("Failure: Should have thrown an error.")
        except Exception as e:
            print("Successfully caught expected error:", str(e))
    finally:
        if os.path.exists(dest):
            os.remove(dest)

if __name__ == "__main__":
    asyncio.run(test_download())
