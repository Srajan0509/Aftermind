from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from memory_engine.database import init_db
from memory_engine.routes import router as memory_router
from memory_engine.config import memory_config
from memory_extraction.routes import router as extraction_router
from data_ingestion.routes import router as ingestion_router
from commitment_tracker.routes import router as tracker_router

load_dotenv()

# Initialize Database tables and pgvector extension
init_db()

app = FastAPI(
    title="AFTERMIND API",
    description="AI Memory Platform for Businesses - Persistent Memory & Semantic Search",
    version="1.0.0"
)

# CORS Middleware to allow requests from the Next.js frontend
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Module 3 Memory Engine routes
app.include_router(memory_router)
# Mount Module 1 Multi-Source AI Data Ingestion routes
app.include_router(ingestion_router)
# Mount Module 2 Intelligent Memory Extraction routes
app.include_router(extraction_router)
# Mount Module 4 Smart Commitment & Decision Tracker routes
app.include_router(tracker_router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AFTERMIND - AI Memory for Businesses",
        "modules": [
            "Module 1: Multi-Source AI Data Ingestion",
            "Module 2: Intelligent Memory Extraction",
            "Module 3: Connected Long-Term Memory & Semantic Search",
            "Module 4: Smart Commitment & Decision Tracker"
        ],
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "vector_dim": memory_config.VECTOR_DIMENSION
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
