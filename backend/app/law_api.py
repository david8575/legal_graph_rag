import httpx
from datetime import datetime
from typing import Any
import xml.etree.ElementTree as ET

from backend.app.models import Law, LegalDomain, Article
from backend.app.config import settings


LAW_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
LAW_DETAIL_URL = "https://www.law.go.kr/DRF/lawService.do"

def search_laws(query: str, display: int = 10, page: int = 1) -> dict:
    params = {
        "OC": settings.law_api_key,
        "target": "law",
        "type": "JSON",
        "query": query,
        "display": display,
        "page": page, 
    }

    headers = {
        "user-agent": "legal-graph-rag/0.1.0"
    }

    response = httpx.get(
        LAW_SEARCH_URL,
        params=params,
        headers=headers,
        timeout=15.0,
        follow_redirects=True
    )

    response.raise_for_status()

    return response.json()

def parse_yyyymmdd(value: str):
    if not value:
        return None
    
    return datetime.strptime(value, "%Y%m%d").date()

def normalize_law_search_result(item: dict[str, Any]) -> Law:
    mst = item["법령일련번호"]

    return Law(
        id=f"law:{mst}",
        name=item["법령명한글"],
        domain=LegalDomain.REAL_ESTATE_LEASE,
        source="law.go.kr",
        effective_date=parse_yyyymmdd(item.get("시행일자", "")),  
        metadata={
            "mst": mst,
            "law_id": item.get("법령ID"),
            "law_type": item.get("법령구분명"),
            "ministry": item.get("소관부처명"),
            "promulgation_date": item.get("공포일자"),
            "detail_link": item.get("법령상세링크"),
            "short_name": item.get("법령약칭명"),
        },      
    )

def normalize_law_search_response(data: dict[str, Any]) -> list[Law]:
    law_search = data.get("LawSearch", {})
    laws = law_search.get("law", [])

    if isinstance(laws, dict):
        laws = [laws]

    return [normalize_law_search_result(item) for item in laws]

def get_law_detail_xml(mst: str) -> str:
    params = {
        "OC": settings.law_api_key,
        "target": "law",
        "MST": mst,
        "type": "XML",
    }

    headers = {
        "User-Agent": "legal-graph-rag/0.1.0",
    }

    response = httpx.get(
        LAW_DETAIL_URL,
        params=params,
        headers=headers,
        timeout=15.0,
        follow_redirects=True,
    )

    response.raise_for_status()

    return response.text

def get_text(element: ET.Element, tag: str) -> str:
    child = element.find(tag)

    if child is None or child.text is None:
        return ""
    
    return child.text.strip()

def build_article_no(article_element:ET.Element) -> str:
    article_no = get_text(article_element, "조문번호")
    branch_no = get_text(article_element, "조문가지번호")
    
    if branch_no and branch_no != "0":
        return f"제{article_no}조의{branch_no}"
    
    return f"제{article_no}조"

def normalize_law_detail_articles(
        xml_text: str,
        law_id: str,
        domain: LegalDomain = LegalDomain.REAL_ESTATE_LEASE) -> list[Article]:
    root = ET.fromstring(xml_text)

    articles: list[Article] = []

    for article_element in root.findall(".//조문단위"):
        article_no = build_article_no(article_element)
        title = get_text(article_element, "조문제목") or None
        text = build_article_text(article_element)
        effective_date = parse_yyyymmdd(get_text(article_element, "조문시행일자"))

        if not text:
            continue

        article_id = f"{law_id}:article:{article_no}"

        articles.append(
            Article(
                id=article_id,
                law_id=law_id,
                article_no=article_no,
                title=title,
                text=text,
                domain=domain,
                effective_date=effective_date,
            )
        )

    return articles

def build_article_text(article_element: ET.Element) -> str:
    parts = []

    article_text = get_text(article_element, "조문내용")
    if article_text:
        parts.append(article_text)

    for paragraph in article_element.findall(".//항"):
        paragraph_text = get_text(paragraph, "항내용")
        if paragraph_text:
            parts.append(paragraph_text)

        for item in paragraph.findall(".//호"):
            item_text = get_text(item, "호내용")
            if item_text:
                parts.append(item_text)

    return "\n".join(parts).strip()