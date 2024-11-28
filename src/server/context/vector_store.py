import os
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
import numpy as np
from typing import List, Dict, Any, Optional, Union
import asyncio
import logging
from pathlib import Path
import backoff
from datetime import datetime
from dataclasses import dataclass, field

@dataclass
class VectorStoreConfig:
    """Configuration for VectorStore."""
    persist_directory: str
    collection_name: str
    embedding_model: str = "text-embedding-3-small"
    batch_size: int = 100
    max_retries: int = 3
    retry_delay: int = 1
    connection_timeout: int = 30
    max_concurrent_requests: int = 4
    distance_metric: str = "cosine"
    enable_telemetry: bool = False
    metadata_schema: Dict[str, type] = field(default_factory=dict)

class VectorStore:
    """Enhanced vector store with better error handling and performance."""

    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self._client = None
        self._collection = None
        self._embedding_function = None
        self._semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        self._setup_logging()
        self._initialize_store()

    def _setup_logging(self):
        """Set up logging for the vector store."""
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=lambda self: self.config.max_retries,
        max_time=lambda self: self.config.connection_timeout
    )
    def _initialize_store(self):
        """Initialize the vector store with retry logic."""
        try:
            self._client = chromadb.PersistentClient(
                path=self.config.persist_directory,
                settings=Settings(
                    anonymized_telemetry=self.config.enable_telemetry,
                    is_persistent=True,
                    allow_reset=True
                )
            )

            self._embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name=self.config.embedding_model
            )

            self._collection = self._client.get_or_create_collection(
                name=self.config.collection_name,
                embedding_function=self._embedding_function,
                metadata={"hnsw:space": self.config.distance_metric}
            )

            self.logger.info(f"Initialized vector store: {self.config.collection_name}")

        except Exception as e:
            self.logger.error(f"Error initializing vector store: {str(e)}")
            raise

    async def _validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate metadata against schema."""
        if not self.config.metadata_schema:
            return True

        try:
            for key, expected_type in self.config.metadata_schema.items():
                if key in metadata:
                    if not isinstance(metadata[key], expected_type):
                        raise ValueError(
                            f"Invalid type for metadata key '{key}': "
                            f"expected {expected_type}, got {type(metadata[key])}"
                        )
            return True
        except Exception as e:
            self.logger.error(f"Metadata validation failed: {str(e)}")
            return False

    async def add_items(
        self,
        embeddings: np.ndarray,
        metadatas: List[Dict[str, Any]],
        contents: List[str],
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Add items to the vector store in batches."""
        batch_size = batch_size or self.config.batch_size
        stats = {"processed": 0, "failed": 0}

        # Validate input lengths
        if not (len(embeddings) == len(metadatas) == len(contents)):
            raise ValueError("Embeddings, metadatas, and contents must have same length")

        for i in range(0, len(contents), batch_size):
            batch_slice = slice(i, i + batch_size)
            batch_embeddings = embeddings[batch_slice]
            batch_metadatas = metadatas[batch_slice]
            batch_contents = contents[batch_slice]

            try:
                async with self._semaphore:
                    # Validate metadata
                    valid_indices = []
                    for idx, metadata in enumerate(batch_metadatas):
                        if await self._validate_metadata(metadata):
                            valid_indices.append(idx)
                        else:
                            stats["failed"] += 1

                    if not valid_indices:
                        continue

                    # Process valid items
                    valid_embeddings = batch_embeddings[valid_indices]
                    valid_metadatas = [batch_metadatas[i] for i in valid_indices]
                    valid_contents = [batch_contents[i] for i in valid_indices]

                    # Generate IDs
                    ids = [
                        f"item_{hash(content)}_{datetime.now().timestamp()}"
                        for content in valid_contents
                    ]

                    # Add to collection
                    self._collection.add(
                        embeddings=valid_embeddings.tolist(),
                        metadatas=valid_metadatas,
                        documents=valid_contents,
                        ids=ids
                    )

                    stats["processed"] += len(valid_indices)

            except Exception as e:
                self.logger.error(f"Error adding batch: {str(e)}")
                stats["failed"] += len(batch_contents)

        return stats

    async def search(
        self,
        embedding: np.ndarray,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5,
        offset: int = 0,
        include_embeddings: bool = False
    ) -> List[Dict[str, Any]]:
        """Search for similar items with enhanced filtering."""
        try:
            async with self._semaphore:
                results = self._collection.query(
                    query_embeddings=[embedding.tolist()],
                    n_results=limit + offset,
                    where=filters,
                    include=['metadatas', 'documents', 'distances']
                )

                formatted_results = []
                for i in range(offset, min(len(results['ids'][0]), offset + limit)):
                    result = {
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "relevance": 1 - results['distances'][0][i],  # Convert distance to similarity
                    }
                    
                    if include_embeddings:
                        result["embedding"] = self._collection.get(
                            ids=[results['ids'][0][i]],
                            include=['embeddings']
                        )['embeddings'][0]
                    
                    formatted_results.append(result)

                return formatted_results

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise

    async def update_embeddings(
        self,
        ids: List[str],
        embeddings: np.ndarray,
        batch_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update embeddings for existing items in batches."""
        batch_size = batch_size or self.config.batch_size
        stats = {"processed": 0, "failed": 0}

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_embeddings = embeddings[i:i + batch_size]

            try:
                async with self._semaphore:
                    # Get existing items
                    existing_items = self._collection.get(
                        ids=batch_ids,
                        include=['metadatas', 'documents']
                    )

                    # Update items with new embeddings
                    self._collection.update(
                        ids=batch_ids,
                        embeddings=batch_embeddings.tolist(),
                        metadatas=existing_items['metadatas'],
                        documents=existing_items['documents']
                    )

                    stats["processed"] += len(batch_ids)

            except Exception as e:
                self.logger.error(f"Error updating batch: {str(e)}")
                stats["failed"] += len(batch_ids)

        return stats

    async def delete_items(self, ids: List[str]) -> Dict[str, Any]:
        """Delete items from the vector store."""
        try:
            async with self._semaphore:
                self._collection.delete(ids=ids)
                return {"deleted": len(ids)}
        except Exception as e:
            self.logger.error(f"Error deleting items: {str(e)}")
            raise

    async def get_nearest_neighbors(
        self,
        id: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Find nearest neighbors for a specific item."""
        try:
            async with self._semaphore:
                # Get the embedding for the query item
                item = self._collection.get(
                    ids=[id],
                    include=['embeddings']
                )
                
                if not item['embeddings']:
                    raise ValueError(f"Item not found: {id}")

                # Search using the item's embedding
                return await self.search(
                    embedding=np.array(item['embeddings'][0]),
                    filters=filters,
                    limit=k + 1  # Add 1 to account for the item itself
                )[1:]  # Exclude the query item

        except Exception as e:
            self.logger.error(f"Error finding nearest neighbors: {str(e)}")
            raise

    async def get_collection_stats(self) -> Dict[str, float]:
        """Get detailed statistics about the collection."""
        try:
            async with self._semaphore:
                count = self._collection.count()
                peek = self._collection.peek()
                
                # Calculate additional statistics
                stats = {
                    "total_items": count,
                    "sample_metadata_keys": [],
                    "metadata_value_counts": {},
                    "last_modified": None,
                    "embedding_dimension": None
                }

                if peek['metadatas']:
                    first_metadata = peek['metadatas'][0]
                    stats["sample_metadata_keys"] = list(first_metadata.keys())

                    # Get metadata value distributions
                    all_items = self._collection.get(
                        limit=1000,  # Sample for large collections
                        include=['metadatas']
                    )
                    
                    for metadata in all_items['metadatas']:
                        for key, value in metadata.items():
                            if key not in stats["metadata_value_counts"]:
                                stats["metadata_value_counts"][key] = {}
                            if str(value) not in stats["metadata_value_counts"][key]:
                                stats["metadata_value_counts"][key][str(value)] = 0
                            stats["metadata_value_counts"][key][str(value)] += 1

                if peek['embeddings']:
                    stats["embedding_dimension"] = len(peek['embeddings'][0])

                return stats

        except Exception as e:
            self.logger.error(f"Error getting collection stats: {str(e)}")
            raise

    async def create_backup(self, backup_dir: str) -> str:
        """Create a backup of the vector store."""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_path / f"{self.config.collection_name}_{timestamp}.backup"

            async with self._semaphore:
                # Get all items
                all_items = self._collection.get(
                    include=['embeddings', 'metadatas', 'documents']
                )

                # Save to backup file
                backup_data = {
                    "config": self.config.__dict__,
                    "items": {
                        "ids": all_items['ids'],
                        "embeddings": all_items['embeddings'],
                        "metadatas": all_items['metadatas'],
                        "documents": all_items['documents']
                    },
                    "timestamp": timestamp
                }

                import pickle
                with open(backup_file, 'wb') as f:
                    pickle.dump(backup_data, f)

                return str(backup_file)

        except Exception as e:
            self.logger.error(f"Error creating backup: {str(e)}")
            raise

    @classmethod
    async def restore_from_backup(cls, backup_file: str) -> 'VectorStore':
        """Restore a vector store from a backup file."""
        try:
            import pickle
            with open(backup_file, 'rb') as f:
                backup_data = pickle.load(f)

            # Create new instance with backed up config
            config = VectorStoreConfig(**backup_data["config"])
            vector_store = cls(config)

            # Restore items
            items = backup_data["items"]
            await vector_store.add_items(
                embeddings=np.array(items["embeddings"]),
                metadatas=items["metadatas"],
                contents=items["documents"]
            )

            return vector_store

        except Exception as e:
            logging.error(f"Error restoring from backup: {str(e)}")
            raise