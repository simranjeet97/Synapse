import asyncio
import json
from typing import List, Dict, Any, Union
import google.generativeai as genai
from app.config import settings
from app.models import RetrievedDoc, SearchResult, GradingResult, AgentResponse, RefusalResponse
from services.query_decomposer import query_decomposer
from retrieval.hybrid_retriever import hybrid_retriever
from .tools.web_search import web_search_tool

class CRAGAgent:
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def _grade_doc(self, query: str, doc: str) -> GradingResult:
        prompt = f"""Rate this document's relevance to the query. 
Return ONLY JSON: {{"relevance": "correct"|"ambiguous"|"incorrect", "confidence": float, "reason": str}}

Query: {query}
Document: {doc}
"""
        try:
            # genai library doesn't have a direct async call in the same way, but we can use run_in_executor
            # or just call it since it's an agent loop. For production we'd use a wrapper.
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
                )
            )
            data = json.loads(response.text)
            return GradingResult(**data)
        except Exception as e:
            print(f"Grading error: {e}")
            return GradingResult(relevance="incorrect", confidence=0.0, reason=str(e))

    async def run(self, query: str, retrieved_docs: List[RetrievedDoc], session_id: str) -> Union[AgentResponse, RefusalResponse]:
        print(f"CRAG: Grading {len(retrieved_docs)} documents using Gemini...")
        
        # Step 1: Parallel grading
        grading_tasks = [self._grade_doc(query, doc.content) for doc in retrieved_docs[:5]]
        grading_results = await asyncio.gather(*grading_tasks)
        
        correct_docs = [doc for doc, res in zip(retrieved_docs, grading_results) if res.relevance == "correct"]
        ambiguous_docs = [doc for doc, res in zip(retrieved_docs, grading_results) if res.relevance == "ambiguous"]
        
        # Step 2: Branching
        if len(correct_docs) >= 3:
            print("CRAG: Correct path selected.")
            return await self._generate_answer(query, correct_docs)
            
        elif len(ambiguous_docs) > 0 or (len(correct_docs) < 3 and len(correct_docs) > 0):
            print("CRAG: Ambiguous path selected. Decomposing query...")
            sub_queries = await query_decomposer.decompose(query)
            
            all_new_docs = []
            for sub_q in sub_queries:
                new_docs = await hybrid_retriever.search(sub_q, limit=5)
                all_new_docs.extend(new_docs)
            
            # Merge unique by ID
            unique_docs = {doc.id: doc for doc in all_new_docs}.values()
            return await self.run(query, list(unique_docs), session_id) # Recursive re-grade
            
        else:
            print("CRAG: Incorrect path selected. Triggering web search...")
            web_results = await web_search_tool.run(query)
            if not web_results:
                return RefusalResponse()
                
            # Re-grade web results
            web_grading_tasks = [self._grade_doc(query, doc.content) for doc in web_results]
            web_grading_results = await asyncio.gather(*web_grading_tasks)
            
            final_docs = [doc for doc, res in zip(web_results, web_grading_results) if res.relevance in ["correct", "ambiguous"]]
            
            if not final_docs:
                return RefusalResponse()
                
            return await self._generate_answer(query, final_docs)

    async def _generate_answer(self, query: str, docs: List[SearchResult]) -> AgentResponse:
        context = "\n\n".join([f"Source [{i+1}]: {d.content}" for i, d in enumerate(docs)])
        prompt = f"""Use the following context to answer the question. Include citations like [1], [2].
        
Context: {context}
Question: {query}
"""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
        
        return AgentResponse(
            answer=response.text,
            sources=docs
        )

crag_agent = CRAGAgent()
