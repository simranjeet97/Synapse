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
        persist_directory = os.path.join(os.getcwd(), "chroma_db")
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
            
        self.collection = self.chroma_client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)
        self.redis = redis.from_url(settings.REDIS_URL)

    async def _dense_search(self, query_vec: List[float], limit: int, filters: Optional[FilterParams]) -> List[SearchResult]:
        where = {}
        if filters:
            conditions = []
            if filters.source_type:
                conditions.append({"source_type": filters.source_type})
            
            # Date range filtering (assuming metadata 'date' is ISO string)
            if filters.date_gte:
                conditions.append({"date": {"$gte": filters.date_gte}})
            if filters.date_lte:
                conditions.append({"date": {"$lte": filters.date_lte}})
                
            if len(conditions) > 1:
                where = {"$and": conditions}
            elif len(conditions) == 1:
                where = conditions[0]
        
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=limit, # Get more if we need to post-filter entities
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        docs = []
        if results["ids"] and len(results["ids"]) > 0:
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                
                # Post-retrieval filtering for entities
                # Since 'entities' is stored as a string "Entity1,Entity2"
                if filters and filters.entity_names:
                    doc_entities = metadata.get("entities", "").split(",")
                    doc_entities = [e.strip() for e in doc_entities if e.strip()]
                    # Check if any requested entity is in the document
                    if not any(e in doc_entities for e in filters.entity_names):
                        continue

                docs.append(SearchResult(
                    id=results["ids"][0][i],
                    content=results["documents"][0][i],
                    metadata=metadata,
                    score=1.0 - results["distances"][0][i]
                ))
        return docs

    async def _sparse_search(self, query: str, limit: int) -> List[SearchResult]:
        try:
            bm25_data = await self.redis.get("bm25:corpus")
            if not bm25_data:
                return []
            
            # Data is pickled as (bm25, list_of_dicts_with_content_and_metadata)
            bm25, doc_data = pickle.loads(bm25_data)
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)
            
            # Sort and get top results
            import numpy as np
            top_indices = np.argsort(scores)[::-1][:limit]
            
            results = []
            for i in top_indices:
                if scores[i] > 0:
                    results.append(SearchResult(
                        id=f"sparse_{i}",
                        content=doc_data[i]["content"],
                        metadata=doc_data[i]["metadata"],
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
