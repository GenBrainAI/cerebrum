from typing import List, Dict, Any, Optional, Generator
import asyncio
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor
import backoff
from tqdm.asyncio import tqdm
import numpy as np
from .vector_store import VectorStore
from .vector_store import VectorStoreConfig
class ContextDatabase:
    """Enhanced version of the context database with better error handling and performance."""
    
    def __init__(self, persist_directory: str="./context_db", batch_size: int = 100):
        self.persist_directory = persist_directory
        self.batch_size = batch_size
        self._setup_logging()
        self._initialize_collections()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.vector_store = VectorStore(
            VectorStoreConfig(
                persist_directory=persist_directory,
                collection_name="code_context",
                embedding_model="text-embedding-3-small"
            )
        )

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def _initialize_collections(self):
        from .vector_store import VectorStoreConfig
        config = VectorStoreConfig(persist_directory=self.persist_directory, collection_name="codebase")
        self.vector_store = VectorStore(config)


    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def _safe_embed(self, texts: List[str]) -> np.ndarray:
        """Safely generate embeddings with retry logic."""
        try:
            embeddings = await self.embeddings.abatch(texts)
            return embeddings
        except Exception as e:
            self.logger.error(f"Embedding generation failed: {str(e)}")
            raise

    async def ingest_code_directory(
        self,
        directory_path: str,
        exclude_dirs: Optional[List[str]] = None,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Enhanced code ingestion with progress tracking and batching."""
        stats = {"processed": 0, "failed": 0, "skipped": 0}
        
        async for batch in self._get_code_batches(directory_path, exclude_dirs):
            try:
                await self._process_code_batch(batch)
                stats["processed"] += len(batch)
                if callback:
                    await callback(stats)
            except Exception as e:
                stats["failed"] += len(batch)
                self.logger.error(f"Batch processing failed: {str(e)}")

        return stats

    async def _get_code_batches(
        self,
        directory_path: str,
        exclude_dirs: Optional[List[str]]
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Generate batches of code files for processing."""
        files = []
        for path in Path(directory_path).rglob("*.py"):
            if exclude_dirs and any(d in path.parts for d in exclude_dirs):
                continue
            files.append(path)

        for i in range(0, len(files), self.batch_size):
            batch = files[i:i + self.batch_size]
            yield [self._read_code_file(f) for f in batch]

    def _read_code_file(self, path: Path) -> Dict[str, Any]:
        """Read and prepare a code file for ingestion."""
        try:
            content = path.read_text(encoding='utf-8')
            return {
                "content": content,
                "metadata": {
                    "file_path": str(path),
                    "file_type": path.suffix,
                    "file_name": path.name,
                    "size": path.stat().st_size
                }
            }
        except Exception as e:
            self.logger.error(f"Error reading file {path}: {str(e)}")
            return None

    async def _process_code_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of code files."""
        if not batch:
            return

        valid_items = [item for item in batch if item is not None]
        contents = [item["content"] for item in valid_items]
        metadatas = [item["metadata"] for item in valid_items]

        try:
            # Generate embeddings in parallel
            embeddings = await self._safe_embed(contents)
            
            # Add to vector store
            await self.vector_store.add_items(
                embeddings=embeddings,
                metadatas=metadatas,
                contents=contents
            )
        except Exception as e:
            self.logger.error(f"Batch embedding failed: {str(e)}")
            raise

    async def search_context(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5,
        min_relevance: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Enhanced context search with filtering and relevance threshold."""
        try:
            # Generate query embedding
            query_embedding = await self._safe_embed([query])
            
            # Search vector store
            results = await self.vector_store.search(
                embedding=query_embedding[0],
                filters=filters,
                limit=limit * 2  # Get extra results for filtering
            )
            
            # Filter by relevance and format results
            filtered_results = []
            for result in results:
                if result["relevance"] >= min_relevance:
                    filtered_results.append({
                        "content": result["content"],
                        "metadata": result["metadata"],
                        "relevance": result["relevance"]
                    })
                if len(filtered_results) >= limit:
                    break
                    
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise

    async def update_embeddings(
        self,
        collection_name: str,
        batch_size: int = 100,
        callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Update embeddings for an entire collection."""
        stats = {"processed": 0, "failed": 0}
        
        try:
            # Get all documents
            documents = await self.vector_store.get_all(collection_name)
            total_batches = len(documents) // batch_size + 1
            
            async for i in tqdm(range(total_batches)):
                start_idx = i * batch_size
                end_idx = start_idx + batch_size
                batch = documents[start_idx:end_idx]
                
                try:
                    # Generate new embeddings
                    contents = [doc["content"] for doc in batch]
                    new_embeddings = await self._safe_embed(contents)
                    
                    # Update vector store
                    await self.vector_store.update_embeddings(
                        ids=[doc["id"] for doc in batch],
                        embeddings=new_embeddings
                    )
                    
                    stats["processed"] += len(batch)
                    if callback:
                        await callback(stats)
                        
                except Exception as e:
                    stats["failed"] += len(batch)
                    self.logger.error(f"Batch update failed: {str(e)}")
                    
            return stats
            
        except Exception as e:
            self.logger.error(f"Embedding update failed: {str(e)}")
            raise
