## GitHub Repository Import: Architecture Analysis & Implementation Plan

## 1. Current Architecture Analysis

The DocSwarm application currently operates on a clean, asynchronous client-server architecture designed around temporary session-based storage.

- Frontend (Next.js): Provides an upload interface ( page.tsx ) that sends a FormData payload containing a .zip file to the backend. It relies on a polling mechanism ( setInterval ) to check the status of the background task and updates the UI accordingly.

- Backend (FastAPI): Exposes a /api/upload endpoint ( routes.py ). Upon receiving the file, it validates the file type and payload size (50MB max), creates a unique temporary directory, and writes the UploadFile to a local repo.zip .

- State Management: Uses in-memory dictionaries ( sessions and tasks in utils/state.py ) to track background task progress and store processed repository data (Graph, file trees, ChromaDB vector index) for a given session_id .

## 2. Existing Repository Upload Flow

- 1. Upload: User uploads a ZIP file via /api/upload .

- 2. Initialization: Backend generates a session_id and task_id , saves the ZIP to a temporary directory, and starts a BackgroundTasks job ( process_upload_task ).

- 3. Extraction & Analysis:

- extract_and_analyze_zip executes in a thread pool.

- It iterates through the ZIP, enforcing security constraints (max 15,000 files, max 50MB per file, max 250MB extracted size) and preventing path traversals.

- It runs analyze_directory to generate the dependency graph, AST chunks, and files_data .

- 4. Vector Indexing: Extracted chunks are asynchronously embedded and inserted into a VectorSearchIndex .

- 5. Polling: Frontend polls /api/status/{task_id} every 2 seconds until the status is completed or failed .

- 6. Completion: Frontend routes to the dashboard, loading the graph and files using the session_id .


## 3. Integration Points for GitHub Import

To achieve the requested architecture without duplicating logic, the GitHub import feature should hook into the pipeline immediately after the file acquisition stage but before the extraction/analysis stage.

## Integration Point:

Create a new endpoint /api/import-github that acts as a sister endpoint to /api/upload . Instead of receiving an UploadFile , it receives a JSON payload with a GitHub URL. The backend will fetch the repository as a ZIP archive from GitHub, save it to repo.zip in a temp directory, and then invoke the exact same process_upload_task function used by the local upload flow.

## 4. Potential Technical Challenges

- Long Network Requests: Downloading large repositories from GitHub can take time. If the download happens synchronously in the endpoint handler, the request might timeout.

- GitHub Rate Limiting: Fetching from github.com without authentication is subject to rate limits. High traffic could result in IP-based blocking.

- Private Repositories: Without authentication integration (e.g., GitHub OAuth or PATs), private repositories will fail to download (404 Not Found).

- Branch Selection: Users might want to import specific branches (e.g., dev or staging ) instead of the default main branch.

## 5. Security Analysis

- SSRF (Server-Side Request Forgery): A malicious user could provide an internal URL (e.g., regex to ensure the URL precisely matches http://localhost:8000/admin ) instead of a GitHub URL. Safeguard: Strict URL validation using ^https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+/?\$ .

- ZIP Bombs & Path Traversal: Since the GitHub flow will reuse process_upload_task , the existing ZIP extraction safeguards (file count limits, file size limits, path traversal checks) are inherently preserved and will protect the system against malicious GitHub repositories.

- Denial of Service (DoS) via Bandwidth Exhaustion: A user could provide a massive GitHub repository, causing the server to download gigabytes of data. Safeguard: Implement streaming downloads with a hard cutoff limit (e.g., abort download if Content-Length or streamed bytes exceed 50MB).

- Temporary File Cleanup: Ensure that if the network download fails halfway, the partial temporary directory is reliably deleted.


## 6. Performance Analysis

- Streaming Downloads: The backend must download the GitHub ZIP in chunks (e.g., using httpx or requests with stream=True ) and write directly to disk, avoiding loading the entire ZIP into memory.

- Asynchronous Execution: To prevent connection timeouts, the actual GitHub download should be pushed into the process_upload_task (or a dedicated download step preceding it) so that the /api/import-github endpoint returns immediately with a task_id .

- Reusability: By injecting the downloaded ZIP into the existing pipeline, we avoid duplicating the heavy AST parsing and graph generation logic, ensuring consistent performance.

## 7. Recommended Architecture

```
┌── Local ZIP Upload ────────────┐
User Repository ────┤ (/api/upload) │
│ │
└── GitHub Repo URL ─────────────┤
(/api/import-github) │
↓ │
Stream ZIP from GitHub │
(Aborts if > 50MB) │
↓ │
└────────────────────┴──► background_tasks
↓
process_upload_task()
↓
Secure Extraction
↓
Repository Analysis
↓
Dependency Graph
↓
AI / RAG / AI Docs
```


## 8. Detailed Phase-Wise Implementation Plan

## Phase 1: Backend Core Integration (API & Download Logic)

- Objective: Create the /api/import-github endpoint and securely download the repository ZIP.

- Scope: Backend only.

- Files Modified: backend/api/routes.py , backend/utils/models.py .

- Implementation Details:

- Add GithubImportRequest(BaseModel) to models.py to validate incoming URLs.

- Create download_github_repo utility to stream the ZIP archive from https://github.com/{owner}/{repo}/archive/refs/heads/main.zip using httpx .

- Implement a 50MB streaming abort constraint to prevent DoS.

- Create /api/import-github endpoint. It will create a temporary directory, validate the URL, generate a task_id and session_id , and launch a new background wrapper task.

- Create an async wrapper function process_github_task that first runs the download, and if successful, directly calls the existing process_upload_task .

- Security Considerations: Strict Regex URL validation (prevent SSRF). Stream size enforcement (prevent DoS).

- Testing & Validation: Use tools like Postman to POST valid/invalid/huge GitHub URLs and verify task status and error handling.

## Phase 2: Frontend UI Update (Upload Interface)

- Objective: Allow users to input a GitHub URL alongside the existing ZIP upload.

- Scope: Frontend only.

- Files Modified: frontend/src/app/page.tsx , frontend/src/lib/api.ts .

- Implementation Details:

- Add importGithub: \ \${API_BASE_URL}/api/import-github` to api.ts`.

- Update page.tsx UI to include a toggle or tabs: "Upload ZIP" vs "GitHub URL".

- Add a text input field for the GitHub URL.

- Implement handleGithubImport function mirroring handleFileUpload , sending a POST request to /api/import-github .

- Reuse the exact same polling logic ( setInterval on /api/status ) since the task format remains identical.

- Expected Outcome: Users can paste a URL, click "Import", and the UI seamlessly transitions to the same loading/polling state as a ZIP upload.

- Dependencies: Depends on Phase 1 completion.


## Phase 3: Robustness, Error Handling & Branch Selection

- Objective: Handle edge cases smoothly and add quality-of-life improvements.

- Scope: Full Stack.

- Files Modified: backend/api/routes.py , frontend/src/app/page.tsx .

- Implementation Details:

- Backend: Use the GitHub API ( https://api.github.com/repos/{owner}/{repo} ) to fetch the default branch instead of hardcoding main . Fallback to master if necessary.

- Backend: Catch 404 errors explicitly and return user-friendly messages ("Repository not found or is private").

- Frontend: Add client-side regex validation for the GitHub URL before submission to provide instant feedback.

- Performance Considerations: The GitHub API call adds a minor delay (~200ms) but greatly improves reliability for repos not using main .

- Dependencies: Depends on Phases 1 and 2.

## 9. Recommended First Phase

## Execute Phase 1 (Backend Core Integration) first.

The most critical challenge is securely fetching the remote repository and seamlessly injecting it into the existing background task architecture without breaking the local ZIP upload flow. By completing the backend first, you can independently test the download limits, SSRF protections, and temp directory cleanup before touching the React frontend.

## 10. Future Enhancements (Out of Scope for Initial Implementation)

- Private Repositories: Implementing GitHub OAuth to fetch short-lived access tokens, allowing the backend to clone private repositories on behalf of the user.

- Sub-directory Support: Allowing users to import a specific folder within a monorepo rather than the entire repository.

- Real-time Download Progress: Emitting download progress percentages (via WebSockets or SSE) before the extraction phase begins.

- Git Clone vs ZIP: For massive repositories, performing a shallow git clone --depth 1 might be faster than generating and downloading a ZIP archive from GitHub.
