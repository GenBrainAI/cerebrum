import os
import io
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import logging
import json
from dataclasses import dataclass
import PyPDF2
from tqdm.asyncio import tqdm
import asyncio

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

class VectorStore:
    def __init__(self, config: Optional[VectorStoreConfig] = None, base_path: str = "persistent_state/chroma_db"):
        """Initialize vector store with configuration."""
        self.config = config or VectorStoreConfig()
        self.base_path = base_path
        
        # Ensure base directory exists
        os.makedirs(base_path, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=base_path,
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding function
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=self.config.embedding_model
        )
        
        # Initialize indices dictionary
        self.indices = {}
        
        # Load existing indices
        self._load_existing_indices()

    def get_full_index_name(self, name: str) -> str:
        """Get the full index name with the vs_ prefix if not already present."""
        if not name:
            return name
        if name.startswith("vs_"):
            return name
        return f"vs_{name}"
    
    def get_display_name(self, index_name: str) -> str:
        """Get the display name without the vs_ prefix."""
        if not index_name:
            return index_name
        return index_name.replace("vs_", "")

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
            index_name = self.get_full_index_name(name)
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
            print(f"DEBUG - _reload_indices found collections: {[c.name for c in collections]}")
            
            vs_collections = [c for c in collections if c.name.startswith('vs_')]
            print(f"DEBUG - _reload_indices found vs_ collections: {[c.name for c in vs_collections]}")
            
            for collection in vs_collections:
                try:
                    self.indices[collection.name] = self.client.get_collection(
                        name=collection.name,
                        embedding_function=self.embedding_function
                    )
                    print(f"DEBUG - Added collection to indices: {collection.name}")
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

    async def add_items(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]], 
                       contents: List[str]) -> Dict[str, Any]:
        """Add items to the default collection."""
        if not embeddings or not metadatas or not contents:
            return {"added": 0}
            
        if len(embeddings) != len(metadatas) or len(embeddings) != len(contents):
            raise ValueError("Embeddings, metadatas, and contents must have the same length")
            
        # Generate IDs for the items
        ids = [str(hashlib.md5(content.encode()).hexdigest()) for content in contents]
        
        # Ensure default collection exists
        collection = self._ensure_collection("default")
        
        # Add items to collection
        collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            documents=contents,
            ids=ids
        )
        
        return {"added": len(ids), "ids": ids}

    async def search(self, embedding: List[float], filters: Optional[Dict[str, Any]] = None, 
                    limit: int = 10) -> List[Dict[str, Any]]:
        """Search across all collections."""
        results = []
        
        # Search in each collection
        for name, collection in self.indices.items():
            try:
                collection_results = await self.search_in_index(
                    index_name=name,
                    embedding=embedding,
                    filters=filters,
                    limit=limit
                )
                results.extend(collection_results)
            except Exception as e:
                logging.error(f"Error searching in collection {name}: {str(e)}")
                
        # Sort by relevance and limit results
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return results[:limit]

    def _ensure_collection(self, collection_name: str) -> chromadb.Collection:
        """Ensure a collection exists and return it."""
        print(f"🔍 DEBUG: _ensure_collection called for collection_name={collection_name}")
        print(f"🔍 DEBUG: ChromaDB client: {self.client}")
        
        try:
            # List all collections
            all_collections = self.client.list_collections()
            collection_names = [c.name for c in all_collections]
            print(f"📋 DEBUG: All ChromaDB collections: {collection_names}")
            
            # Check if collection already exists in indices
            if collection_name in self.indices:
                print(f"✅ DEBUG: Collection {collection_name} already exists in indices")
                return self.indices[collection_name]
                
            # Try to get existing collection
            try:
                print(f"🔍 DEBUG: Getting collection info for {collection_name}")
                collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                
                # Check if collection has documents
                count = collection.count()
                print(f"📊 DEBUG: Collection {collection_name} contains {count} documents")
                
                # Add to indices
                self.indices[collection_name] = collection
                return collection
                
            except Exception as e:
                print(f"⚠️ DEBUG: Collection {collection_name} not found: {str(e)}")
                
                # Create new collection
                print(f"🔄 DEBUG: Creating new collection: {collection_name}")
                collection = self.client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                
                # Add to indices
                self.indices[collection_name] = collection
                print(f"✅ DEBUG: Created new collection: {collection_name}")
                return collection
                
        except Exception as e:
            print(f"❌ DEBUG: Error ensuring collection {collection_name}: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            raise

    async def search_in_index(self, index_name: str, embedding: List[float], 
                         filters: Optional[Dict[str, Any]] = None, 
                         limit: int = 10) -> List[Dict[str, Any]]:
        """Search in a specific index/collection."""
        print(f"🔍 DEBUG: search_in_index called with index_name={index_name}, limit={limit}, filters={filters}")
        print(f"🔢 DEBUG: Embedding dimensions: {len(embedding)}")
        print(f"🔢 DEBUG: First 5 embedding values: {embedding[:5]}")
        
        try:
            # Ensure collection exists
            collection = self._ensure_collection(index_name)
            
            # Check if collection is empty
            count = collection.count()
            if count == 0:
                print(f"⚠️ DEBUG: Collection {index_name} is empty")
                return []
                
            # Prepare ChromaDB filters if needed
            chroma_filter = None
            if filters:
                # Convert filters to ChromaDB format
                if isinstance(filters, dict) and 'filters' in filters:
                    filter_dict = filters['filters']
                    if 'file_type' in filter_dict:
                        chroma_filter = {"file_type": filter_dict['file_type']}
                    if 'domain' in filter_dict:
                        chroma_filter = {"domain": filter_dict['domain']}
            
            # Query the collection
            results = collection.query(
                query_embeddings=[embedding],
                n_results=limit,
                where=chroma_filter
            )
            
            # Process results
            processed_results = []
            if results and 'documents' in results and results['documents']:
                documents = results['documents'][0]  # First query result
                metadatas = results['metadatas'][0]  # First query result
                distances = results['distances'][0]  # First query result
                ids = results['ids'][0]  # First query result
                
                for i, doc in enumerate(documents):
                    # Convert distance to relevance score (1.0 is perfect match, 0.0 is no match)
                    # ChromaDB uses cosine distance, so 0.0 is perfect match and 2.0 is opposite
                    # Convert to a 0-1 relevance score
                    distance = distances[i]
                    relevance = 1.0 - (distance / 2.0)
                    
                    processed_results.append({
                        "content": doc,
                        "metadata": metadatas[i],
                        "id": ids[i],
                        "relevance": relevance
                    })
            
            print(f"📊 DEBUG: Vector search returned {len(processed_results)} results")
            return processed_results
            
        except Exception as e:
            print(f"❌ DEBUG: Error searching in index {index_name}: {str(e)}")
            import traceback
            print(f"❌ DEBUG: Traceback: {traceback.format_exc()}")
            return []

    async def get_filtered_items_from_index(self, index_name: str, 
                                 filters: Optional[Dict[str, Any]] = None, 
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """Get items from a specific index with filters."""
        try:
            # Ensure collection exists
            collection = self._ensure_collection(index_name)
            
            # Prepare ChromaDB filters if needed
            chroma_filter = None
            if filters:
                # Convert filters to ChromaDB format
                if isinstance(filters, dict) and 'filters' in filters:
                    filter_dict = filters['filters']
                    if 'file_type' in filter_dict:
                        chroma_filter = {"file_type": filter_dict['file_type']}
                    if 'domain' in filter_dict:
                        chroma_filter = {"domain": filter_dict['domain']}
            
            # Query the collection
            results = collection.get(
                limit=limit,
                where=chroma_filter
            )
            
            # Process results
            processed_results = []
            if results and 'documents' in results and results['documents']:
                documents = results['documents']
                metadatas = results['metadatas']
                ids = results['ids']
                
                for i, doc in enumerate(documents):
                    processed_results.append({
                        "content": doc,
                        "metadata": metadatas[i],
                        "id": ids[i],
                        "relevance": 1.0  # No relevance for direct retrieval
                    })
            
            return processed_results
            
        except Exception as e:
            logging.error(f"Error getting filtered items from index {index_name}: {str(e)}")
            return []

    async def remove_context(self, context_id: str) -> bool:
        """Remove a context from all collections."""
        success = False
        for name, collection in self.indices.items():
            try:
                collection.delete(ids=[context_id])
                success = True
            except Exception as e:
                logging.error(f"Error removing context {context_id} from collection {name}: {str(e)}")
        return success

    async def delete_index(self, index_name: str) -> bool:
        """Delete an entire index/collection."""
        try:
            # Remove from indices dictionary
            if index_name in self.indices:
                del self.indices[index_name]
            
            # Delete from ChromaDB
            self.client.delete_collection(name=index_name)
            logging.info(f"Deleted index: {index_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error deleting index {index_name}: {str(e)}")
            return False

    def _calculate_storage_size(self) -> float:
        """Calculate the size of the ChromaDB storage in MB."""
        try:
            total_size = 0
            chroma_path = Path(self.base_path)
            
            if chroma_path.exists():
                for path in chroma_path.glob('**/*'):
                    if path.is_file():
                        total_size += path.stat().st_size
            
            # Convert to MB
            return total_size / (1024 * 1024)
        except Exception as e:
            logging.error(f"Error calculating storage size: {str(e)}")
            return 0.0

    async def add_file_to_index(self, index_name: str, file_path_or_obj: Any, 
                               metadata: Optional[Dict[str, Any]] = None,
                               progress_callback: Optional[Callable[[str, int, int], None]] = None) -> List[str]:
        """Add file content to a specific index with chunking."""
        try:
            # Ensure index exists
            await self.create_index(index_name)
            collection = self._ensure_collection(index_name)
            
            # Update progress
            if progress_callback:
                progress_callback("Reading file...", 0, 100)
            
            # Extract text from file
            try:
                import PyPDF2
                import io
                
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
            import hashlib
            from datetime import datetime
            
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
            
            # Generate embeddings for chunks
            embeddings = []
            for chunk in chunks:
                embedding = self._safe_embed([chunk])[0]
                embeddings.append(embedding)
            
            # Add root chunk
            collection.add(
                ids=[root_id],
                documents=[text[:self.config.chunk_size]],  # Store first chunk size of text
                metadatas=[root_metadata],
                embeddings=[embeddings[0]]  # Use first chunk embedding
            )
            chunk_ids.append(root_id)
            
            # Add individual chunks with their metadata
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
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
                    metadatas=[chunk_metadata],
                    embeddings=[embedding]
                )
                chunk_ids.append(chunk_id)
                
                if progress_callback:
                    progress_callback(f"Processing chunk {i+1}/{total_chunks}", i+1, total_chunks)
            
            return chunk_ids
            
        except Exception as e:
            logging.error(f"Error adding file to index: {str(e)}")
            raise

    async def process_directory(self, index_name: str, directory_path: str, 
                               metadata: Optional[Dict[str, Any]] = None,
                               progress_callback: Optional[Callable[[str, int, int], None]] = None) -> int:
        """Process all files in a directory and add them to an index."""
        try:
            # Ensure index exists
            await self.create_index(index_name)
            
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
            
        except Exception as e:
            logging.error(f"Error processing directory: {str(e)}")
            raise

    async def add_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add text content directly to the vector store."""
        try:
            # Generate text ID
            import hashlib
            from datetime import datetime
            
            text_id = hashlib.md5(text.encode()).hexdigest()
            
            # Update metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                'type': 'text',
                'added_at': datetime.now().isoformat(),
                'size': len(text.encode('utf-8'))
            })
            
            # Generate embedding
            embedding = self._safe_embed([text])[0]
            
            # Ensure default collection exists
            collection = self._ensure_collection("default")
            
            # Add to collection
            collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[text_id],
                embeddings=[embedding]
            )
            
            return text_id
            
        except Exception as e:
            logging.error(f"Error adding text to vector store: {str(e)}")
            raise