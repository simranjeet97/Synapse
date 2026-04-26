from fastapi import APIRouter, Query
from typing import List
from app.models import RetrievedDoc
from retrieval.hybrid_retriever import hybrid_retriever
from retrieval.reranker import cohere_reranker

router = APIRouter()

@router.get("/")
async def debug_search(
    q: str = Query(..., min_length=1),
    top_k: int = 10
):
    """Debug endpoint to inspect raw retrieval and reranking scores."""
    # 1. Hybrid Retrieval
    raw_results = await hybrid_retriever.search(q, limit=20)
    
    # 2. Reranking
    reranked_results = await cohere_reranker.rerank(q, raw_results, top_n=top_k)
    
    return {
        "query": q,
        "results": reranked_results
    }
