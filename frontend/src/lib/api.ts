export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const endpoints = {
  upload: `${API_BASE_URL}/api/upload`,
  chat: `${API_BASE_URL}/api/chat`,
  status: (taskId: string) => `${API_BASE_URL}/api/status/${taskId}`,
  fileContent: (sessionId: string, filepath: string) => 
    `${API_BASE_URL}/api/file/${encodeURIComponent(sessionId)}?filepath=${encodeURIComponent(filepath)}`,
  generateDocs: `${API_BASE_URL}/api/generate-docs`,
};
