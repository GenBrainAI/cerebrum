"""
ChromaDB-based Vector Store for Cerebrum.

This module provides a vector store implementation using ChromaDB for efficient
storage and retrieval of embeddings. It replaces the custom vector store implementation
with a more robust and scalable solution.
"""

import os
import io
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
import logging
import json
from dataclasses import dataclass
import asyncio
import PyPDF2
from tqdm.asyncio import tqdm

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

@dataclass
class VectorStoreConfig:
    """Configuration for vector store operations."""
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: int = 1
    connection_timeout: int = 30
    max_concurrent_requests: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 100
    embedding_model: str = "text-embedding-3-small"
    embeddings_provider: str = "openai"
    persist_directory: str = "context_db"
    collection_name: str = "default"
    metadata_schema: Optional[Dict[str, Any]] = None

class ChromaVectorStore:
    def __init__(self, config: Optional[VectorStoreConfig] = None, base_path: str = "persistent_state/context/chroma_db"):
        """Initialize ChromaVectorStore with ChromaDB.
        
        Args:
            config: VectorStoreConfig object with settings
            base_path: Base path for ChromaDB persistence
        """
        self.config = config or VectorStoreConfig()
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.base_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True
            )
        )

        # Initialize OpenAI embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=self.config.embedding_model
        )
        
        # Initialize indices dictionary
        self.indices = {}
        self._load_existing_indices()
        
        # Logger
        self.logger = logging.getLogger(__name__)

    def _load_existing_indices(self):
        """Load existing collections from ChromaDB."""
        try:
            for collection in self.client.list_collections():
                if collection.name.startswith('vs_'):
                    self.indices[collection.name] = self.client.get_collection(
                        name=collection.name,
                        embedding_function=self.embedding_function
                    )
            logging.info(f"Loaded {len(self.indices)} existing vector indices")
        except Exception as e:
            logging.error(f"Error loading existing collections: {str(e)}")

    def _safe_embed(self, texts: List[str]) -> List[List[float]]:
        """Safely generate embeddings for a list of texts."""
        try:
            # Use the embedding function directly
            embeddings = self.embedding_function(texts)
            return embeddings
        except Exception as e:
            logging.error(f"Error generating embeddings: {str(e)}")
            # Return zero embeddings as fallback
            dimension = 1536  # OpenAI's default embedding dimension
            return [[0.0] * dimension for _ in texts]

    async def create_index(self, name: str, description: Optional[str] = None) -> str:
        """Create a new index/collection for specific content."""
        try:
            index_name = f"vs_{name}"
            # Check if collection already exists
            try:
                collection = self.client.get_collection(
                    name=index_name,
                    embedding_function=self.embedding_function
                )
            except:
                # Create new collection if it doesn't exist
                collection = self.client.create_collection(
                    name=index_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": description}
                )
            
            # Store in indices dictionary
            self.indices[index_name] = collection
            logging.info(f"Created/loaded index: {index_name}")
            return index_name
            
        except Exception as e:
            logging.error(f"Error creating index {name}: {str(e)}")
            raise

    def _reload_indices(self):
        """Reload all indices from ChromaDB."""
        try:
            self.indices.clear()  # Clear existing indices
            collections = self.client.list_collections()
            
            vs_collections = [c for c in collections if c.name.startswith('vs_')]
            
            for collection in vs_collections:
                try:
                    self.indices[collection.name] = self.client.get_collection(
                        name=collection.name,
                        embedding_function=self.embedding_function
                    )
                except Exception as e:
                    logging.error(f"Error loading collection {collection.name}: {str(e)}")
            
            logging.info(f"Reloaded {len(self.indices)} vector indices")
        except Exception as e:
            logging.error(f"Error reloading indices: {str(e)}")

    async def list_indices(self) -> List[Dict[str, Any]]:
        """List all available indices/collections."""
        try:
            self._reload_indices()  # Reload before listing
            collections = self.client.list_collections()
            indices = []
            
            # Process each collection
            for col in collections:
                if col.name.startswith("vs_"):
                    try:
                        count = col.count()
                        indices.append({
                            "name": col.name,
                            "description": col.metadata.get("description", ""),
                            "count": count
                        })
                    except Exception as e:
                        logging.error(f"Error getting collection stats for {col.name}: {str(e)}")
                        # Still include the collection even if stats fail
                        indices.append({
                            "name": col.name,
                            "description": col.metadata.get("description", ""),
                            "count": 0
                        })
            
            logging.info(f"Listed {len(indices)} indices: {[idx['name'] for idx in indices]}")
            return indices
            
        except Exception as e:
            logging.error(f"Error listing indices: {str(e)}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        collections = await self.list_indices()
        total_vectors = sum(col["count"] for col in collections)
        return {
            "total_vectors": total_vectors,
            "indices_count": len(collections),
            "storage_size": self._calculate_storage_size()
        }

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            remaining = text_len - start
            
            if remaining <= chunk_size:
                # If remaining text is smaller than chunk_size, add it and we're done
                chunks.append(text[start:])
                break
            
            # Find a good breaking point within the chunk_size
            end = start + chunk_size
            while end > start and not text[end - 1].isspace():
                end -= 1
            
            # If we couldn't find a space, just use the full chunk_size
            if end == start:
                end = start + chunk_size
            
            chunks.append(text[start:end])
            start = end - overlap
        
        return [chunk.strip() for chunk in chunks if chunk.strip()]  # Added strip() to clean chunks

    async def add_file_to_index(self, index_name: str, file_path_or_obj: Any, 
                               metadata: Optional[Dict[str, Any]] = None,
                               progress_callback: Optional[Callable[[str, int, int], None]] = None) -> List[str]:
        """Add file content to a specific index with chunking."""
        try:
            if index_name not in self.indices:
                collection = self.client.get_or_create_collection(
                    name=index_name,
                    embedding_function=self.embedding_function
                )
                self.indices[index_name] = collection
            else:
                collection = self.indices[index_name]

            # Update progress
            if progress_callback:
                progress_callback("Reading file...", 0, 100)
            
            # Extract text from file
            try:
                if hasattr(file_path_or_obj, 'read'):  # File-like object
                    filename = getattr(file_path_or_obj, 'name', '')
                    if filename.lower().endswith('.pdf'):
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_path_or_obj.read()))
                        text = ""
                        total_pages = len(pdf_reader.pages)
                        for i, page in enumerate(pdf_reader.pages):
                            text += page.extract_text() + "\n"
                            if progress_callback:
                                progress_callback(f"Reading PDF page {i+1}/{total_pages}", 
                                               i+1, total_pages)
                        file_path_or_obj.seek(0)
                    else:
                        content = file_path_or_obj.read()
                        text = content.decode('utf-8') if isinstance(content, bytes) else str(content)
                else:  # File path
                    file_path = Path(file_path_or_obj)
                    if not file_path.exists():
                        raise FileNotFoundError(f"File not found: {file_path}")
                    
                    if file_path.suffix.lower() == '.pdf':
                        with open(file_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            text = ""
                            total_pages = len(pdf_reader.pages)
                            for i, page in enumerate(pdf_reader.pages):
                                text += page.extract_text() + "\n"
                                if progress_callback:
                                    progress_callback(f"Reading PDF page {i+1}/{total_pages}", 
                                                   i+1, total_pages)
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text = f.read()
            
            except Exception as e:
                logging.error(f"Error reading file: {str(e)}")
                raise
            
            # Generate chunks
            chunks = self._chunk_text(text, self.config.chunk_size, self.config.chunk_overlap)
            if not chunks:
                raise ValueError("No valid chunks generated from file")
            
            # Generate unique IDs for chunks
            chunk_ids = []
            original_text_length = len(text)
            total_chunks = len(chunks)
            
            # Create root chunk with full metadata
            root_id = hashlib.md5(text.encode()).hexdigest()
            root_metadata = {
                **(metadata or {}),
                "is_root": True,
                "total_chunks": total_chunks,
                "original_text_length": original_text_length,
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap,
                "created_at": datetime.now().isoformat()
            }
            
            # Add root chunk
            collection.add(
                ids=[root_id],
                documents=[text[:self.config.chunk_size]],  # Store first chunk size of text
                metadatas=[root_metadata]
            )
            chunk_ids.append(root_id)
            
            # Add individual chunks with their metadata
            for i, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{root_id}_{i}".encode()).hexdigest()
                chunk_metadata = {
                    **(metadata or {}),
                    "is_root": False,
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    "root_id": root_id,
                    "created_at": datetime.now().isoformat()
                }
                
                collection.add(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[chunk_metadata]
                )
                chunk_ids.append(chunk_id)
                
                if progress_callback:
                    progress_callback(f"Processing chunk {i+1}/{total_chunks}", i+1, total_chunks)
            
            return chunk_ids
            
        except Exception as e:
            logging.error(f"Error adding file to index: {str(e)}")
            raise

    async def search_index(self, index_name: str, query: str, 
                          filters: Optional[Dict[str, Any]] = None, 
                          limit: int = 5) -> List[Dict[str, Any]]:
        """Search a specific index for relevant documents."""
        try:
            if index_name not in self.indices:
                raise ValueError(f"Index {index_name} not found")
            
            collection = self.indices[index_name]
            
            # Query collection
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=filters
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "relevance": float(results['distances'][0][i]) if 'distances' in results else 1.0
                    })
            
            logging.info(f"Search returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logging.error(f"Error searching index: {str(e)}")
            return []

    async def delete_index(self, index_name: str) -> bool:
        """Delete an index and all its contents."""
        try:
            if index_name not in self.indices:
                return False
            
            # Delete from ChromaDB
            self.client.delete_collection(index_name)
            
            # Remove from indices dictionary
            del self.indices[index_name]
            
            logging.info(f"Deleted index: {index_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error deleting index {index_name}: {str(e)}")
            return False

    async def process_directory(self, index_name: str, directory_path: str, 
                              metadata: Optional[Dict[str, Any]] = None,
                              progress_callback: Optional[Callable[[str, int, int], None]] = None) -> int:
        """Process all files in a directory and add them to an index."""
        if index_name not in self.indices:
            raise ValueError(f"Index {index_name} not found")
        
        processed = 0
        path = Path(directory_path)
        
        # Get list of files to process
        files = [f for f in path.rglob("*") 
                 if f.is_file() and f.suffix.lower() in ['.txt', '.pdf', '.docx', '.py', '.md', '.json']]
        
        total_files = len(files)
        for i, file_path in enumerate(files):
            try:
                if progress_callback:
                    progress_callback(f"Processing file {i+1}/{total_files}: {file_path.name}",
                                   i, total_files)
                
                await self.add_file_to_index(
                    index_name=index_name,
                    file_path_or_obj=str(file_path),
                    metadata={
                        **(metadata or {}),
                        "original_path": str(file_path)
                    },
                    progress_callback=lambda msg, cur, tot: progress_callback(
                        f"File {i+1}/{total_files} - {msg}", cur, tot
                    ) if progress_callback else None
                )
                processed += 1
            except Exception as e:
                logging.error(f"Error processing file {file_path}: {str(e)}")
        
        return processed

    async def get_index_contents(self, index_name: str) -> List[Dict[str, Any]]:
        """Get all contents of an index."""
        try:
            if index_name not in self.indices:
                raise ValueError(f"Index {index_name} not found")
            
            collection = self.indices[index_name]
            results = collection.get()
            
            contents = []
            for i, (id, text, metadata) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
                contents.append({
                    "id": id,
                    "text": text,
                    "metadata": metadata
                })
            
            return contents
            
        except Exception as e:
            logging.error(f"Error getting index contents: {str(e)}")
            return []

    def _calculate_storage_size(self) -> float:
        """Calculate total storage size in MB."""
        try:
            total_size = 0
            base_path = Path(self.base_path)
            
            # Check if directory exists
            if not base_path.exists():
                return 0.0
            
            # Calculate size recursively
            for path in base_path.rglob('*'):
                if path.is_file():
                    total_size += path.stat().st_size
            
            # Convert to MB
            return total_size / (1024 * 1024)
            
        except Exception as e:
            logging.error(f"Error calculating storage size: {str(e)}")
            return 0.0

    async def add_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add text content directly to the vector store."""
        try:
            # Generate text ID
            text_id = hashlib.md5(text.encode()).hexdigest()
            
            # Update metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                'type': 'text',
                'added_at': datetime.now().isoformat(),
                'size': len(text.encode('utf-8'))
            })
            
            # Get or create default collection
            collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                embedding_function=self.embedding_function
            )
            
            # Add to collection
            collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[text_id]
            )
            
            return text_id
            
        except Exception as e:
            logging.error(f"Error adding text to vector store: {str(e)}")
            raise

    async def get_content(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get content by ID from the vector store."""
        try:
            # Get or create default collection
            collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                embedding_function=self.embedding_function
            )
            
            # Get content by ID
            results = collection.get(
                ids=[content_id],
                include=["documents", "metadatas"]
            )
            
            if results["documents"]:
                return {
                    "content": results["documents"][0],
                    "metadata": results["metadatas"][0]
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting content from vector store: {str(e)}")
            return None

    async def get_all_items(self) -> List[Dict[str, Any]]:
        """Get all items from the default collection."""
        try:
            # Ensure default collection exists
            collection = self._ensure_collection(self.config.collection_name)
            
            # Get all items
            items = collection.get()
            
            # Format results
            results = []
            if items and "ids" in items and len(items["ids"]) > 0:
                for i in range(len(items["ids"])):
                    results.append({
                        "id": items["ids"][i],
                        "content": items["documents"][i] if "documents" in items else "",
                        "metadata": items["metadatas"][i] if "metadatas" in items else {},
                        "embedding": items["embeddings"][i] if "embeddings" in items else None
                    })
                    
            return results
            
        except Exception as e:
            logging.error(f"Error getting all items: {str(e)}")
            return []

    async def add_items(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]], 
                       contents: List[str]) -> Dict[str, Any]:
        """Add items to the default collection.
        
        Args:
            embeddings: List of embeddings
            metadatas: List of metadata dictionaries
            contents: List of content strings
            
        Returns:
            Dictionary with stats about the operation
        """
        try:
            # Ensure default collection exists
            collection = self._ensure_collection(self.config.collection_name)
            
            # Generate IDs
            ids = [hashlib.md5(f"{content}_{datetime.now().isoformat()}".encode()).hexdigest() 
                  for content in contents]
            
            # Add items to collection
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=contents
            )
            
            return {
                "processed": len(contents),
                "failed": 0,
                "ids": ids
            }
            
        except Exception as e:
            logging.error(f"Error adding items: {str(e)}")
            return {
                "processed": 0,
                "failed": len(contents),
                "ids": [],
                "error": str(e)
            }

    async def update_embeddings(self, ids: List[str], embeddings: List[List[float]]) -> Dict[str, Any]:
        """Update embeddings for existing items.
        
        Args:
            ids: List of item IDs
            embeddings: List of new embeddings
            
        Returns:
            Dictionary with stats about the operation
        """
        try:
            # Ensure default collection exists
            collection = self._ensure_collection(self.config.collection_name)
            
            # Update embeddings
            for i, item_id in enumerate(ids):
                collection.update(
                    ids=[item_id],
                    embeddings=[embeddings[i]]
                )
            
            return {
                "processed": len(ids),
                "failed": 0
            }
            
        except Exception as e:
            logging.error(f"Error updating embeddings: {str(e)}")
            return {
                "processed": 0,
                "failed": len(ids),
                "error": str(e)
            }

    async def search(self, embedding: List[float], filters: Optional[Dict[str, Any]] = None, 
                    limit: int = 10) -> List[Dict[str, Any]]:
        """Search the default collection using an embedding.
        
        Args:
            embedding: Query embedding
            filters: Optional metadata filters
            limit: Maximum number of results to return
            
        Returns:
            List of matching items with relevance scores
        """
        try:
            # Ensure default collection exists
            collection = self._ensure_collection(self.config.collection_name)
            
            # Perform search
            results = collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                where=filters
            )
            
            # Format results
            formatted_results = []
            if results and "ids" in results and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "relevance": results["distances"][0][i] if "distances" in results else 0.0
                    })
                    
            return formatted_results
            
        except Exception as e:
            logging.error(f"Error searching: {str(e)}")
            return []

    def _ensure_collection(self, collection_name: str):
        """Ensure a collection exists and return it."""
        try:
            return self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
        except:
            return self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )

    async def migrate_from_custom_store(self, custom_store_path: str) -> Dict[str, Any]:
        """Migrate data from a custom vector store to ChromaDB.
        
        Args:
            custom_store_path: Path to the custom vector store
            
        Returns:
            Dictionary with migration statistics
        """
        try:
            import json
            import os
            from pathlib import Path
            
            # Check if the custom store exists
            custom_path = Path(custom_store_path)
            index_path = custom_path / "index.json"
            embeddings_path = custom_path / "embeddings.json"
            
            if not index_path.exists() or not embeddings_path.exists():
                return {
                    "total": 0,
                    "processed": 0,
                    "skipped": 0,
                    "error": "Custom store files not found"
                }
            
            # Load index and embeddings
            with open(index_path, "r") as f:
                index_data = json.load(f)
                
            with open(embeddings_path, "r") as f:
                embeddings_data = json.load(f)
                
            # Ensure default collection exists
            collection = self._ensure_collection(self.config.collection_name)
            
            # Prepare data for migration
            ids = []
            contents = []
            metadatas = []
            embeddings = []
            
            # Process each item
            for item_id, item_data in index_data.items():
                if item_id in embeddings_data:
                    ids.append(item_id)
                    contents.append(item_data["content"])
                    
                    # Extract metadata
                    metadata = {k: v for k, v in item_data.items() if k != "content"}
                    metadatas.append(metadata)
                    
                    # Get embedding
                    embedding = embeddings_data[item_id]
                    # Ensure embedding is the right size
                    if len(embedding) < 1536:  # OpenAI's default dimension
                        # Pad with zeros
                        embedding = embedding + [0.0] * (1536 - len(embedding))
                    embeddings.append(embedding)
            
            # Add items to collection
            if ids:
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=contents
                )
            
            return {
                "total": len(index_data),
                "processed": len(ids),
                "skipped": len(index_data) - len(ids)
            }
            
        except Exception as e:
            logging.error(f"Error migrating from custom store: {str(e)}")
            return {
                "total": 0,
                "processed": 0,
                "skipped": 0,
                "error": str(e)
            } 