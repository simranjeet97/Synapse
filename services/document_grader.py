from typing import List
from app.models import SearchResult

class DocumentGrader:
    async def grade_relevance(self, query: str, document: str) -> bool:
        # LLM-based grading logic would go here
        print(f"Grading document relevance for query: {query}")
        return True # Default to True for skeleton

    async def filter_irrelevant(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        filtered = []
        for res in results:
            if await self.grade_relevance(query, res.content):
                filtered.append(res)
        return filtered

document_grader = DocumentGrader()
