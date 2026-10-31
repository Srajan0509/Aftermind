# Afterminds

Full-stack application containing the Next.js frontend and FastAPI backend.

## Architecture

- **`frontend/`**: Modern React framework powered by [Next.js](https://nextjs.org/) (App Router, TypeScript).
- **`backend/`**: High-performance Python backend powered by [FastAPI](https://fastapi.tiangolo.com/).

## Getting Started

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```
- Web Application: [http://localhost:3000](http://localhost:3000)
