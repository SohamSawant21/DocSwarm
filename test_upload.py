import requests
import zipfile
import time
import os

def test_upload():
    print("Generating large dummy repo...")
    with zipfile.ZipFile("test_repo.zip", "w") as z:
        # Create 100 folders with 10 files each
        for fld in range(10):
            for i in range(10):
                path = f"folder_{fld}/file_{i}.py"
                # Import something from the previous folder to test cross-folder
                imp = ""
                if fld > 0:
                    imp = f"from folder_{fld-1}.file_{i} import something"
                
                content = f"{imp}\n\ndef func():\n    print('hello')\n"
                z.writestr(path, content)
        z.writestr("main.py", "import folder_0.file_0\nprint('hello world')")

    print("Uploading repo...")
    start_time = time.time()
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
    for _ in range(30):
        time.sleep(0.5)
        res_status = requests.get(f"http://localhost:8000/api/status/{task_id}")
        
        status_data = res_status.json()
        print("Status:", status_data.get("status"), status_data.get("message"))
        
        if status_data.get("status") in ["completed", "failed"]:
            print(f"Final State reached in {time.time() - start_time:.2f} seconds.")
            break

if __name__ == "__main__":
    test_upload()
