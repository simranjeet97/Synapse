import os
import magic
from typing import List
from app.models import Chunk, DocumentMetadata
from .extractors.pdf_extractor import pdf_extractor
from .extractors.html_extractor import html_extractor
from .extractors.docx_extractor import docx_extractor
from .extractors.image_extractor import image_extractor
from .extractors.text_extractor import text_extractor
from .preprocessor import preprocessor
from .deduplicator import deduplicator
from .chunker import chunker
from .embedder import embedder
from .indexer import indexer

class IngestionPipeline:
    def __init__(self):
        self.mime = magic.Magic(mime=True)

    async def process_file(self, file_path: str):
        print(f"Starting ingestion for: {file_path}")
        
        # 1. Detect MIME Type
        mime_type = self.mime.from_file(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        print(f"MIME Type: {mime_type}, Extension: {ext}")
        
        # 2. Extract
        if mime_type == 'application/pdf':
            content = pdf_extractor.extract(file_path)
        elif mime_type == 'text/html':
            with open(file_path, 'r') as f:
                content = html_extractor.extract(f.read())
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            content = docx_extractor.extract(file_path)
        elif mime_type.startswith('image/'):
            content = image_extractor.extract(file_path)
        else:
            content = text_extractor.extract(file_path)
            
        # 3. Preprocess
        # For simplicity, we treat the whole content as one "page" for now
        # In a real system, extractors would return a List[str] of pages
        pages = [content]
        clean_pages = preprocessor.strip_headers_footers(pages)
        full_content = "\n".join([preprocessor.normalize(p) for p in clean_pages])
        
        # 4. Deduplicate (Near-Dedup)
        if deduplicator.is_duplicate(full_content, doc_id=file_path):
            print(f"Skipping duplicate file: {file_path}")
            return
            
        # 5. Chunk
        chunk_texts = chunker.split_text(full_content, file_ext=ext)
        print(f"Split into {len(chunk_texts)} chunks.")
        
        # 6. Embed (Dense)
        vectors = embedder.embed_batches(chunk_texts)
        
        # 7. Create Chunk objects and Index (Chroma)
        doc_metadata = DocumentMetadata(
            title=os.path.basename(file_path),
            source_url=file_path,
            source_type=ext.replace(".", "") or "text"
        )
        
        chunks = []
        for i, (text, vec) in enumerate(zip(chunk_texts, vectors)):
            chunks.append(Chunk(
                id=f"{file_path}_{i}",
                content=text,
                embedding=vec,
                metadata=doc_metadata
            ))
            
        await indexer.upsert_chunks(chunks)
        
        # 8. Update BM25 Index (Redis)
        embedder.build_bm25_index(chunk_texts, [doc_metadata.model_dump() for _ in chunk_texts])
        
        print(f"Ingestion complete for: {file_path}")

ingest_pipeline = IngestionPipeline()
