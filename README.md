# DocSwarm

A code intelligence tool that visualizes repository dependency graphs, generates structured documentation from source code, and provides interactive code exploration.

## Stack

- **Frontend**: Next.js, TypeScript, React Flow
- **Backend**: FastAPI, Python, NetworkX

## Getting Started

**Backend**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Features

- Upload a `.zip` repository to generate an interactive dependency graph
- Auto-generate structured documentation (module summaries, function references) from source code
- Click nodes to inspect file contents
- Chat with the repo using the built-in assistant

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/upload` | POST | Upload a `.zip` repo, returns graph nodes/edges |
| `/api/chat` | POST | Ask questions about the uploaded repository |
