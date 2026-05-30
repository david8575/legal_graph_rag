from fastapi import FastAPI
from backend.app.config import settings
from backend.app.db import check_neo4j, check_qdrant

app = FastAPI(
    title="Legal Graph RAG API",
    description="Korea Legal Graph RAG Backend",
    version="0.1.0"   
)

# uvicorn backend.app.main:app --reload

@app.get("/health")
def health_check():
    return{
        "status": "ok",
        "service": "legal-graph-rag-api",
        "version": "0.1.0",
        "llm_model": settings.ollama_llm_model,
        "embed_model": settings.ollama_embed_model
    }

@app.get("/health/dependencies")
def dependencies_health_check():
    return {
        "neo4j": check_neo4j(),
        "qdrant": check_qdrant(),
    }