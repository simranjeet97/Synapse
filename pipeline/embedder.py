import pickle
import redis
from typing import List
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from app.config import settings

class Embedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.redis = redis.from_url(settings.REDIS_URL)
        self.batch_size = 64
        self.bm25_key = "bm25:corpus"

    def embed_batches(self, texts: List[str]) -> List[List[float]]:
        # Encode in batches
        embeddings = self.model.encode(
            texts, 
            batch_size=self.batch_size, 
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.tolist()

    def build_bm25_index(self, chunks: List[str], metadata: List[dict]):
        """Build and serialize BM25 index to Redis."""
        tokenized_corpus = [doc.lower().split() for doc in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        
        # Pickle both index and associated metadata (corpus docs)
        data = pickle.dumps((bm25, metadata))
        self.redis.set(self.bm25_key, data)
        print("Embedder: BM25 index updated in Redis.")

embedder = Embedder()
