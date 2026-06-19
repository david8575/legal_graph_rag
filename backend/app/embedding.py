import httpx

from backend.app.config import settings

def embed_text(text: str) -> list[float]:
    response = httpx.post(
        f"{settings.ollama_base_url}/api/embed",
        json = {
            "model": settings.ollama_embed_model,
            "input": text,
        },
        timeout=60.0,
    )

    response.raise_for_status()

    data = response.json()
    embeddings = data["embeddings"]

    if not embeddings:
        raise ValueError("Ollama Returned No Embeddings")
    
    return embeddings[0]