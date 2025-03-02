import os
from typing import List, Dict, Any, Optional, Generator
import asyncio
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor
import backoff
from tqdm.asyncio import tqdm
import numpy as np
from .chroma_vector_store import ChromaVectorStore, VectorStoreConfig
from openai import OpenAI
import json
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime

class ContextDatabase:
    """Enhanced version of the context database with better error handling and performance."""
    
    def __init__(self, persist_directory: str = None, batch_size: int = 100):
        """Initialize context database components."""
        if persist_directory is None:
            # Default to context_db in the project root
            project_root = Path(__file__).parents[3]  # Adjust based on directory structure
            persist_directory = str(project_root / "context_db")
        
        print(f"Debug - Using persist directory: {persist_directory}")
        self.persist_directory = persist_directory
        self.batch_size = batch_size
        self._setup_logging()
        
        # Initialize vector store
        self.vector_store = ChromaVectorStore(
            config=VectorStoreConfig(
                batch_size=batch_size,
                persist_directory=persist_directory
            ),
            base_path=persist_directory
        )
        
        # Initialize OpenAI client for embeddings
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        # Initialize ChromaDB client
        self.chromadb_client = chromadb.PersistentClient(
            path=str(Path(persist_directory) / "chroma"),
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model_name="text-embedding-3-small"
        )
        
        # Initialize collections
        self._initialize_collections()
        
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            error_msg = "OPENAI_API_KEY not found in environment variables. Please set your OpenAI API key."
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.openai_client = OpenAI(api_key=api_key)
        
        # Initialize embeddings configuration
        self.embeddings = {
            "model": "text-embedding-3-small",
            "provider": "openai"
        }

        self.contexts = {}  # Dictionary to store contexts by task_id

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def _initialize_collections(self):
        """Initialize collections in ChromaDB."""
        try:
            # Initialize main collection for contexts
            self.collection = self.chromadb_client.get_or_create_collection(
                name="contexts",
                embedding_function=self.embedding_function
            )
            
            # Initialize code collection
            self.code_collection = self.chromadb_client.get_or_create_collection(
                name="code_contexts",
                embedding_function=self.embedding_function
            )
            
            logging.info("Initialized context database collections")
        except Exception as e:
            logging.error(f"Error initializing collections: {str(e)}")
            raise

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def _safe_embed(self, texts: List[str]) -> np.ndarray:
        """Safely embed texts with error handling and retries."""
        try:
            # Use the vector store's embedding function
            embeddings = []
            for text in texts:
                response = await self.client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small"
                )
                embeddings.append(response.data[0].embedding)
            return embeddings
        except Exception as e:
            self.logger.error(f"Error embedding texts: {str(e)}")
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
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5,
        min_relevance: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Enhanced context search with filtering and relevance threshold."""
        try:
            print(f"Debug - Search context called with filters: {filters}")
            
            if filters and 'file_ids' in filters.get('filters', {}):
                # Direct lookup by file IDs - no need for embedding search
                results = []
                for file_id in filters['filters']['file_ids']:
                    try:
                        print(f"Debug - Looking up file ID: {file_id}")
                        file_info = await self.vector_store.get_file_info(file_id)
                        print(f"Debug - Found file info: {file_info}")
                        if file_info:
                            results.append({
                                "content": file_info.get('content', ''),
                                "metadata": file_info,
                                "relevance": 1.0  # Direct match
                            })
                    except Exception as e:
                        print(f"Debug - Error getting file {file_id}: {str(e)}")
                        continue
                print(f"Debug - Direct lookup results: {results}")
                return results[:limit]
            
            # If we have a query, do semantic search
            if query and query.strip():
                query_embedding = await self._safe_embed([query])
                if not query_embedding:
                    self.logger.warning("No embedding generated for query")
                    return []
                
                # Search vector store
                results = await self.vector_store.search(
                    embedding=query_embedding[0],
                    filters=filters,
                    limit=limit * 2  # Get extra results for filtering
                )
                
                # Filter by relevance
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
            
            # If no query but have filters, return filtered results without relevance scoring
            elif filters:
                results = await self.vector_store.get_filtered_items(
                    filters=filters,
                    limit=limit
                )
                return [{
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "relevance": 1.0  # Default relevance for filtered results
                } for item in results]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            return []

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

    async def store_context(
        self,
        task_id: str,
        context_type: str,
        source_id: str,
        metadata: Dict[str, Any],
        priority: int = 50
    ) -> str:
        """Store a context entry."""
        if task_id not in self.contexts:
            self.contexts[task_id] = []
        
        context_id = f"{task_id}_{context_type}_{source_id}"
        context = {
            "id": context_id,
            "type": context_type,
            "source_id": source_id,
            "metadata": metadata,
            "priority": priority,
            "created_at": datetime.now()
        }
        
        self.contexts[task_id].append(context)
        return context_id
    
    async def get_contexts(
        self,
        task_id: str,
        context_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get contexts for a task."""
        if task_id not in self.contexts:
            return []
        
        contexts = self.contexts[task_id]
        if context_types:
            contexts = [ctx for ctx in contexts if ctx["type"] in context_types]
        
        return sorted(contexts, key=lambda x: x["priority"], reverse=True)
    
    async def clear(self):
        """Clear all contexts."""
        self.contexts = {}

    async def delete_context(self, context_id: str) -> bool:
        """Delete a context from the database."""
        try:
            self.collection.delete(ids=[context_id])
            logging.info(f"Deleted context {context_id}")
            return True
        except Exception as e:
            logging.error(f"Error deleting context: {str(e)}")
            return False

    async def update_context(self, context_id: str, metadata: Dict[str, Any]) -> bool:
        """Update context metadata."""
        try:
            self.collection.update(
                ids=[context_id],
                metadatas=[metadata]
            )
            logging.info(f"Updated context {context_id}")
            return True
        except Exception as e:
            logging.error(f"Error updating context: {str(e)}")
            return False
