# src/server/context/__init__.py

from pathlib import Path
import logging
from typing import Optional

from .context_management import ContextDatabase, CodeCatalog
from .vector_store import VectorStore
from .knowledge_base import KnowledgeBase

class ContextManager:
    """
    Facade for the context management system.
    Provides a simplified interface to all context-related functionality.
    """
    _instance = None

    def __new__(cls, base_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(ContextManager, cls).__new__(cls)
            cls._instance._initialize(base_path)
        return cls._instance

    def _initialize(self, base_path: Optional[str] = None):
        """Initialize all components of the context system."""
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path("context_db")
        
        # Create necessary directories
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "code").mkdir(exist_ok=True)
        (self.base_path / "domain_knowledge").mkdir(exist_ok=True)
        
        # Initialize components
        self.context_db = ContextDatabase(str(self.base_path))
        self.code_catalog = CodeCatalog()
        self.knowledge_base = KnowledgeBase(str(self.base_path / "knowledge_base"))
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Context Manager initialized")

    async def index_codebase(self, directory_path: str, exclude_dirs: Optional[list] = None):
        """Index a codebase for both vector search and catalog."""
        self.logger.info(f"Indexing codebase: {directory_path}")
        try:
            # Update code catalog
            await self.code_catalog.index_directory(directory_path)
            
            # Update vector database
            await self.context_db.ingest_code_directory(directory_path, exclude_dirs)
            
            self.logger.info("Codebase indexing completed")
        except Exception as e:
            self.logger.error(f"Error indexing codebase: {str(e)}")
            raise

    async def add_domain_expertise(self, content: str, domain: str, metadata: dict, tags: Optional[list] = None):
        """Add domain expertise to both vector search and knowledge base."""
        self.logger.info(f"Adding domain expertise for domain: {domain}")
        try:
            # Add to vector database
            await self.context_db.add_domain_knowledge(content, metadata)
            
            # Add to knowledge base with more structured organization
            await self.knowledge_base.add_knowledge(
                content=content,
                domain=domain,
                metadata=metadata,
                tags=tags
            )
            
            self.logger.info("Domain expertise added successfully")
        except Exception as e:
            self.logger.error(f"Error adding domain expertise: {str(e)}")
            raise

    async def search(self, query: str, search_code: bool = True, search_domain: bool = True, 
                    num_results: int = 5) -> dict:
        """Combined search across code and domain knowledge."""
        self.logger.info(f"Performing combined search for: {query}")
        try:
            results = {}
            
            if search_code and search_domain:
                results = await self.context_db.combine_context(
                    query=query,
                    num_results=num_results
                )
            elif search_code:
                results = {
                    "code_context": await self.context_db.search_context(
                        query=query,
                        collection_name="code",
                        num_results=num_results
                    )
                }
            elif search_domain:
                results = {
                    "domain_context": await self.context_db.search_context(
                        query=query,
                        collection_name="domain_knowledge",
                        num_results=num_results
                    )
                }
            
            return results
        except Exception as e:
            self.logger.error(f"Error performing search: {str(e)}")
            raise

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """Get detailed information about a specific file."""
        return self.code_catalog.get_file_info(file_path)

    def get_domain_summary(self, domain: str) -> dict:
        """Get summary information about a domain."""
        return self.knowledge_base.get_domain_summary(domain)

    async def export_domain(self, domain: str, export_path: Optional[str] = None) -> str:
        """Export domain knowledge to a file."""
        return self.knowledge_base.export_domain(domain, export_path)

    async def import_domain(self, import_path: str, merge: bool = False) -> int:
        """Import domain knowledge from a file."""
        return await self.knowledge_base.import_domain(import_path, merge)

    def get_statistics(self) -> dict:
        """Get statistics about the context system."""
        stats = {
            "collections": self.context_db.get_collection_stats(),
            "catalog": {
                "total_files": len(self.code_catalog.file_index),
                "total_modules": len(self.code_catalog.module_descriptions)
            },
            "knowledge_base": {
                "total_domains": len(self.knowledge_base.knowledge_index["domains"]),
                "total_entries": len(self.knowledge_base.knowledge_index["entries"]),
                "total_tags": len(self.knowledge_base.knowledge_index["tags"])
            }
        }
        return stats