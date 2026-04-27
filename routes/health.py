from fastapi import APIRouter, HTTPException
import chromadb
import redis.asyncio as redis
from app.config import settings

router = APIRouter()

@router.get("/")
async def health_check():
    health_status = {
        "status": "healthy",
        "chroma": "unknown",
        "redis": "unknown",
        "model": "healthy"
    }
    
    # 1. Check Chroma
    try:
        from pipeline.indexer import indexer
        indexer.client.heartbeat()
        health_status["chroma"] = "healthy"
    except Exception as e:
        health_status["chroma"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # 2. Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
        # We don't mark the whole app as unhealthy if Redis is down, 
        # as it can run without semantic cache.
        # But for this demo, let's stick to strict health if needed.
        # health_status["status"] = "unhealthy"

    return health_status

@router.get("/ready")
async def readiness_check():
    try:
        from pipeline.indexer import indexer
        indexer.client.heartbeat()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")
