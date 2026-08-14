import os
from typing import Dict, Any
from utils.state import sessions
from services.ai_service import call_gemini_async

async def generate_project_docs(session_id: str) -> str:
    if session_id not in sessions:
        raise ValueError("Session not found")
        
    session_data = sessions[session_id]
    
    # Return cached docs if they exist
    if "docs" in session_data and session_data["docs"]:
        return session_data["docs"]
        
    repo_map = session_data.get("repo_map", "")
    files_data = session_data.get("files", {})
    extract_dir = session_data.get("extract_dir", "")
    
    # 1. Gather context
    MAX_CHARS = 100000
    current_chars = 0
    context_str = f"{repo_map}\n\n### CRITICAL API & CONFIGURATION FILES\n\n"
    
    # Prioritize Routes, Controllers, Entry Points, and Configs to generate API docs and Setup guides
    for path, data in files_data.items():
        role = data.get("role", "Other")
        if role in ["Entry Points", "Routing & Controllers", "Configuration", "Data Models & Persistence"]:
            content_len = data.get("size", 0)
            if current_chars + content_len <= MAX_CHARS:
                try:
                    with open(os.path.join(extract_dir, path), 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    context_str += f"--- FILE: {path} ({role}) ---\n{content}\n\n"
                    current_chars += content_len
                except Exception:
                    pass
                    
    system_instruction = """You are an expert Technical Writer and Software Architect.
Your task is to generate comprehensive, professional Markdown documentation for the provided repository.

Use the provided REPOSITORY ARCHITECTURE BLUEPRINT and the source code of critical files to write the documentation.
DO NOT fabricate or hallucinate features, endpoints, or commands that are not evident in the provided context.

The output MUST be formatted in Markdown and MUST include the following sections if the evidence supports them:

# Project Overview
A clear, high-level summary of what the project does, its purpose, and its primary domain.

## Project Structure & Architecture
A breakdown of the architecture, key modules, and how the repository is organized.

## Setup & Installation
Inferred instructions for running or building the project (e.g., npm install, pip install, environment variables).

## Key Technologies & Frameworks
A list of frameworks and libraries heavily used in the project.

## API Reference (If Applicable)
A structured list of detected API endpoints, including:
- HTTP Method & Path
- Purpose
- Expected parameters or request body (if inferable)
- Response structure (if inferable)

## Core Workflows
A brief explanation of how data flows through the application or the main user journeys.

Make the documentation elegant, readable, and highly accurate.
"""

    prompt = "Please generate the comprehensive AI Documentation for this repository based on the provided structural blueprint and critical source files:\n\n" + context_str

    try:
        response = await call_gemini_async(
            model_name="gemini-2.5-flash",
            contents=[prompt],
            system_instruction=system_instruction
        )
        
        docs_content = response.text
        if not docs_content:
            raise ValueError("LLM returned empty documentation.")
            
        # Cache it
        sessions[session_id]["docs"] = docs_content
        return docs_content
        
    except Exception as e:
        raise ValueError(f"Failed to generate documentation: {str(e)}")
