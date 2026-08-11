from fastapi.testclient import TestClient
from main import app, sessions
import os
import tempfile
import uuid

client = TestClient(app)

def test_file_endpoint():
    print("Testing /api/file/{session_id} endpoint...")
    
    # 1. Setup a mock session with a temporary directory
    session_id = str(uuid.uuid4())
    extract_dir = tempfile.mkdtemp()
    
    # Create valid text file
    os.makedirs(os.path.join(extract_dir, "src"), exist_ok=True)
    valid_file_path = os.path.join(extract_dir, "src", "main.ts")
    with open(valid_file_path, "w", encoding="utf-8") as f:
        f.write("console.log('Hello World');")
        
    # Create deeply nested file
    os.makedirs(os.path.join(extract_dir, "a", "b", "c"), exist_ok=True)
    deep_file_path = os.path.join(extract_dir, "a", "b", "c", "nested.txt")
    with open(deep_file_path, "w", encoding="utf-8") as f:
        f.write("nested content")

    # Create binary file
    binary_file_path = os.path.join(extract_dir, "image.png")
    with open(binary_file_path, "wb") as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')
        
    # Create large text file (simulated by just bypassing the check or letting it hit size limit if we create 10MB)
    # 11MB file to trigger the limit
    large_file_path = os.path.join(extract_dir, "large.txt")
    with open(large_file_path, "wb") as f:
        f.write(b'0' * (11 * 1024 * 1024))
        
    # File outside extract_dir (to test traversal)
    outside_file_path = os.path.abspath(os.path.join(extract_dir, "..", "outside.txt"))
    with open(outside_file_path, "w", encoding="utf-8") as f:
        f.write("secret outside content")

    sessions[session_id] = {
        "extract_dir": extract_dir
    }

    # Test Cases
    
    # TC1: Valid session ID and valid file path
    response = client.get(f"/api/file/{session_id}?filepath=src/main.ts")
    assert response.status_code == 200
    assert response.json() == {"content": "console.log('Hello World');"}
    print("✓ Valid session ID and valid file path")
    
    # TC2: Invalid session ID
    response = client.get("/api/file/invalid-session-id?filepath=src/main.ts")
    assert response.status_code == 404
    print("✓ Invalid session ID")
    
    # TC3: Valid session with nonexistent file
    response = client.get(f"/api/file/{session_id}?filepath=src/missing.ts")
    assert response.status_code == 404
    print("✓ Valid session with nonexistent file")
    
    # TC4: Root-level file
    root_file_path = os.path.join(extract_dir, "root.txt")
    with open(root_file_path, "w", encoding="utf-8") as f:
        f.write("root file")
    response = client.get(f"/api/file/{session_id}?filepath=root.txt")
    assert response.status_code == 200
    assert response.json() == {"content": "root file"}
    print("✓ Root-level file")

    # TC5: Deeply nested files
    response = client.get(f"/api/file/{session_id}?filepath=a/b/c/nested.txt")
    assert response.status_code == 200
    assert response.json() == {"content": "nested content"}
    print("✓ Deeply nested files")
    
    # TC6: Invalid paths (empty)
    response = client.get(f"/api/file/{session_id}?filepath=")
    assert response.status_code == 400
    print("✓ Invalid paths (empty)")
    
    # TC7: Directory paths
    response = client.get(f"/api/file/{session_id}?filepath=src")
    assert response.status_code == 400
    print("✓ Directory paths")

    # TC8: Directory traversal attempts such as ../../
    response = client.get(f"/api/file/{session_id}?filepath=../outside.txt")
    assert response.status_code == 403
    print("✓ Directory traversal attempts")
    
    # TC9: Absolute paths
    # Note: On Windows, passing an absolute path like C:/... to os.path.join(extract_dir, filepath) 
    # might resolve to C:/... directly depending on how join works, which would fail the commonpath check.
    abs_path = os.path.abspath(outside_file_path)
    # Using URL encoding might be needed, but requests handles it if we pass it simply
    response = client.get(f"/api/file/{session_id}", params={"filepath": abs_path})
    assert response.status_code == 403
    print("✓ Absolute paths")
    
    # TC10: Binary files
    response = client.get(f"/api/file/{session_id}?filepath=image.png")
    assert response.status_code == 400
    assert "Cannot read binary" in response.json()["detail"]
    print("✓ Binary files")
    
    # TC11: Large text files
    response = client.get(f"/api/file/{session_id}?filepath=large.txt")
    assert response.status_code == 400
    assert "too large" in response.json()["detail"]
    print("✓ Large text files")
    
    print("All tests passed!")
    
if __name__ == '__main__':
    test_file_endpoint()
