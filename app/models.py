from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from retrieval.filters import FilterParams

class DocumentMetadata(BaseModel):
    title: str
    source_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_type: str # 'pdf' | 'web' | 'doc'
    
from typing import List, Optional, Dict, Any, Literal

class CitationEdge(BaseModel):
    source_doc_id: str
    target_doc_id: str
    citation_type: Literal['hyperlink', 'crossref', 'footnote']
    weight: float
    raw_text: str

class Chunk(BaseModel):
    id: str
    content: str
    embedding: List[float]
    metadata: DocumentMetadata

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: str = Field(..., description="Unique ID for the conversation session")
    filters: Optional[FilterParams] = None
    stream: bool = Field(True)
    use_sharding: bool = Field(False)

class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float
    id: Optional[str] = None

class RetrievedDoc(SearchResult):
    dense_score: Optional[float] = 0.0
    bm25_score: Optional[float] = 0.0
    rrf_score: Optional[float] = 0.0
    pagerank_score: Optional[float] = 0.0
    boosted_score: Optional[float] = 0.0

class Message(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CachedResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GradingResult(BaseModel):
    relevance: str # 'correct' | 'ambiguous' | 'incorrect'
    confidence: float
    reason: str

class AgentResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    grading_summary: Optional[Dict[str, Any]] = None

class RefusalResponse(BaseModel):
    message: str = "I could not find reliable information to answer this question."

class CRAGResult(BaseModel):
    documents: List[SearchResult]
    path: str # 'correct' | 'ambiguous' | 'incorrect'
    reason: Optional[str] = None

class PipelineTrace(BaseModel):
    latencies: Dict[str, float]
    model: str
    cache_hit: bool
    crag_path: str
    shard_stats: Optional[Dict[str, Any]] = None

class FinalQueryResponse(BaseModel):
    token: str = ""
    sources: List[SearchResult]
    trace: PipelineTrace
    done: bool = True

class QueryResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    conversation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class HealthCheck(BaseModel):
    status: str
    version: str
    services: Dict[str, str]

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
