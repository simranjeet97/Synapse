import redis.asyncio as redis
import json
import hashlib
from typing import Optional, List
from app.config import settings
from app.models import SearchResult, CachedResponse

class SemanticCache:
    def __init__(self):
        self.redis = None
        self.local_cache = {} # Fallback
        self.is_connected = False
        
        try:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # We'll check connection during first lookup to avoid startup crash
        except Exception as e:
            print(f"SemanticCache: Failed to init Redis: {e}. Using in-memory fallback.")

    async def _check_conn(self):
        if self.is_connected:
            return True
        if not self.redis:
            return False
        try:
            await self.redis.ping()
            self.is_connected = True
            return True
        except Exception:
            self.is_connected = False
            return False

    async def init_index(self):
        # No-op for the local fallback/simple Redis mode
        pass

    async def lookup(self, query: str, threshold: float = 0.92) -> Optional[CachedResponse]:
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        
        if await self._check_conn():
            try:
                data = await self.redis.get(f"cache:{query_hash}")
                if data:
                    cached = json.loads(data)
                    return CachedResponse(**cached)
            except Exception:
                pass
        
        # Fallback to local
        return self.local_cache.get(query_hash)

    async def get(self, query: str, threshold: float = 0.92) -> Optional[CachedResponse]:
        return await self.lookup(query, threshold)

    async def store(self, query: str, response: CachedResponse, ttl: int = 3600):
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        
        if await self._check_conn():
            try:
                await self.redis.setex(
                    f"cache:{query_hash}",
                    ttl,
                    response.model_dump_json()
                )
            except Exception:
                pass
        
        self.local_cache[query_hash] = response

    async def set(self, query: str, response: CachedResponse, ttl: int = 3600):
        await self.store(query, response, ttl)

semantic_cache = SemanticCache()
