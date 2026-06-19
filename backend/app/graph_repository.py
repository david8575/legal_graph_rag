import json

from neo4j import GraphDatabase

from backend.app.config import settings
from backend.app.models import Article, Law, TextChunk


def get_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def upsert_law(tx, law: Law) -> None:
    tx.run(
        """
        MERGE (l:Law {id: $id})
        SET l.name = $name,
            l.domain = $domain,
            l.jurisdiction = $jurisdiction,
            l.effective_date = $effective_date,
            l.collected_at = $collected_at,
            l.source = $source,
            l.metadata = $metadata
        """,
        id=law.id,
        name=law.name,
        domain=law.domain.value,
        jurisdiction=law.jurisdiction,
        effective_date=law.effective_date.isoformat() if law.effective_date else None,
        collected_at=law.collected_at.isoformat(),
        source=law.source,
        metadata=json.dumps(law.metadata, ensure_ascii=False),
    )


def upsert_article(tx, article: Article) -> None:
    tx.run(
        """
        MERGE (a:Article {id: $id})
        SET a.law_id = $law_id,
            a.article_no = $article_no,
            a.title = $title,
            a.text = $text,
            a.domain = $domain,
            a.effective_date = $effective_date
        """,
        id=article.id,
        law_id=article.law_id,
        article_no=article.article_no,
        title=article.title,
        text=article.text,
        domain=article.domain.value,
        effective_date=article.effective_date.isoformat() if article.effective_date else None,
    )


def link_law_article(tx, law_id: str, article_id: str) -> None:
    tx.run(
        """
        MATCH (l:Law {id: $law_id})
        MATCH (a:Article {id: $article_id})
        MERGE (l)-[:HAS_ARTICLE]->(a)
        """,
        law_id=law_id,
        article_id=article_id,
    )


def save_law_with_articles(law: Law, articles: list[Article]) -> dict:
    driver = get_driver()

    try:
        with driver.session() as session:
            session.execute_write(upsert_law, law)

            for article in articles:
                session.execute_write(upsert_article, article)
                session.execute_write(link_law_article, law.id, article.id)

        return {
            "law_id": law.id,
            "articles_count": len(articles),
        }
    finally:
        driver.close()

def upsert_chunk(tx, chunk: TextChunk) -> None:
    tx.run(
        """
        MERGE (ch:Chunk {id: $id})
        SET ch.source_type = $source_type,
            ch.source_id = $source_id,
            ch.text = $text,
            ch.domain = $domain,
            ch.chunk_index = $chunk_index,
            ch.metadata = $metadata
        """,
        id=chunk.id,
        source_type=chunk.source_type.value,
        source_id=chunk.source_id,
        text=chunk.text,
        domain=chunk.domain.value,
        chunk_index=chunk.chunk_index,
        metadata=json.dumps(chunk.metadata, ensure_ascii=False),
    )

def link_article_chunk(tx, article_id: str, chunk_id: str) -> None:
    tx.run(
        """
        MATCH (a:Article {id: $article_id})
        MATCH (ch:Chunk {id: $chunk_id})
        MERGE (a)-[:HAS_CHUNK]->(ch)
        """,
        article_id=article_id,
        chunk_id=chunk_id,
    )

def save_chunks(chunks: list[TextChunk]) -> dict:
    driver = get_driver()

    try:
        with driver.session() as session:
            for chunk in chunks:
                session.execute_write(upsert_chunk, chunk)
                session.execute_write(link_article_chunk, chunk.source_id, chunk.id)

        return {
            "chunks_count": len(chunks),
        }
    finally:
        driver.close()

def list_chunks(limit: int = 100) -> list[TextChunk]:
    driver = get_driver()

    try:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (ch:Chunk)
                RETURN ch.id AS id,
                       ch.source_type AS source_type,
                       ch.source_id AS source_id,
                       ch.text AS text,
                       ch.domain AS domain,
                       ch.chunk_index AS chunk_index,
                       ch.metadata AS metadata
                ORDER BY ch.id
                LIMIT $limit
                """,
                limit=limit,
            )

            chunks: list[TextChunk] = []

            for record in result:
                metadata = json.loads(record["metadata"]) if record["metadata"] else {}

                chunks.append(
                    TextChunk(
                        id=record["id"],
                        source_type=record["source_type"],
                        source_id=record["source_id"],
                        text=record["text"],
                        domain=record["domain"],
                        chunk_index=record["chunk_index"],
                        metadata=metadata,
                    )
                )

            return chunks
    finally:
        driver.close()

def get_article_context(article_id: str) -> dict | None:
    driver = get_driver()

    try:
        with driver.session() as session:
            record = session.run(
                """
                MATCH (l:Law)-[:HAS_ARTICLE]->(a:Article {id: $article_id})
                RETURN
                    l.id AS law_id,
                    l.name AS law_name,
                    l.domain AS law_domain,
                    l.source AS law_source,
                    a.id AS article_id,
                    a.article_no AS article_no,
                    a.title AS article_title,
                    a.text AS article_text,
                    a.domain AS article_domain,
                    a.effective_date AS article_effective_date
                """,
                article_id=article_id,
            ).single()

            if record is None:
                return None

            return {
                "law": {
                    "id": record["law_id"],
                    "name": record["law_name"],
                    "domain": record["law_domain"],
                    "source": record["law_source"],
                },
                "article": {
                    "id": record["article_id"],
                    "article_no": record["article_no"],
                    "title": record["article_title"],
                    "text": record["article_text"],
                    "domain": record["article_domain"],
                    "effective_date": record["article_effective_date"],
                },
            }
    finally:
        driver.close()