from backend.app.models import Article, SourceType, TextChunk

def chunk_article(article: Article) -> list[TextChunk]:
    text = article.text.strip()

    if not text:
        return []
    
    chunk_text = build_article_chunk_text(article)

    return [
        TextChunk(
            id=f"{article.id}:chunk:0",
            source_type=SourceType.LAW,
            source_id=article.id,
            text=chunk_text,
            domain=article.domain,
            chunk_index=0,
            metadata={
                "law_id": article.law_id,
                "article_no": article.article_no,
                "title": article.title,
                "effective_date": (
                    article.effective_date.isoformat()
                    if article.effective_date
                    else None
                ),
            },
        )
    ]

def build_article_chunk_text(article: Article) -> str:
    parts = []

    parts.append(article.article_no)

    if article.title:
        parts.append(f"({article.title})")

    parts.append(article.text)

    return " ".join(parts)

def chunk_articles(articles: list[Article]) -> list[TextChunk]:
    chunks: list[TextChunk] = []

    for article in articles:
        chunks.extend(chunk_article(article))

    return chunks