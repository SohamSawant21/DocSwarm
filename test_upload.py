import requests
import zipfile
import time

def test_upload():
    # Create a dummy zip file
    with zipfile.ZipFile("test_repo.zip", "w") as z:
        z.writestr("main.py", "print('hello world')")
        z.writestr("README.md", "This is a test repo.")

    with open("test_repo.zip", "rb") as f:
        res = requests.post(
            "http://localhost:8000/api/upload", 
            files={"file": ("test_repo.zip", f, "application/zip")}
        )
    
    print("Upload Response:", res.status_code, res.text)
    if res.status_code != 200:
        return
        
    data = res.json()
    task_id = data.get("task_id")
    print("Task ID:", task_id)
    
    if not task_id:
        return

    # Poll status
    for _ in range(10):
        time.sleep(1)
        res_status = requests.get(f"http://localhost:8000/api/status/{task_id}")
        print("Status Response:", res_status.status_code)
        
        status_data = res_status.json()
        print("Status:", status_data.get("status"), status_data.get("message"))
        
        if status_data.get("status") in ["completed", "failed"]:
            print("Final State reached.")
            break

if __name__ == "__main__":
    test_upload()
