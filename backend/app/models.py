from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

class LegalDomain(str, Enum):
    REAL_ESTATE_LEASE = "real_estate_lease"

class SourceType(str, Enum):
    LAW = "law"
    CASE = "case"

class Law(BaseModel):
    """
    법률 전체
    ex) 주택임대차보호법, 상가건물 임대차보호법, 민법
    """
    id: str
    name: str
    domain: LegalDomain
    jurisdiction: str = "KR"
    effective_date: Optional[date] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    source: str
    metadata: dict = Field(default_factory=dict)

class Article(BaseModel):
    """
    법률 안의 조문
    ex) 주택임대차보호법 제3조, 상가건물 임대차보호법 제10조
    """
    id: str
    law_id: str
    article_no: str
    title: Optional[str] = None
    text: str
    domain: LegalDomain
    effective_date: Optional[date] = None

class LegalCase(BaseModel):
    """
    판례
    """
    id: str
    case_name: Optional[str] = None
    court_name: Optional[str] = None
    decision_date: Optional[date] = None
    case_number: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    domain: LegalDomain
    source: str


class Issue(BaseModel):
    """
    법적 쟁점
    ex) 보증금 반환, 묵시적 갱신, 대항력, 우선변제권, 권리금 회수기회
    """
    id: str
    name: str
    description: Optional[str] = None
    domain: LegalDomain


class TextChunk(BaseModel):
    """
    검색 단위
    Qdrant에 들어갈 텍스트 조합
    """
    id: str
    source_type: SourceType
    source_id: str
    text: str
    domain: LegalDomain
    chunk_index: int
    metadata: dict = Field(default_factory=dict)
