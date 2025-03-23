import os
from typing import List, Dict, Any, Optional, Generator
import asyncio
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor
import backoff
from tqdm.asyncio import tqdm
import numpy as np
from .vector_store import VectorStore, VectorStoreConfig
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
            # Default to persistent_state/chroma_db
            persist_directory = "persistent_state/chroma_db"
        
        print(f"Debug - Using persist directory: {persist_directory}")
        self.persist_directory = persist_directory
        self.batch_size = batch_size
        self._setup_logging()
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            error_msg = "OPENAI_API_KEY not found in environment variables. Please set your OpenAI API key."
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        self.openai_client = OpenAI(api_key=api_key)
        
        # Initialize vector store with the same persist directory
        self.vector_store = VectorStore(base_path=persist_directory)
        
        # Initialize embeddings configuration
        self.embeddings = {
            "model": "text-embedding-3-small",
            "provider": "openai"
        }

        self.contexts = {}  # Dictionary to store contexts by task_id
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def _safe_embed(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Safely generate embeddings with error handling and retries."""
        if not texts:
            print("⚠️ DEBUG: No texts provided for embedding")
            return None
            
        print(f"🔤 DEBUG: Generating embeddings for {len(texts)} texts")
        print(f"🔤 DEBUG: First text preview: {texts[0][:100]}...")
        
        # Try OpenAI embeddings first
        try:
            if self.openai_client:
                print("🔄 DEBUG: Using OpenAI for embeddings")
                response = self.openai_client.embeddings.create(
                    input=texts,
                    model="text-embedding-3-small"
                )
                embeddings = [item.embedding for item in response.data]
                print(f"✅ DEBUG: Generated {len(embeddings)} OpenAI embeddings")
                print(f"🔢 DEBUG: First embedding dimensions: {len(embeddings[0])}")
                print(f"🔢 DEBUG: First 5 values of first embedding: {embeddings[0][:5]}")
                return embeddings
            else:
                print("⚠️ DEBUG: OpenAI client not available")
        except Exception as e:
            print(f"❌ DEBUG: Error generating OpenAI embeddings: {str(e)}")
            self.logger.error(f"OpenAI embedding error: {str(e)}")
            
        # Fall back to local embeddings
        try:
            print("🔄 DEBUG: Falling back to local embeddings")
            # Use the embedding function from vector_store
            if hasattr(self.vector_store, 'embedding_function') and self.vector_store.embedding_function:
                embeddings = self.vector_store.embedding_function(texts)
                print(f"✅ DEBUG: Generated {len(embeddings)} local embeddings")
                if embeddings:
                    print(f"🔢 DEBUG: First embedding dimensions: {len(embeddings[0])}")
                    print(f"🔢 DEBUG: First 5 values of first embedding: {embeddings[0][:5]}")
                return embeddings
            else:
                print("❌ DEBUG: Local embedding function not available")
        except Exception as e:
            print(f"❌ DEBUG: Error generating local embeddings: {str(e)}")
            self.logger.error(f"Local embedding error: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            
        print("❌ DEBUG: Failed to generate embeddings through any method")
        return None

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
        min_relevance: float = 0.2,
        index_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Enhanced context search with filtering and relevance threshold."""
        try:
            print(f"\n🔍 DEBUG: search_context called with query='{query}', filters={filters}, limit={limit}, min_relevance={min_relevance}, index_name={index_name}")
            
            # Ensure index_name has the vs_ prefix if provided
            prefixed_index_name = None
            if index_name:
                if index_name.strip():  # Only process non-empty strings
                    original_index_name = index_name
                    prefixed_index_name = self.vector_store.get_full_index_name(index_name)
                    if original_index_name != prefixed_index_name:
                        print(f"🔄 DEBUG: Added vs_ prefix to index_name: {original_index_name} -> {prefixed_index_name}")
                else:
                    print("⚠️ DEBUG: Empty index_name provided, will use default collection")
            else:
                print("⚠️ DEBUG: No index_name provided, will use default collection")
            
            if filters and 'file_ids' in filters.get('filters', {}):
                # Direct lookup by file IDs - no need for embedding search
                print(f"📂 DEBUG: Performing direct file ID lookup with {len(filters['filters']['file_ids'])} file IDs")
                results = []
                for file_id in filters['filters']['file_ids']:
                    try:
                        print(f"📄 DEBUG: Looking up file ID: {file_id}")
                        # Use get_filtered_items_from_index instead of get_file_info
                        file_results = await self.vector_store.get_filtered_items_from_index(
                            index_name=prefixed_index_name or "default",
                            filters={"id": file_id},
                            limit=1
                        )
                        if file_results:
                            print(f"📄 DEBUG: Found file info")
                            results.extend(file_results)
                        else:
                            print(f"⚠️ DEBUG: File ID {file_id} not found")
                    except Exception as e:
                        print(f"❌ DEBUG: Error getting file {file_id}: {str(e)}")
                        continue
                print(f"📊 DEBUG: Direct lookup returned {len(results)} results")
                return results[:limit]
            
            # If we have a query, do semantic search
            if query and query.strip():
                print(f"🔤 DEBUG: Generating embedding for query: '{query}'")
                query_embedding = await self._safe_embed([query])
                if not query_embedding:
                    print("❌ DEBUG: Failed to generate embedding for query")
                    self.logger.warning("No embedding generated for query")
                    
                    # Fallback: Return all documents from the specified index or default collection
                    print("🔄 DEBUG: Falling back to returning all documents without embedding search")
                    return await self._get_all_documents_fallback(prefixed_index_name, limit)
                
                print(f"🔢 DEBUG: Generated embedding with dimensions: {len(query_embedding[0])}")
                print(f"🔢 DEBUG: First 5 embedding values: {query_embedding[0][:5]}")
                
                # Search vector store
                # If index_name is provided, use it to search in the specific collection
                if prefixed_index_name:
                    print(f"🔎 DEBUG: Searching in specific index: {prefixed_index_name}")
                    # Search in the specific collection
                    results = await self.vector_store.search_in_index(
                        index_name=prefixed_index_name,
                        embedding=query_embedding[0],
                        filters=filters,
                        limit=limit * 2  # Get extra results for filtering
                    )
                else:
                    # Search in the default collection
                    print(f"🔎 DEBUG: Searching in default collection")
                    results = await self.vector_store.search(
                        embedding=query_embedding[0],
                        filters=filters,
                        limit=limit * 2  # Get extra results for filtering
                    )
                
                print(f"📊 DEBUG: Vector search returned {len(results)} results")
                
                # If no results from semantic search, try fallback
                if not results:
                    print("🔄 DEBUG: No results from semantic search, trying fallback")
                    return await self._get_all_documents_fallback(prefixed_index_name, limit)
                
                # Log individual result relevance scores for debugging
                print("📊 DEBUG: Result relevance scores:")
                for i, result in enumerate(results):
                    relevance = result.get('relevance', 0)
                    print(f"  Result {i+1}: relevance={relevance:.4f} {'✅ (above threshold)' if relevance >= min_relevance else '❌ (below threshold)'}")
                
                # Filter by relevance threshold
                filtered_results = [r for r in results if r.get('relevance', 0) >= min_relevance]
                print(f"📊 DEBUG: After relevance filtering ({min_relevance}): {len(filtered_results)} results")
                
                # Sort by relevance and limit
                filtered_results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
                return filtered_results[:limit]
            
            # If no query, return all documents
            print("🔄 DEBUG: No query provided, returning all documents")
            return await self._get_all_documents_fallback(prefixed_index_name, limit)
            
        except Exception as e:
            print(f"❌ DEBUG: Error in search_context: {str(e)}")
            self.logger.error(f"Error searching context: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            return []

    async def _get_all_documents_fallback(self, index_name: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get all documents from a collection as a fallback."""
        try:
            print(f"🔄 DEBUG: Using fallback to get all documents from index {index_name}")
            
            if index_name:
                # Get documents from specific index
                results = await self.vector_store.get_filtered_items_from_index(
                    index_name=index_name,
                    limit=limit
                )
            else:
                # Try to get documents from any available index
                indices = await self.vector_store.list_indices()
                results = []
                
                if indices:
                    # Try each index until we get some results
                    for idx in indices:
                        idx_results = await self.vector_store.get_filtered_items_from_index(
                            index_name=idx["name"],
                            limit=limit
                        )
                        if idx_results:
                            results.extend(idx_results)
                            if len(results) >= limit:
                                break
                
                # If still no results, try the default collection
                if not results:
                    default_results = await self.vector_store.get_filtered_items_from_index(
                        index_name="default",
                        limit=limit
                    )
                    results.extend(default_results)
            
            print(f"📊 DEBUG: Fallback returned {len(results)} results")
            return results[:limit]
            
        except Exception as e:
            print(f"❌ DEBUG: Error in fallback document retrieval: {str(e)}")
            self.logger.error(f"Error in fallback document retrieval: {str(e)}")
            return []

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
            # Remove from in-memory contexts
            for task_id, contexts in self.contexts.items():
                self.contexts[task_id] = [ctx for ctx in contexts if ctx["id"] != context_id]
            
            # Remove from vector store if it exists there
            await self.vector_store.remove_context(context_id)
            
            return True
        except Exception as e:
            self.logger.error(f"Error deleting context: {str(e)}")
            return False
    
    async def update_context(self, context_id: str, metadata: Dict[str, Any]) -> bool:
        """Update context metadata."""
        try:
            # Update in-memory contexts
            for task_id, contexts in self.contexts.items():
                for ctx in contexts:
                    if ctx["id"] == context_id:
                        ctx["metadata"].update(metadata)
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating context: {str(e)}")
            return False
            
    async def remove_context(self, task_id: str, context_id: str) -> bool:
        """Remove a context from a task."""
        try:
            if task_id in self.contexts:
                initial_length = len(self.contexts[task_id])
                self.contexts[task_id] = [ctx for ctx in self.contexts[task_id] if ctx["id"] != context_id]
                return len(self.contexts[task_id]) < initial_length
            return False
        except Exception as e:
            self.logger.error(f"Error removing context: {str(e)}")
            return False
