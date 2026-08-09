import requests
import zipfile
import time

def test_upload_and_chat():
    print("Generating dummy repo...")
    with zipfile.ZipFile("test_repo.zip", "w") as z:
        z.writestr("main.py", "import utils\ndef main():\n    print('hello world')\n")
        z.writestr("utils.py", "def helper():\n    return True\n")
        z.writestr("README.md", "This is a test repo.\n")

    print("Uploading repo...")
    start_time = time.time()
    with open("test_repo.zip", "rb") as f:
        res = requests.post(
            "http://localhost:8000/api/upload", 
            files={"file": ("test_repo.zip", f, "application/zip")}
        )
    
    if res.status_code != 200:
        print("Upload failed:", res.text)
        return
        
    data = res.json()
    task_id = data.get("task_id")
    session_id = data.get("session_id")
    print("Task ID:", task_id, "Session ID:", session_id)
    
    # Poll status
    for _ in range(30):
        time.sleep(0.5)
        res_status = requests.get(f"http://localhost:8000/api/status/{task_id}")
        status_data = res_status.json()
        if status_data.get("status") == "completed":
            print("Upload & processing completed!")
            break
        elif status_data.get("status") == "failed":
            print("Upload failed:", status_data)
            return
            
    print("Testing /api/chat...")
    chat_res = requests.post(
        "http://localhost:8000/api/chat",
        json={"message": "What does main.py do?", "session_id": session_id, "context": {}}
    )
    print("Chat Response Code:", chat_res.status_code)
    try:
        print("Chat Response:", chat_res.json())
    except Exception:
        print("Chat Response text:", chat_res.text)

if __name__ == "__main__":
    test_upload_and_chat()
