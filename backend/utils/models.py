from pydantic import BaseModel
from typing import Dict, Any

class CodeChunk:
    def __init__(self, file_path: str, content: str, start_line: int, end_line: int):
        self.file_path = file_path
        self.content = content
        self.start_line = start_line
        self.end_line = end_line

class ChatRequest(BaseModel):
    message: str
    session_id: str
    context: Dict[str, Any] = {}

class DocsRequest(BaseModel):
    session_id: str

class AuditFinding(BaseModel):
    issue_type: str
    severity: str
    location: str
    description: str
    evidence: str
    remediation: str

class FileAuditResult(BaseModel):
    file_path: str
    is_safe: bool
    findings: list[AuditFinding]

class BatchAuditResponse(BaseModel):
    results: list[FileAuditResult]
