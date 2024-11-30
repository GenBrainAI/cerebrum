# src/server/context/knowledge_base.py

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path
import logging

class KnowledgeBase:
    """Manages domain knowledge with metadata, versioning, and categorization."""
    
    def __init__(self, base_path: str = "persistent_state/context/knowledge_base"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_path / "knowledge_index.json"
        self.knowledge_index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """Load or create the knowledge index."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            return {
                "domains": {},
                "entries": {},
                "tags": {},
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error loading knowledge index: {str(e)}")
            raise
    
    def _save_index(self):
        """Save the current state of the knowledge index."""
        try:
            self.knowledge_index["last_updated"] = datetime.now().isoformat()
            with open(self.index_file, 'w') as f:
                json.dump(self.knowledge_index, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving knowledge index: {str(e)}")
            raise
        
    async def add_knowledge(
        self,
        content: str,
        domain: str,
        metadata: Dict[str, Any],
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add new knowledge entry with metadata and tags.
        Returns the ID of the new entry.
        """
        try:
            # Generate unique ID for the entry
            entry_id = f"knowledge_{len(self.knowledge_index['entries'])}_{hash(content)}"
            
            # Extract tags from metadata if not provided directly
            if tags is None and metadata and 'tags' in metadata:
                tags = metadata['tags']
            
            # Create entry
            entry = {
                "id": entry_id,
                "content": content,
                "domain": domain,
                "metadata": metadata,
                "tags": tags or [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "version": 1
            }
            
            # Update index structures
            self.knowledge_index["entries"][entry_id] = entry
            
            # Update domain index
            if domain not in self.knowledge_index["domains"]:
                self.knowledge_index["domains"][domain] = []
            self.knowledge_index["domains"][domain].append(entry_id)
            
            # Update tags index
            for tag in entry["tags"]:
                if tag not in self.knowledge_index["tags"]:
                    self.knowledge_index["tags"][tag] = []
                self.knowledge_index["tags"][tag].append(entry_id)
            
            # Save changes
            self._save_index()
            
            return entry_id
                
        except Exception as e:
            self.logger.error(f"Error adding knowledge entry: {str(e)}")
            raise

    async def update_knowledge(
        self,
        entry_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update an existing knowledge entry."""
        try:
            if entry_id not in self.knowledge_index["entries"]:
                raise ValueError(f"Entry not found: {entry_id}")
            
            entry = self.knowledge_index["entries"][entry_id]
            
            # Update fields if provided
            if content is not None:
                entry["content"] = content
                entry["version"] += 1
            
            if metadata is not None:
                entry["metadata"].update(metadata)
            
            if tags is not None:
                # Remove old tags from index
                for tag in entry["tags"]:
                    self.knowledge_index["tags"][tag].remove(entry_id)
                
                # Add new tags
                entry["tags"] = tags
                for tag in tags:
                    if tag not in self.knowledge_index["tags"]:
                        self.knowledge_index["tags"][tag] = []
                    self.knowledge_index["tags"][tag].append(entry_id)
            
            entry["updated_at"] = datetime.now().isoformat()
            
            # Save changes
            self._save_index()
            
            return entry
            
        except Exception as e:
            logging.error(f"Error updating knowledge entry: {str(e)}")
            raise

    def get_knowledge(
        self,
        entry_id: Optional[str] = None,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve knowledge entries by ID, domain, or tags.
        Returns a list of matching entries.
        
        Args:
            entry_id: Specific entry ID to retrieve
            domain: Domain to filter by
            tags: List of tags to filter by (entries must have all tags)
                
        Returns:
            List of matching knowledge entries
        """
        try:
            results = set()
            
            # If entry_id is provided, return just that entry
            if entry_id:
                entry = self.knowledge_index["entries"].get(entry_id)
                return [entry] if entry else []
            
            # Filter by domain
            if domain:
                domain_entries = self.knowledge_index["domains"].get(domain, [])
                results.update(domain_entries)
            
            # Filter by tags
            if tags:
                # Get entries for the first tag
                tag_entries = set()
                for tag in tags:
                    if tag in self.knowledge_index["tags"]:
                        # For first tag, initialize the set
                        if not tag_entries:
                            tag_entries = set(self.knowledge_index["tags"][tag])
                        # For subsequent tags, keep only entries that have all tags
                        else:
                            tag_entries.intersection_update(self.knowledge_index["tags"][tag])
                    else:
                        # If any tag doesn't exist, return empty list
                        return []
                
                # If domain was specified, intersect with domain results
                if domain:
                    results.intersection_update(tag_entries)
                else:
                    results = tag_entries
            
            # If no filters provided, return all entries
            if not domain and not tags:
                results = set(self.knowledge_index["entries"].keys())
            
            # Convert IDs to full entries
            return [self.knowledge_index["entries"][entry_id] for entry_id in results]
                
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge entries: {str(e)}")
            raise
        
    def get_domain_summary(self, domain: str) -> Dict[str, Any]:
        """
        Get summary information about a domain.
        
        Args:
            domain: The domain to summarize
            
        Returns:
            Dictionary containing domain statistics and metadata
        """
        try:
            if domain not in self.knowledge_index["domains"]:
                return {
                    "domain": domain,
                    "entry_count": 0,
                    "tags": [],
                    "last_updated": None
                }
            
            entries = [
                self.knowledge_index["entries"][entry_id]
                for entry_id in self.knowledge_index["domains"][domain]
            ]
            
            # Collect all tags used in this domain
            domain_tags = set()
            latest_update = None
            
            for entry in entries:
                domain_tags.update(entry["tags"])
                entry_updated = datetime.fromisoformat(entry["updated_at"])
                if not latest_update or entry_updated > latest_update:
                    latest_update = entry_updated
            
            return {
                "domain": domain,
                "entry_count": len(entries),
                "tags": sorted(list(domain_tags)),
                "last_updated": latest_update.isoformat() if latest_update else None
            }
            
        except Exception as e:
            logging.error(f"Error getting domain summary: {str(e)}")
            raise

    def get_tag_summary(self, tag: str) -> Dict[str, Any]:
        """
        Get summary information about a tag.
        
        Args:
            tag: The tag to summarize
            
        Returns:
            Dictionary containing tag statistics and metadata
        """
        try:
            if tag not in self.knowledge_index["tags"]:
                return {
                    "tag": tag,
                    "entry_count": 0,
                    "domains": [],
                    "last_updated": None
                }
            
            entries = [
                self.knowledge_index["entries"][entry_id]
                for entry_id in self.knowledge_index["tags"][tag]
            ]
            
            # Collect all domains using this tag
            tag_domains = set()
            latest_update = None
            
            for entry in entries:
                tag_domains.add(entry["domain"])
                entry_updated = datetime.fromisoformat(entry["updated_at"])
                if not latest_update or entry_updated > latest_update:
                    latest_update = entry_updated
            
            return {
                "tag": tag,
                "entry_count": len(entries),
                "domains": sorted(list(tag_domains)),
                "last_updated": latest_update.isoformat() if latest_update else None
            }
            
        except Exception as e:
            logging.error(f"Error getting tag summary: {str(e)}")
            raise

    async def delete_knowledge(self, entry_id: str) -> bool:
        """
        Delete a knowledge entry.
        
        Args:
            entry_id: ID of the entry to delete
            
        Returns:
            True if entry was deleted, False if not found
        """
        try:
            if entry_id not in self.knowledge_index["entries"]:
                return False
            
            entry = self.knowledge_index["entries"][entry_id]
            
            # Remove from domains index
            if entry["domain"] in self.knowledge_index["domains"]:
                self.knowledge_index["domains"][entry["domain"]].remove(entry_id)
            
            # Remove from tags index
            for tag in entry["tags"]:
                if tag in self.knowledge_index["tags"]:
                    self.knowledge_index["tags"][tag].remove(entry_id)
            
            # Remove entry
            del self.knowledge_index["entries"][entry_id]
            
            # Save changes
            self._save_index()
            
            return True
            
        except Exception as e:
            logging.error(f"Error deleting knowledge entry: {str(e)}")
            raise

    def export_domain(self, domain: str, export_path: Optional[str] = None) -> str:
        """
        Export all entries from a domain to a JSON file.
        
        Args:
            domain: Domain to export
            export_path: Optional path for export file
            
        Returns:
            Path to the exported file
        """
        try:
            if domain not in self.knowledge_index["domains"]:
                raise ValueError(f"Domain not found: {domain}")
            
            entries = [
                self.knowledge_index["entries"][entry_id]
                for entry_id in self.knowledge_index["domains"][domain]
            ]
            
            export_data = {
                "domain": domain,
                "exported_at": datetime.now().isoformat(),
                "entries": entries
            }
            
            if not export_path:
                export_path = os.path.join(self.base_path, f"export_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return export_path
                
        except Exception as e:
            self.logger.error(f"Error exporting domain: {str(e)}")
            raise

    async def import_domain(self, import_path: str, merge: bool = False) -> int:
        """
        Import entries from a JSON export file.
        
        Args:
            import_path: Path to the import file
            merge: If True, merge with existing entries; if False, overwrite
            
        Returns:
            Number of entries imported
        """
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            domain = import_data["domain"]
            entries = import_data["entries"]
            
            if not merge and domain in self.knowledge_index["domains"]:
                # Delete existing entries for this domain
                for entry_id in self.knowledge_index["domains"][domain]:
                    await self.delete_knowledge(entry_id)
            
            # Import entries
            imported_count = 0
            for entry in entries:
                try:
                    await self.add_knowledge(
                        content=entry["content"],
                        domain=domain,
                        metadata=entry["metadata"],
                        tags=entry["tags"]
                    )
                    imported_count += 1
                except Exception as e:
                    logging.error(f"Error importing entry: {str(e)}")
                    continue
            
            return imported_count
            
        except Exception as e:
            logging.error(f"Error importing domain: {str(e)}")
            raise