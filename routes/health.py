from fastapi import APIRouter, HTTPException
import chromadb
import redis.asyncio as redis
from app.config import settings

router = APIRouter()

@router.get("/")
async def health_check():
    health_status = {
        "chroma": "unknown",
        "redis": "unknown",
        "model": "healthy" # Simplified for this demo
    }
    
    # 1. Check Chroma
    try:
        from pipeline.indexer import chroma_indexer
        chroma_indexer.client.heartbeat()
        health_status["chroma"] = "healthy"
    except Exception as e:
        health_status["chroma"] = f"unhealthy: {str(e)}"

    # 2. Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"

    return health_status

@router.get("/ready")
async def readiness_check():
    try:
        # We allow readiness even if Redis is down (using local mode)
        # but Chroma must at least be initialized
        from pipeline.indexer import chroma_indexer
        chroma_indexer.client.heartbeat()
        return {"status": "ready"}
    except Exception as e:
        # If even local chroma fails, then not ready
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")
