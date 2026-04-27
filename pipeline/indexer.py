import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List
from app.config import settings
from app.models import Chunk, DocumentMetadata
from datetime import datetime
import spacy
import os

class ChromaIndexer:
    def __init__(self):
        # Use local persistence only
        persist_directory = os.path.join(os.getcwd(), "chroma_db")
        self.client = chromadb.PersistentClient(path=persist_directory)
        print(f"Chroma: Using local persistent storage at {persist_directory}")

        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        self.nlp = spacy.load("en_core_web_sm")

    def _extract_entities(self, text: str) -> List[str]:
        doc = self.nlp(text[:1000])
        return list(set([ent.text for ent in doc.ents]))

    async def upsert_chunks(self, chunks: List[Chunk]):
        await self.index_chunks(chunks)

    async def index_chunks(self, chunks: List[Chunk]):
        if not chunks:
            return
            
        ids = [c.id for c in chunks]
        documents = [c.content for c in chunks]
        embeddings = [c.embedding for c in chunks]
        metadatas = []

        for c in chunks:
            meta = c.metadata.model_dump()
            # Convert datetime to string for Chroma
            for k, v in meta.items():
                if isinstance(v, datetime):
                    meta[k] = v.isoformat()
            
            meta["entities"] = ",".join(self._extract_entities(c.content))
            metadatas.append(meta)

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        print(f"Chroma: Indexed {len(chunks)} chunks into collection {settings.CHROMA_COLLECTION_NAME}")

indexer = ChromaIndexer()
