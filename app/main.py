from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from routes import query, search, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (e.g., connect to Qdrant, Redis)
    print(f"Starting {settings.PROJECT_NAME}...")
    from services.semantic_cache import semantic_cache
    await semantic_cache.init_index()
    yield
    # Shutdown logic
    print(f"Shutting down {settings.PROJECT_NAME}...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    debug=settings.DEBUG
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(query.router, prefix=settings.API_V1_STR + "/query", tags=["Query"])
app.include_router(search.router, prefix=settings.API_V1_STR + "/search", tags=["Search"])

@app.get("/")
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}", "version": "0.1.0"}
