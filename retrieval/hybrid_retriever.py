import chromadb
import asyncio
import redis.asyncio as redis
import pickle
import os
from typing import List, Optional
from app.config import settings
from app.models import RetrievedDoc, FilterParams, SearchResult
from pipeline.embedder import embedder

class ChromaHybridRetriever:
    def __init__(self):
        try:
            self.chroma_client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )
            self.chroma_client.heartbeat()
        except Exception:
            persist_directory = os.path.join(os.getcwd(), "chroma_db")
            self.chroma_client = chromadb.PersistentClient(path=persist_directory)
            
        self.collection = self.chroma_client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)
        self.redis = redis.from_url(settings.REDIS_URL)

    async def _dense_search(self, query_vec: List[float], limit: int, filters: Optional[FilterParams]) -> List[SearchResult]:
        where = {}
        if filters:
            if filters.source_type:
                where["source_type"] = filters.source_type
        
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        docs = []
        if results["ids"]:
            for i in range(len(results["ids"][0])):
                docs.append(SearchResult(
                    id=results["ids"][0][i],
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i],
                    score=1.0 - results["distances"][0][i]
                ))
        return docs

    async def _sparse_search(self, query: str, limit: int) -> List[SearchResult]:
        try:
            bm25_data = await self.redis.get("bm25:corpus")
            if not bm25_data:
                return []
            
            # Data is pickled as (bm25, metadata)
            bm25, metadatas = pickle.loads(bm25_data)
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)
            
            # Sort and get top results
            import numpy as np
            top_indices = np.argsort(scores)[::-1][:limit]
            
            results = []
            for i in top_indices:
                if scores[i] > 0:
                    # In a real system, we'd fetch the actual doc content. 
                    # For this skeleton, we assume metadatas[i] has what we need or we return a placeholder.
                    # Usually BM25 stores the doc content or we fetch from DB.
                    results.append(SearchResult(
                        content=f"BM25 Result {i}", # Placeholder as content is not in BM25 index normally
                        metadata=metadatas[i],
                        score=float(scores[i])
                    ))
            return results
        except Exception as e:
            print(f"Sparse search error: {e}")
            return []

    async def search(self, query: str, limit: int = 10, filters: Optional[FilterParams] = None) -> List[RetrievedDoc]:
        query_vec = await embedder.embed_text(query)
        
        # Get results from both
        dense_results = await self._dense_search(query_vec, limit=50, filters=filters)
        sparse_results = await self._sparse_search(query, limit=50)
        
        # RRF Merging
        k = 60
        scores = {} # id -> rrf_score
        docs = {}   # id -> doc
        
        for i, res in enumerate(dense_results):
            doc_id = res.id or f"dense_{i}"
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + i + 1)
            docs[doc_id] = res
            
        for i, res in enumerate(sparse_results):
            doc_id = res.id or f"sparse_{i}"
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + i + 1)
            if doc_id not in docs:
                docs[doc_id] = res
                
        # Sort by RRF score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        fused_results = []
        for doc_id in sorted_ids[:limit]:
            res = docs[doc_id]
            fused_results.append(RetrievedDoc(
                id=doc_id,
                content=res.content,
                metadata=res.metadata,
                dense_score=getattr(res, 'score', 0.0),
                bm25_score=0.0, # Placeholder
                rrf_score=scores[doc_id]
            ))
            
        return fused_results

hybrid_retriever = ChromaHybridRetriever()
