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
    def __init__(self, config: Optional[VectorStoreConfig] = None, base_path: str = "persistent_state/context/vector_store"):
        """Initialize VectorStore with ChromaDB.
        
        Args:
            config: VectorStoreConfig object with settings
            base_path: Base path for ChromaDB persistence
        """
        self.config = config or VectorStoreConfig()
        self.base_path = Path(base_path)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.base_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
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

    def create_index(self, name: str, description: Optional[str] = None) -> str:
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
            for collection in collections:
                if collection.name.startswith('vs_'):
                    self.indices[collection.name] = self.client.get_collection(
                        name=collection.name,
                        embedding_function=self.embedding_function
                    )
            logging.info(f"Reloaded {len(self.indices)} vector indices")
        except Exception as e:
            logging.error(f"Error reloading indices: {str(e)}")

    async def list_indices(self) -> List[Dict[str, Any]]:
        """List all available indices/collections."""
        self._reload_indices()  # Reload before listing
        collections = self.client.list_collections()
        indices = [{
            "name": col.name,
            "description": col.metadata.get("description", ""),
            "count": col.count()
        } for col in collections if col.name.startswith("vs_")]
        logging.info(f"Listed {len(indices)} indices: {[idx['name'] for idx in indices]}")
        return indices

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
        """Add file content to a specific index with chunking.
        
        Args:
            index_name: Name of the index to add to
            file_path_or_obj: File path or file-like object
            metadata: Optional metadata for the file
            progress_callback: Optional callback function(status_message, current, total)
        """
        try:
            if index_name not in self.indices:
                raise ValueError(f"Index {index_name} not found")
            
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

            if progress_callback:
                progress_callback("Chunking text...", 0, 100)

            # Split into chunks
            chunks = self._chunk_text(text)
            successful_ids = []
            
            # Ensure we have a file_id in metadata
            if metadata is None:
                metadata = {}
            if 'file_id' not in metadata:
                metadata['file_id'] = hashlib.md5(text.encode()).hexdigest()
            
            if progress_callback:
                progress_callback("Adding root chunk...", 0, len(chunks) + 1)

            # Add root chunk first
            root_id = f"{metadata['file_id']}_root"
            root_metadata = {
                **metadata,
                "is_root": True,
                "total_chunks": len(chunks),
                "original_text_length": len(text)
            }
            
            # Add root chunk to collection
            collection.add(
                ids=[root_id],
                documents=[text[:min(len(text), 1000)]],  # Store first 1000 chars as preview
                metadatas=[root_metadata]
            )
            successful_ids.append(root_id)
            
            # Process each chunk with progress updates
            for i, chunk in enumerate(chunks):
                try:
                    if progress_callback:
                        progress_callback(f"Processing chunk {i+1}/{len(chunks)}", 
                                       i+1, len(chunks))
                    
                    # Generate unique ID for this chunk
                    chunk_id = f"{metadata['file_id']}_{i}"
                    
                    # Add chunk-specific metadata
                    chunk_metadata = {
                        **metadata,
                        "is_root": False,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "chunk_size": len(chunk)
                    }
                    
                    # Add to collection
                    collection.add(
                        ids=[chunk_id],
                        documents=[chunk],
                        metadatas=[chunk_metadata]
                    )
                    
                    successful_ids.append(chunk_id)
                    logging.info(f"Added chunk {i+1}/{len(chunks)} to index {index_name}")
                    
                    # Allow other tasks to run
                    await asyncio.sleep(0)
                    
                except Exception as e:
                    logging.error(f"Error processing chunk {i+1}/{len(chunks)}: {str(e)}")
                    continue
            
            if not successful_ids:
                raise Exception("No chunks were successfully processed")
            
            if progress_callback:
                progress_callback("Complete!", len(chunks), len(chunks))
            
            return successful_ids
            
        except Exception as e:
            logging.error(f"Error adding file to index {index_name}: {str(e)}")
            raise

    async def add_items(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]], 
                       contents: List[str]) -> Dict[str, Any]:
        """Add items to ChromaDB collection."""
        try:
            # Generate IDs for the items
            ids = [hashlib.md5(f"{content}{i}".encode()).hexdigest() 
                  for i, content in enumerate(contents)]
            
            # Get or create default collection
            collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                embedding_function=self.embedding_function
            )
            
            # Add to collection in batches
            batch_size = self.config.batch_size
            for i in range(0, len(contents), batch_size):
                batch_end = min(i + batch_size, len(contents))
                collection.add(
                    embeddings=embeddings[i:batch_end],
                    documents=contents[i:batch_end],
                    metadatas=metadatas[i:batch_end],
                    ids=ids[i:batch_end]
                )
            
            return {
                "ids": ids,
                "processed": len(ids),
                "failed": 0
            }
            
        except Exception as e:
            logging.error(f"Error adding items to vector store: {str(e)}")
            return {
                "ids": [],
                "processed": 0,
                "failed": len(contents)
            }

    async def add_file(self, file_path_or_obj: Any, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Process and add a file to ChromaDB."""
        try:
            # Handle Streamlit UploadedFile
            if hasattr(file_path_or_obj, 'read'):  # It's a file-like object
                # Get the filename from the uploaded file
                filename = getattr(file_path_or_obj, 'name', '')
                
                # Read content based on file type
                if filename.lower().endswith('.pdf'):
                    # Handle PDF file
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_path_or_obj.read()))
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    
                    # Reset file pointer
                    if hasattr(file_path_or_obj, 'seek'):
                        file_path_or_obj.seek(0)
                else:
                    # Handle other file types as before
                    content = file_path_or_obj.read()
                    if isinstance(content, bytes):
                        try:
                            text = content.decode('utf-8')
                        except UnicodeDecodeError:
                            import chardet
                            detected = chardet.detect(content)
                            if detected['encoding']:
                                text = content.decode(detected['encoding'])
                            else:
                                raise ValueError("Could not detect file encoding")
                    else:
                        text = str(content)
                        
                # Generate file ID from content
                file_hash = hashlib.md5(text.encode()).hexdigest()
                
            else:  # It's a path
                file_path = Path(file_path_or_obj)
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # Handle different file types
                if file_path.suffix.lower() == '.pdf':
                    # Handle PDF file
                    with open(file_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text() + "\n"
                else:
                    # Handle other file types as before
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            text = f.read()
                    except UnicodeDecodeError:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            import chardet
                            detected = chardet.detect(content)
                            if detected['encoding']:
                                text = content.decode(detected['encoding'])
                            else:
                                raise ValueError("Could not detect file encoding")
                
                # Generate file ID
                file_hash = hashlib.md5(str(file_path).encode()).hexdigest()

            # Ensure we have valid text content
            if not text.strip():
                raise ValueError("No text content could be extracted from the file")

            # Create chunks using config settings
            chunks = self._create_chunks(
                text, 
                chunk_size=self.config.chunk_size, 
                overlap=self.config.chunk_overlap
            )
            
            # Store chunks
            chunk_files = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_hash}_{i}"
                chunk_file = self.chunks_dir / f"{chunk_id}.txt"
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    f.write(chunk)
                chunk_files.append(str(chunk_file))
            
            # Update metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                'file_type': 'application/pdf' if filename.lower().endswith('.pdf') else 'text/plain',
                'added_at': datetime.now().isoformat(),
                'chunk_count': len(chunks),
                'size': len(text.encode('utf-8')),
                'filename': filename if hasattr(file_path_or_obj, 'name') else str(file_path_or_obj)
            })
            
            # Store metadata
            metadata_file = self.base_path / 'metadata' / f"{file_hash}.json"
            metadata_file.parent.mkdir(exist_ok=True, parents=True)
            
            print(f"Debug - Storing file metadata:")
            print(f"  Path: {metadata_file.absolute()}")
            print(f"  Hash: {file_hash}")
            print(f"  Metadata: {metadata}")
            
            # Add content to metadata
            metadata['content'] = text
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"Debug - Successfully stored metadata at: {metadata_file}")
            
            # Add processed content to ChromaDB
            file_id = str(hash(text))
            
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[file_id]
            )
            
            return file_id
            
        except Exception as e:
            logging.error(f"Error adding file to vector store: {str(e)}")
            raise

    async def search(self, embedding: List[float], filters: Optional[Dict[str, Any]] = None, 
                    limit: int = 10) -> List[Dict[str, Any]]:
        """Search ChromaDB collection."""
        try:
            # Get or create default collection
            collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                embedding_function=self.embedding_function
            )
            
            # Query collection
            results = collection.query(
                query_embeddings=[embedding],
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
            logging.error(f"Error searching vector store: {str(e)}")
            return []

    async def get_filtered_items(self, filters: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Get items from ChromaDB using filters."""
        try:
            results = self.collection.get(
                where=filters.get('filters', {}),
                limit=limit
            )
            
            return [{
                "content": doc,
                "metadata": meta
            } for doc, meta in zip(results['documents'], results['metadatas'])]
            
        except Exception as e:
            logging.error(f"Error getting filtered items: {str(e)}")
            return []

    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file information from ChromaDB."""
        try:
            result = self.collection.get(
                ids=[file_id],
                include=['documents', 'metadatas']
            )
            
            if result['ids']:
                return {
                    'content': result['documents'][0],
                    **result['metadatas'][0]
                }
            return None
            
        except Exception as e:
            logging.error(f"Error getting file info: {str(e)}")
            return None

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from ChromaDB."""
        try:
            self.collection.delete(ids=[file_id])
            return True
        except Exception as e:
            logging.error(f"Error deleting file: {str(e)}")
            return False

    def _calculate_storage_size(self) -> float:
        """Calculate total storage size in MB."""
        try:
            total_size = 0
            for root, _, files in os.walk(self.base_path):
                for file in files:
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception as e:
            logging.error(f"Error calculating storage size: {str(e)}")
            return 0.0

    async def delete_index(self, index_name: str) -> bool:
        """Delete an index and all its contents."""
        try:
            if index_name in self.indices:
                self.client.delete_collection(index_name)
                del self.indices[index_name]
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting index: {str(e)}")
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
        """Get all files stored in a specific index, grouped by root files."""
        try:
            self._reload_indices()
            self._ensure_collection(index_name)
            
            collection = self.indices[index_name]
            results = collection.get()
            
            if not results['ids']:
                return []
            
            # Group chunks by file_id
            file_groups = {}
            for doc_id, doc, meta in zip(results['ids'], results['documents'], results['metadatas']):
                file_id = meta.get('file_id')
                if file_id:
                    if file_id not in file_groups:
                        # Initialize group with root metadata if this is a root chunk
                        if meta.get('is_root', False):
                            file_groups[file_id] = {
                                "id": doc_id,
                                "content": doc,
                                "metadata": {
                                    **meta,
                                    "chunks": []
                                }
                            }
                    else:
                        # Add non-root chunks to the chunks list
                        if not meta.get('is_root', False):
                            file_groups[file_id]["metadata"]["chunks"].append({
                                "id": doc_id,
                                "content": doc,
                                "metadata": meta
                            })
            
            # Convert groups to list and sort by added_at
            contents = list(file_groups.values())
            contents.sort(key=lambda x: x["metadata"].get("added_at", ""), reverse=True)
            
            logging.info(f"Retrieved {len(contents)} root files from index {index_name}")
            return contents
            
        except Exception as e:
            logging.error(f"Error getting index contents: {str(e)}")
            return []

    async def delete_file_from_index(self, index_name: str, file_id: str) -> bool:
        """Delete a file and all its chunks from an index."""
        try:
            if index_name not in self.indices:
                raise ValueError(f"Index {index_name} not found")
            
            collection = self.indices[index_name]
            
            # Get all chunks with matching file_id
            results = collection.get(
                where={"file_id": file_id}
            )
            
            if results['ids']:
                # Delete all chunks associated with this file
                collection.delete(
                    ids=results['ids']
                )
                logging.info(f"Deleted file {file_id} and {len(results['ids'])} associated chunks")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error deleting file from index: {str(e)}")
            return False

    def _ensure_collection(self, index_name: str):
        """Ensure collection exists and is properly initialized."""
        if index_name not in self.indices:
            try:
                collection = self.client.get_collection(
                    name=index_name,
                    embedding_function=self.embedding_function
                )
                self.indices[index_name] = collection
                logging.info(f"Loaded existing collection: {index_name}")
            except:
                collection = self.client.create_collection(
                    name=index_name,
                    embedding_function=self.embedding_function
                )
                self.indices[index_name] = collection
                logging.info(f"Created new collection: {index_name}")

    async def update_embeddings(self, ids: List[str], embeddings: List[List[float]]) -> Dict[str, Any]:
        """Update embeddings for existing items in ChromaDB.
        
        Args:
            ids: List of document IDs to update
            embeddings: List of new embeddings to assign
            
        Returns:
            Dict containing stats about the update operation
        """
        try:
            if len(ids) != len(embeddings):
                raise ValueError("Number of IDs must match number of embeddings")
            
            # Get or create default collection
            collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                embedding_function=self.embedding_function
            )
            
            # Update embeddings in batches
            batch_size = self.config.batch_size
            processed = 0
            failed = 0
            
            for i in range(0, len(ids), batch_size):
                batch_end = min(i + batch_size, len(ids))
                try:
                    collection.update(
                        ids=ids[i:batch_end],
                        embeddings=embeddings[i:batch_end]
                    )
                    processed += batch_end - i
                except Exception as e:
                    logging.error(f"Error updating batch {i}-{batch_end}: {str(e)}")
                    failed += batch_end - i
            
            return {
                "processed": processed,
                "failed": failed
            }
            
        except Exception as e:
            logging.error(f"Error updating embeddings: {str(e)}")
            return {
                "processed": 0,
                "failed": len(ids)
            }