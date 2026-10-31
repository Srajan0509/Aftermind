# Afterminds Backend (FastAPI)

FastAPI backend service for the Afterminds application.

## Prerequisites

- Python 3.10+

## Setup & Run

1. **Create and activate a virtual environment:**
   ```bash
   # Windows PowerShell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   Copy-Item .env.example .env
   ```

4. **Run development server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

5. **API Documentation:**
   - Interactive Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
