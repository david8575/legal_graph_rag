from fastapi import FastAPI, Response

from backend.app.config import settings
from backend.app.db import check_neo4j, check_qdrant
from backend.app.graph_schema import apply_graph_schema
from backend.app.law_api import search_laws, normalize_law_search_response, get_law_detail_xml, normalize_law_detail_articles
from backend.app.chunking import chunk_articles
from backend.app.graph_repository import save_law_with_articles, save_chunks
from backend.app.qdrant_repository import ensure_legal_chunks_collection

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

@app.post("/admin/graph/schema")
def create_graph_schema():
    apply_graph_schema()

    return {
        "status": "ok",
        "message": "graph schema applied",
    }

@app.get("/admin/laws/search")
def admin_search_laws(query: str, display: int = 5, page: int = 1):
    return search_laws(
        query=query,
        display=display,
        page=page
    )

@app.get("/admin/laws/search/normalized")
def admin_search_law_normalized(query: str, display: int = 5, page: int = 1):
    data = search_laws(query=query, display=display, page=page)
    laws = normalize_law_search_response(data)

    return [law.model_dump(mode="json") for law in laws]

@app.get("/admin/laws/{mst}/detail")
def admin_law_detail(mst: str):
    xml_text = get_law_detail_xml(mst)

    return Response(
        content=xml_text,
        media_type="application/xml",
    )

@app.get("/admin/laws/{mst}/articles")
def admin_law_articles(mst: str):
    xml_text = get_law_detail_xml(mst)
    law_id = f"law:{mst}"

    articles = normalize_law_detail_articles(
        xml_text=xml_text,
        law_id=law_id
    )
    
    return [article.model_dump(mode="json") for article in articles]

@app.get("/admin/laws/{mst}/chunks")
def admin_law_chunks(mst: str):
    xml_text = get_law_detail_xml(mst)
    law_id = f"law:{mst}"

    articles = normalize_law_detail_articles(
        xml_text = xml_text,
        law_id=law_id
    )

    chunks = chunk_articles(articles)

    return [chunk.model_dump(mode="json") for chunk in chunks]

@app.post("/admin/laws/{mst}/ingest")
def admin_ingest_law(mst: str, query: str):
    search_data = search_laws(query=query, display=10, page=1)
    laws = normalize_law_search_response(search_data)

    law_id = f"law:{mst}"
    matched_law = next(law for law in laws if law.id == law_id)

    xml_text = get_law_detail_xml(mst)

    articles = normalize_law_detail_articles(
        xml_text=xml_text,
        law_id=law_id,
    )

    chunks = chunk_articles(articles)

    law_result = save_law_with_articles(
        law=matched_law,
        articles=articles,
    )

    chunk_result = save_chunks(chunks)

    return {
        "status": "ok",
        **law_result,
        **chunk_result,
    }

@app.post("/admin/qdrant/collections/legal-chunks")
def create_legal_chunks_collection():
    return ensure_legal_chunks_collection()