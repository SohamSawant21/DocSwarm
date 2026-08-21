
from fastapi.testclient import TestClient
from main import app
from utils.models import GithubImportRequest
import time
import os

client = TestClient(app)

def test_github_import_valid():
    response = client.post("/api/import-github", json={"url": "https://github.com/actions/checkout"})
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "session_id" in data
    
    task_id = data["task_id"]
    # Poll for completion
    for _ in range(60): # 1 minute
        res = client.get(f"/api/status/{task_id}")
        assert res.status_code == 200
        status_data = res.json()
        print(f"Status: {status_data['status']}, Message: {status_data['message']}")
        if status_data["status"] == "completed":
            break
        if status_data["status"] == "failed":
            print(f"Failed: {status_data.get('error')}")
            break
        time.sleep(1)

def test_github_import_invalid_url():
    response = client.post("/api/import-github", json={"url": "http://example.com/not-github"})
    assert response.status_code == 422 # Pydantic validation error

def test_github_import_not_found():
    response = client.post("/api/import-github", json={"url": "https://github.com/invalid-owner1234/invalid-repo1234"})
    assert response.status_code == 200
    data = response.json()
    task_id = data["task_id"]
    for _ in range(30):
        res = client.get(f"/api/status/{task_id}")
        status_data = res.json()
        if status_data["status"] == "failed":
            print("Successfully failed as expected on not found:", status_data["error"])
            break
        time.sleep(1)
        
if __name__ == "__main__":
    print("Running valid test...")
    test_github_import_valid()
    print("Running invalid URL test...")
    test_github_import_invalid_url()
    print("Running not found test...")
    test_github_import_not_found()
    print("All done!")
