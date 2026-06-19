from fastapi import FastAPI, Response

from backend.app.config import settings
from backend.app.db import check_neo4j, check_qdrant
from backend.app.graph_schema import apply_graph_schema
from backend.app.law_api import search_laws, normalize_law_search_response, get_law_detail_xml, normalize_law_detail_articles
from backend.app.chunking import chunk_articles
from backend.app.graph_repository import save_law_with_articles, save_chunks, list_chunks, get_article_context
from backend.app.qdrant_repository import ensure_legal_chunks_collection, upsert_chunk_vectors, search_similar_chunks
from backend.app.llm import generate_answer

from backend.app.embedding import embed_text

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

@app.get("/admin/embedding/test")
def admin_embedding_test(text: str = "주택임대차보호법 제 3조 대항력"):
    vector = embed_text(text)

    return {
        "model": settings.ollama_embed_model,
        "text": text,
        "dimension": len(vector),
        "preview": vector[:5],
    }

@app.post("/admin/qdrant/index/chunks")
def index_chunks(limit: int = 100):
    chunks = list_chunks(limit)
    vectors = [embed_text(chunk.text) for chunk in chunks]

    result = upsert_chunk_vectors(
        chunks=chunks,
        vectors=vectors,
    )

    return {
        "status": "ok",
        "model": settings.ollama_embed_model,
        "chunks_count": len(chunks),
        **result,
    }

@app.get("/admin/retrieval/search")
def admin_retrieval_search(query: str, limit: int = 5):
    query_vector = embed_text(query)
    results = search_similar_chunks(
        query_vector=query_vector,
        limit=limit,
    )

    return {
        "status": "ok",
        "model": settings.ollama_embed_model,
        "query": query,
        "results": results
    }

@app.get("/admin/retrieval/search/context")
def admin_retrieval_search_with_context(query: str, limit: int = 5):
    query_vector = embed_text(query)

    results = search_similar_chunks(
        query_vector=query_vector,
        limit=limit,
    )

    enriched_results = []

    for result in results:
        payload = result.get("payload") or {}
        source_id = payload.get("source_id")

        context = get_article_context(source_id) if source_id else None

        enriched_results.append(
            {
                **result,
                "context": context,
            }
        )

    return {
        "status": "ok",
        "model": settings.ollama_embed_model,
        "query": query,
        "results": enriched_results,
    }

@app.get("/admin/answer")
def admin_answer(query: str, limit: int =3):
    query_vector = embed_text(query)

    results = search_similar_chunks(
        query_vector=query_vector,
        limit=limit,
    )

    enriched_results = []

    for result in results:
        payload = result.get("payload") or {}
        source_id = payload.get("source_id")

        context = get_article_context(source_id) if source_id else None

        enriched_results.append(
            {
                **result,
                "context": context,
            }
        )

    prompt = build_legal_answer_prompt(
        query=query,
        results=enriched_results,
    )

    answer = generate_answer(prompt)

    return {
        "status": "ok",
        "llm_model": settings.ollama_llm_model,
        "embed_model": settings.ollama_embed_model,
        "query": query,
        "answer": answer,
        "sources": enriched_results,
    }

def build_legal_answer_prompt(query: str, results: list[dict]) -> str:
    context_blocks = []

    for index, result in enumerate(results, start=1):
        context = result.get("context") or {}
        law = context.get("law") or {}
        article = context.get("article") or {}

        context_blocks.append(
            f"""
            [근거 {index}]
            법령명: {law.get("name")}
            조문: {article.get("article_no")} {article.get("title")}
            내용:
            {article.get("text")}
            """.strip()
        )

        context_text = "\n\n".join(context_blocks)

    return f"""
            너는 한국 법령 정보를 설명하는 법률 RAG assistant다.
            아래 제공된 근거만 사용해서 답변하라.
            근거에 없는 내용은 추측하지 말고, "제공된 근거만으로는 확인하기 어렵습니다"라고 말하라.
            답변은 일반 정보 제공이며, 법률 자문이 아니라는 점을 마지막에 짧게 밝혀라.
            [사용자 질문]
            {query}

            [검색된 근거]
            {context_text}

            [답변 형식]
            1. 결론
            2. 근거
            3. 참고 조문
            4. 유의사항
            """.strip()