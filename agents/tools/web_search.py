from typing import List
from app.models import SearchResult

class WebSearchTool:
    async def run(self, query: str) -> List[SearchResult]:
        print(f"Tool: Web Search for '{query}'")
        # In production, use Tavily or Brave Search API
        return [
            SearchResult(
                content=f"Web search result for {query}",
                metadata={"source": "web", "url": "https://example.com"},
                score=0.85
            )
        ]

web_search_tool = WebSearchTool()
