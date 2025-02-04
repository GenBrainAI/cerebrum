from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
from pathlib import Path
import json
import hashlib
import io

from .context_provider import ContextProvider
from .knowledge_base import KnowledgeBase
from .vector_store import VectorStore, VectorStoreConfig
from .context_database import ContextDatabase
from ..tools.web_scraper_tool import WebScraperTool
from ..tools.repo_scraper import RepoScraper

logger = logging.getLogger(__name__)

class DataSource:
    """Data source types for context preparation."""
    WEB = "web"
    REPOSITORY = "repository"
    FILE = "file"
    API = "api"
    CUSTOM = "custom"

class PreparedData:
    """Container for prepared data that can be reused across states."""
    def __init__(
        self,
        content: Union[str, Dict[str, Any]],
        source_type: str,
        metadata: Dict[str, Any],
        data_hash: Optional[str] = None
    ):
        self.content = content
        self.source_type = source_type
        self.metadata = metadata
        self.data_hash = data_hash or self._generate_hash()
        self.created_at = datetime.now().isoformat()
    
    def _generate_hash(self) -> str:
        """Generate a unique hash for the data."""
        content_str = str(self.content)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "content": self.content,
            "source_type": self.source_type,
            "metadata": self.metadata,
            "data_hash": self.data_hash,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PreparedData':
        """Create from dictionary."""
        return cls(
            content=data["content"],
            source_type=data["source_type"],
            metadata=data["metadata"],
            data_hash=data.get("data_hash")
        )

class UnifiedContextManager:
    """Unified manager for all context types in Cerebrum.
    
    This class provides a centralized interface for managing:
    1. Knowledge Base Context
    2. Vector Store Context
    3. Task Context
    4. System Context
    5. Documentation Context
    6. Prepared Data Management
    """
    
    def __init__(self, data_dir: str = "persistent_state/prepared_data"):
        """Initialize all context components."""
        self.context_db = ContextDatabase()
        self.context_provider = ContextProvider()
        self.context_provider.context_db = self.context_db  # Set the context_db after initialization
        self.knowledge_base = KnowledgeBase()
        self.vector_store = VectorStore()
        self.web_scraper = WebScraperTool()
        self.repo_scraper = RepoScraper()
        
        # Set up prepared data storage
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.prepared_data: Dict[str, PreparedData] = {}
        self._load_prepared_data()
        
        # Load documentation into knowledge base
        self._initialize_documentation()
    
    def _load_prepared_data(self):
        """Load previously prepared data."""
        try:
            data_file = self.data_dir / "prepared_data.json"
            if data_file.exists():
                with open(data_file, 'r') as f:
                    data_dict = json.load(f)
                    for data_hash, data in data_dict.items():
                        self.prepared_data[data_hash] = PreparedData.from_dict(data)
                logger.info(f"Loaded {len(self.prepared_data)} prepared data entries")
        except Exception as e:
            logger.error(f"Error loading prepared data: {str(e)}")
    
    def _save_prepared_data(self):
        """Save prepared data to disk."""
        try:
            data_file = self.data_dir / "prepared_data.json"
            data_dict = {
                data_hash: data.to_dict()
                for data_hash, data in self.prepared_data.items()
            }
            with open(data_file, 'w') as f:
                json.dump(data_dict, f, indent=2)
            logger.info(f"Saved {len(self.prepared_data)} prepared data entries")
        except Exception as e:
            logger.error(f"Error saving prepared data: {str(e)}")
    
    async def prepare_data(
        self,
        source_type: str,
        source: Union[str, Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> PreparedData:
        """Prepare data for use in context system.
        
        Args:
            source_type: Type of data source (web, repository, file, api, custom)
            source: Source identifier or data
            metadata: Additional metadata about the data
            
        Returns:
            PreparedData object containing the prepared data
        """
        try:
            content = None
            if source_type == DataSource.WEB:
                content = await self.web_scraper.scrape_url(source)
            elif source_type == DataSource.REPOSITORY:
                content = await self.repo_scraper.scrape_repository(source)
            elif source_type == DataSource.FILE:
                with open(source, 'r') as f:
                    content = f.read()
            elif source_type == DataSource.API:
                # Handle API data source
                pass
            elif source_type == DataSource.CUSTOM:
                content = source
            else:
                raise ValueError(f"Unsupported source type: {source_type}")
            
            # Create prepared data
            prepared = PreparedData(
                content=content,
                source_type=source_type,
                metadata=metadata or {}
            )
            
            # Store for reuse
            self.prepared_data[prepared.data_hash] = prepared
            self._save_prepared_data()
            
            return prepared
            
        except Exception as e:
            logger.error(f"Error preparing data: {str(e)}")
            raise
    
    async def add_prepared_data_to_context(
        self,
        data_hash: str,
        task_id: str,
        context_type: str,
        priority: int = 50
    ) -> bool:
        """Add prepared data to task context."""
        # Get prepared data
        if data_hash not in self.prepared_data:
            raise ValueError(f"No prepared data found for hash {data_hash}")
        
        try:
            prepared = self.prepared_data[data_hash]
            
            # Add to appropriate store based on context type
            source_id = None
            metadata = {
                **prepared.metadata,
                "source_type": str(prepared.source_type),  # Convert enum to string
                "data_hash": prepared.data_hash,
                "prepared_at": prepared.created_at  # Already in ISO format
            }
            
            if context_type == "knowledge":
                # Add to knowledge base
                source_id = self.knowledge_base.add_entry(
                    content=prepared.content,
                    metadata=metadata
                )
            elif context_type == "vector":
                # Add to vector store
                source_id = await self.vector_store.add_text(
                    text=prepared.content,
                    metadata={
                        **metadata,
                        "type": "text",
                        "added_at": datetime.now().isoformat(),
                        "size": len(prepared.content)
                    }
                )
            else:
                raise ValueError(f"Unsupported context type: {context_type}")
            
            if not source_id:
                raise ValueError("Failed to store context data")
            
            # Add context reference
            await self.context_provider.add_context_to_task(
                task_id=task_id,
                type=context_type,
                source_id=source_id,
                priority=priority,
                metadata=metadata
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding prepared data to context: {str(e)}")
            if isinstance(e, ValueError):
                raise
            return False
    
    def get_prepared_data(
        self,
        source_type: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[PreparedData]:
        """Get prepared data matching filters."""
        try:
            filtered_data = []
            for data in self.prepared_data.values():
                if source_type and data.source_type != source_type:
                    continue
                    
                if metadata_filter:
                    matches = True
                    for key, value in metadata_filter.items():
                        if key not in data.metadata or data.metadata[key] != value:
                            matches = False
                            break
                    if not matches:
                        continue
                        
                filtered_data.append(data)
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error getting prepared data: {str(e)}")
            return []
    
    async def _initialize_documentation(self):
        """Initialize documentation in knowledge base."""
        try:
            # Get documentation path
            docs_path = Path("docs/tool_development_guide.md")
            
            if docs_path.exists() and docs_path.is_file():
                # Read documentation content
                content = docs_path.read_text()
                
                # Add to knowledge base
                self.knowledge_base.add_entry(
                    content=content,
                    domain="tool_development",
                    metadata={
                        "type": "guide",
                        "source": str(docs_path)
                    }
                )
                logger.info("Documentation initialized in knowledge base")
            else:
                logger.warning("Documentation file not found")
                
        except Exception as e:
            logger.error(f"Error initializing documentation: {str(e)}")
            raise
    
    async def add_context_to_task(
        self,
        task_id: str,
        content: str,
        context_type: str = "knowledge",
        metadata: Optional[Dict[str, Any]] = None,
        priority: int = 50
    ) -> bool:
        """Add context to a task."""
        try:
            # Add to knowledge base if needed
            if context_type == "knowledge":
                entry_id = self.knowledge_base.add_entry(content, metadata)
                source_id = entry_id
            elif context_type == "vector":
                # Add to vector store
                try:
                    source_id = await self.vector_store.add_text(
                        text=content,
                        metadata=metadata or {}
                    )
                except Exception as e:
                    logger.error(f"Error adding text to vector store: {str(e)}")
                    return False
            else:
                source_id = metadata.get("source_id") if metadata else None
            
            if not source_id:
                logger.error("No source ID available for context")
                return False
            
            # Add context reference through provider
            try:
                await self.context_provider.add_context_to_task(
                    task_id=task_id,
                    type=context_type,
                    source_id=source_id,
                    priority=priority,
                    metadata=metadata or {}
                )
                return True
            except Exception as e:
                logger.error(f"Error adding context to task: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding context to task: {str(e)}")
            return False
    
    async def get_task_context(
        self,
        task_id: str,
        context_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get context for a task."""
        try:
            task_context = self.context_provider.task_context_manager.get_task_context(task_id)
            if not task_context:
                return []
            
            contexts = []
            for context_ref in task_context.contexts:
                # Filter by type if specified
                if context_types and context_ref.type not in context_types:
                    continue
                
                # Get context data based on type
                if context_ref.type == "knowledge":
                    entry = self.knowledge_base.get_entry(context_ref.source_id)
                    if entry:
                        contexts.append({
                            "id": str(context_ref.id),
                            "type": "knowledge",
                            "content": entry["content"],
                            "metadata": {**context_ref.metadata, **entry.get("metadata", {})},
                            "priority": context_ref.priority
                        })
                elif context_ref.type == "vector":
                    content = await self.vector_store.get_content(context_ref.source_id)
                    if content:
                        contexts.append({
                            "id": str(context_ref.id),
                            "type": "vector",
                            "content": content["content"],
                            "metadata": {**context_ref.metadata, **content.get("metadata", {})},
                            "priority": context_ref.priority
                        })
            
            # Sort by priority
            contexts.sort(key=lambda x: x.get("priority", 0), reverse=True)
            return contexts
            
        except Exception as e:
            logger.error(f"Error getting task context: {str(e)}")
            return []
    
    async def search_knowledge(
        self,
        query: str,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge base."""
        return self.knowledge_base.get_knowledge(
            query=query,
            domain=domain,
            tags=tags
        )
    
    async def search_code(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search vector store for code."""
        return await self.vector_store.search(
            query=query,
            filters=filters,
            limit=limit
        )
    
    async def add_web_content(
        self,
        url: str,
        context_type: str = "knowledge",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Scrape and add web content to context."""
        try:
            # Scrape content
            content = await self.web_scraper.scrape_url(url)
            
            if context_type == "knowledge":
                # Add to knowledge base
                return await self.knowledge_base.add_knowledge(
                    content=content,
                    domain=metadata.get("domain", "web"),
                    metadata={
                        **(metadata or {}),
                        "source_url": url,
                        "scraped_at": datetime.now().isoformat()
                    }
                )
            elif context_type == "vector":
                # Add to vector store
                return await self.vector_store.add_file(
                    content,
                    metadata={
                        **(metadata or {}),
                        "source_url": url,
                        "scraped_at": datetime.now().isoformat()
                    }
                )
            else:
                raise ValueError(f"Unsupported context type: {context_type}")
                
        except Exception as e:
            logger.error(f"Error adding web content: {str(e)}")
            raise
    
    async def add_repository(
        self,
        repo_url: str,
        context_type: str = "vector",
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Add repository content to context."""
        try:
            # Scrape repository
            repo_content = await self.repo_scraper.scrape_repository(repo_url)
            
            added_ids = []
            for file_path, content in repo_content.items():
                if context_type == "vector":
                    # Add to vector store
                    file_id = await self.vector_store.add_file(
                        content,
                        metadata={
                            **(metadata or {}),
                            "repo_url": repo_url,
                            "file_path": file_path,
                            "added_at": datetime.now().isoformat()
                        }
                    )
                    added_ids.append(file_id)
                elif context_type == "knowledge":
                    # Add to knowledge base
                    knowledge_id = await self.knowledge_base.add_knowledge(
                        content=content,
                        domain=metadata.get("domain", "repository"),
                        metadata={
                            **(metadata or {}),
                            "repo_url": repo_url,
                            "file_path": file_path,
                            "added_at": datetime.now().isoformat()
                        }
                    )
                    added_ids.append(knowledge_id)
                    
            return added_ids
            
        except Exception as e:
            logger.error(f"Error adding repository: {str(e)}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about all context types."""
        try:
            return {
                "knowledge_base": self.knowledge_base.get_statistics(),
                "vector_store": self.vector_store.get_statistics(),
                "task_contexts": len(self.context_provider.task_context_manager.task_contexts),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {} 