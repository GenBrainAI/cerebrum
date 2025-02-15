# src/server/context/knowledge_base.py

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class KnowledgeBase:
    """Knowledge base for storing and retrieving knowledge."""
    
    def __init__(self, base_path: str = "persistent_state/knowledge_base"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.knowledge_file = self.base_path / "knowledge.json"
        
        # Load existing knowledge if available
        self.knowledge = {}
        self.next_id = 1
        
        # Initialize knowledge index for efficient querying
        self.knowledge_index = {}
        
        self._load_knowledge()
        self._build_index()
    
    def _build_index(self):
        """Build knowledge index for efficient querying."""
        self.knowledge_index = {}
        for knowledge_id, entry in self.knowledge.items():
            # Index by domain
            domain = entry["domain"]
            if isinstance(domain, dict):
                domain = domain.get("domain", "general")
            if domain not in self.knowledge_index:
                self.knowledge_index[domain] = []
            self.knowledge_index[domain].append(knowledge_id)
            
            # Index by tags
            for tag in entry["tags"]:
                if tag not in self.knowledge_index:
                    self.knowledge_index[tag] = []
                self.knowledge_index[tag].append(knowledge_id)
                
            # Index by metadata categories
            if "metadata" in entry and isinstance(entry["metadata"], dict):
                for key, value in entry["metadata"].items():
                    if isinstance(value, str):
                        index_key = f"{key}:{value}"
                        if index_key not in self.knowledge_index:
                            self.knowledge_index[index_key] = []
                        self.knowledge_index[index_key].append(knowledge_id)
    
    def _load_knowledge(self):
        """Load knowledge from disk if available."""
        try:
            if self.knowledge_file.exists():
                with open(self.knowledge_file, 'r') as f:
                    data = json.load(f)
                    self.knowledge = data.get('knowledge', {})
                    self.next_id = data.get('next_id', 1)
                self._build_index()
        except Exception as e:
            logger.error(f"Error loading knowledge base: {str(e)}")
            # Keep default empty state if load fails
            
    def _save_knowledge(self):
        """Save knowledge to disk."""
        try:
            with open(self.knowledge_file, 'w') as f:
                json.dump({
                    'knowledge': self.knowledge,
                    'next_id': self.next_id
                }, f, indent=2)
            self._build_index()
        except Exception as e:
            logger.error(f"Error saving knowledge base: {str(e)}")
            raise
    
    async def add_entry(
        self,
        content: str,
        domain: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Add knowledge to the knowledge base."""
        try:
            knowledge_id = f"knowledge_{self.next_id}"
            self.next_id += 1
            
            # Combine tags from both metadata and tags parameter
            combined_tags = set(tags or [])
            if metadata and "tags" in metadata:
                combined_tags.update(metadata.get("tags", []))
            
            # Create metadata with domain and combined tags
            entry_metadata = {
                **(metadata or {}),
                "domain": domain,
                "tags": list(combined_tags)  # Convert back to list
            }
            
            self.knowledge[knowledge_id] = {
                "content": content,
                "domain": domain,
                "metadata": entry_metadata,
                "tags": list(combined_tags),  # Store tags at top level too
                "created_at": datetime.now().isoformat()
            }
            
            self._save_knowledge()
            return knowledge_id
            
        except Exception as e:
            logger.error(f"Error adding knowledge entry: {str(e)}")
            raise

    async def add_knowledge(
        self,
        content: str,
        domain: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Add knowledge to the knowledge base."""
        return await self.add_entry(content, domain, metadata, tags)

    async def get_knowledge(
        self,
        domain: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get knowledge entries matching the filter criteria."""
        return self.get_entries(domain, metadata_filter, query, limit)

    async def update_knowledge(self, knowledge_id: str, content: str) -> bool:
        """Update a knowledge entry's content."""
        return self.update_entry(knowledge_id, content)

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """Delete a knowledge entry."""
        return self.delete_entry(knowledge_id)

    async def get_entry(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific knowledge entry by ID."""
        try:
            if knowledge_id not in self.knowledge:
                return None
            
            entry = self.knowledge[knowledge_id]
            return {
                "id": knowledge_id,
                "content": entry["content"],
                "domain": entry["domain"],
                "metadata": entry["metadata"],
                "tags": entry["tags"],
                "created_at": entry["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge entry: {str(e)}")
            return None

    def update_entry(self, knowledge_id: str, content: str) -> bool:
        """Update a knowledge entry's content."""
        try:
            if knowledge_id not in self.knowledge:
                return False
            
            self.knowledge[knowledge_id]["content"] = content
            self._save_knowledge()
            return True
            
        except Exception as e:
            logger.error(f"Error updating knowledge entry: {str(e)}")
            return False

    def delete_entry(self, knowledge_id: str) -> bool:
        """Delete a knowledge entry."""
        try:
            if knowledge_id not in self.knowledge:
                return False
            
            del self.knowledge[knowledge_id]
            self._save_knowledge()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting knowledge entry: {str(e)}")
            return False

    def get_entries(
        self,
        domain: Optional[str] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get knowledge entries matching the filter criteria."""
        try:
            results = []
            
            # Start with all entries
            candidate_ids = set(self.knowledge.keys())
            
            # Filter by domain if specified
            if domain:
                domain_ids = set()
                for knowledge_id, entry in self.knowledge.items():
                    entry_domain = entry["domain"]
                    if isinstance(entry_domain, dict):
                        entry_domain = entry_domain.get("domain", "general")
                    if entry_domain == domain:
                        domain_ids.add(knowledge_id)
                candidate_ids &= domain_ids
            
            # Apply metadata filter
            if metadata_filter:
                filtered_ids = set()
                for knowledge_id in candidate_ids.copy():
                    entry = self.knowledge[knowledge_id]
                    matches = True
                    
                    for key, value in metadata_filter.items():
                        if key == "tags" and isinstance(value, list):
                            # Check if any of the required tags are present
                            if not any(tag in entry["tags"] for tag in value):
                                matches = False
                                break
                        elif key in entry["metadata"]:
                            if entry["metadata"][key] != value:
                                matches = False
                                break
                        else:
                            matches = False
                            break
                    
                    if matches:
                        filtered_ids.add(knowledge_id)
                candidate_ids = filtered_ids
            
            # Process candidates and apply query filter
            for knowledge_id in candidate_ids:
                entry = self.knowledge[knowledge_id]
                
                # Apply query filter if provided
                if query and query.lower() not in entry["content"].lower():
                    continue
                
                results.append({
                    "id": knowledge_id,
                    "content": entry["content"],
                    "domain": entry["domain"],
                    "metadata": entry["metadata"],
                    "tags": entry["tags"],
                    "created_at": entry["created_at"]
                })
            
            # Apply limit
            if limit is not None:
                results = results[:limit]
                
            return results
            
        except Exception as e:
            logger.error(f"Error getting knowledge entries: {str(e)}")
            return []
    
    async def clear(self) -> None:
        """Clear all knowledge entries."""
        try:
            self.knowledge = {}
            self.next_id = 1
            self._save_knowledge()
        except Exception as e:
            logger.error(f"Error clearing knowledge base: {str(e)}")
            raise

    async def export_domain(self, domain: str, export_path: str) -> str:
        """Export all knowledge entries for a domain to a file."""
        try:
            # Get all entries for the domain
            entries = self.get_entries(domain=domain)
            
            # Create export data
            export_data = {
                "domain": domain,
                "entries": entries,
                "exported_at": datetime.now().isoformat()
            }
            
            # Save to file
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return export_path
            
        except Exception as e:
            logger.error(f"Error exporting domain {domain}: {str(e)}")
            raise

    async def import_domain(self, import_path: str) -> int:
        """Import knowledge entries from a file."""
        try:
            # Load import data
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            # Import each entry
            imported_count = 0
            for entry in import_data.get("entries", []):
                try:
                    await self.add_entry(
                        content=entry["content"],
                        domain=entry["domain"],
                        metadata=entry["metadata"],
                        tags=entry["tags"]
                    )
                    imported_count += 1
                except Exception as e:
                    logger.error(f"Error importing entry: {str(e)}")
                    continue
            
            return imported_count
            
        except Exception as e:
            logger.error(f"Error importing from {import_path}: {str(e)}")
            raise
