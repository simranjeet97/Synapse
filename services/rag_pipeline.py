from typing import List, Optional, Dict, Any, Union
from app.models import SearchResult, QueryResponse, CachedResponse, Message, AgentResponse, RefusalResponse
from retrieval.hybrid_retriever import hybrid_retriever
from agents.crag import crag_agent
from agents.adaptive_router import adaptive_router
from security.input_guard import input_guard
from security.content_filter import content_filter
from security.output_guard import output_guard
from .semantic_cache import semantic_cache
from .conversation import conversation_memory
from datetime import datetime

class RAGPipeline:
    async def run(self, query: str, conversation_id: Optional[str] = None, filters: Optional[Dict[str, Any]] = None) -> Union[QueryResponse, RefusalResponse]:
        # 1. Security Check (Input)
        guard_res = await input_guard.inspect(query)
        if not guard_res.safe:
            return QueryResponse(
                answer=f"Security Alert: {guard_res.reason}",
                sources=[],
                conversation_id=conversation_id or "security-error"
            )

        # 2. Context Awareness & Query Rewriting
        conv_id = conversation_id or "default-session"
        rewritten_query = await conversation_memory.rewrite_query(conv_id, query)

        # 3. Semantic Cache Check
        cached = await semantic_cache.get(rewritten_query)
        if cached:
            return QueryResponse(
                answer=cached.answer,
                sources=cached.sources,
                conversation_id=conv_id
            )

        # 4. Adaptive Routing
        route_config = await adaptive_router.classify_and_route(rewritten_query)
        
        # 5. Retrieval
        raw_results = await hybrid_retriever.search(
            rewritten_query, 
            limit=route_config["top_k"], 
            filters=filters
        )
        
        # 5b. Content Filtering (Source, Toxicity, Relevance)
        from pipeline.embedder import embedder
        query_vec = await embedder.embed_text(rewritten_query)
        
        # Convert RetrievedDoc to SearchResult for the filter if necessary, 
        # but RetrievedDoc has content, metadata, and score (dense_score).
        # We'll map them to SearchResult objects for the filter.
        search_results = [
            SearchResult(
                id=doc.id,
                content=doc.content,
                metadata=doc.metadata,
                score=doc.dense_score
            ) for doc in raw_results
        ]
        
        filtered_results = await content_filter.validate_results(query_vec, search_results)
        
        # Convert back to RetrievedDoc for CRAG
        final_docs = [
            RetrievedDoc(
                id=res.id,
                content=res.content,
                metadata=res.metadata,
                dense_score=res.score,
                rrf_score=0.0 # Placeholder
            ) for res in filtered_results
        ]

        # 6. CRAG (Corrective RAG) Agent
        # This handles grading, web search fallback, and generation
        agent_res = await crag_agent.run(rewritten_query, final_docs, conv_id)
        
        if isinstance(agent_res, RefusalResponse):
            return agent_res

        # 7. Security Check (Output / PII Redaction)
        redacted_answer, entity_types = output_guard.redact(agent_res.answer)
        
        # 8. Update Cache & Conversation Memory
        await semantic_cache.set(rewritten_query, CachedResponse(
            answer=redacted_answer,
            sources=agent_res.sources,
            created_at=datetime.utcnow()
        ))
        
        await conversation_memory.add_message(conv_id, Message(role="user", content=query))
        await conversation_memory.add_message(conv_id, Message(role="assistant", content=redacted_answer))
        
        return QueryResponse(
            answer=redacted_answer,
            sources=agent_res.sources,
            conversation_id=conv_id
        )

rag_pipeline = RAGPipeline()
