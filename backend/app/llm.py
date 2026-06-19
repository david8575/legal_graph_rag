import httpx
from backend.app.config import settings

def generate_answer(prompt: str) -> str:
    response = httpx.post(
        f"{settings.ollama_base_url}/api/generate",
        json = {
            "model": settings.ollama_llm_model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120.0
    )

    response.raise_for_status()

    data = response.json()

    return data["response"]