from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from uuid import UUID, uuid4
import json
import yaml
import httpx
import asyncio
from pathlib import Path


class SystemContextSource(BaseModel):
    """Source information for a system context entry."""
    type: str = "inline"  # inline, file, url
    location: Optional[str] = None  # file path or URL
    encoding: str = "utf-8"
    cache_ttl: Optional[int] = None  # Time to live in seconds for URL content

class SystemContextEntry(BaseModel):
    """A system context entry holding constant information."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    content: str
    source: SystemContextSource = Field(default_factory=lambda: SystemContextSource())
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    format: str = "text"  # text, json, yaml
    category: str = "general"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_fetch: Optional[datetime] = None

    async def get_content(self) -> str:
        """Get content, fetching from source if needed."""
        if self.source.type == "inline":
            return self.content
            
        # Check if we need to refresh cached content
        if (self.source.cache_ttl and self.last_fetch and 
            (datetime.now() - self.last_fetch).total_seconds() > self.source.cache_ttl):
            await self.refresh_content()
            
        return self.content

    async def refresh_content(self) -> None:
        """Refresh content from source."""
        try:
            if self.source.type == "file":
                self.content = await self._read_file()
            elif self.source.type == "url":
                self.content = await self._fetch_url()
            
            self.last_fetch = datetime.now()
            self.updated_at = datetime.now()
            
        except Exception as e:
            raise ValueError(f"Error refreshing content: {str(e)}")

    async def _read_file(self) -> str:
        """Read content from file."""
        if not self.source.location:
            raise ValueError("No file location specified")
            
        path = Path(self.source.location)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
            
        try:
            async with await asyncio.to_thread(open, path, 'r', encoding=self.source.encoding) as f:
                return await asyncio.to_thread(f.read)
        except Exception as e:
            raise ValueError(f"Error reading file: {str(e)}")

    async def _fetch_url(self) -> str:
        """Fetch content from URL."""
        if not self.source.location:
            raise ValueError("No URL specified")
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.source.location)
                response.raise_for_status()
                return response.text
        except Exception as e:
            raise ValueError(f"Error fetching URL: {str(e)}")

    def format_content(self) -> str:
        """Format content based on its type."""
        if self.format == "json":
            return json.dumps(json.loads(self.content), indent=2)
        elif self.format == "yaml":
            return yaml.dump(yaml.safe_load(self.content), default_flow_style=False)
        return self.content

class SystemContextManager:
    """Manager for system-level constant context information."""
    
    def __init__(self):
        self.contexts: Dict[UUID, SystemContextEntry] = {}
        self._categories: Dict[str, List[UUID]] = {}
        self._tags: Dict[str, List[UUID]] = {}

    async def add_file_context(
        self,
        name: str,
        file_path: Union[str, Path],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        format: str = "text",
        category: str = "general",
        encoding: str = "utf-8"
    ) -> SystemContextEntry:
        """Add a new file-based context entry."""
        source = SystemContextSource(
            type="file",
            location=str(file_path),
            encoding=encoding
        )
        
        entry = SystemContextEntry(
            name=name,
            content="",  # Will be loaded from file
            source=source,
            description=description,
            tags=tags or [],
            format=format,
            category=category
        )
        
        # Load initial content
        await entry.refresh_content()
        
        return self._store_entry(entry)

    async def add_url_context(
        self,
        name: str,
        url: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        format: str = "text",
        category: str = "general",
        cache_ttl: Optional[int] = 3600  # 1 hour default cache
    ) -> SystemContextEntry:
        """Add a new URL-based context entry."""
        source = SystemContextSource(
            type="url",
            location=url,
            cache_ttl=cache_ttl
        )
        
        entry = SystemContextEntry(
            name=name,
            content="",  # Will be loaded from URL
            source=source,
            description=description,
            tags=tags or [],
            format=format,
            category=category
        )
        
        # Load initial content
        await entry.refresh_content()
        
        return self._store_entry(entry)

    def _store_entry(self, entry: SystemContextEntry) -> SystemContextEntry:
        """Store a context entry and update indices."""
        self.contexts[entry.id] = entry
        
        # Update category index
        if entry.category not in self._categories:
            self._categories[entry.category] = []
        self._categories[entry.category].append(entry.id)
        
        # Update tags index
        for tag in entry.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            self._tags[tag].append(entry.id)
        
        return entry


    def add_context(
        self,
        name: str,
        content: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        format: str = "text",
        category: str = "general"
    ) -> SystemContextEntry:
        """Add a new system context entry."""
        entry = SystemContextEntry(
            name=name,
            content=content,
            description=description,
            tags=tags or [],
            format=format,
            category=category
        )
        
        # Store the entry
        self.contexts[entry.id] = entry
        
        # Update category index
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(entry.id)
        
        # Update tags index
        for tag in entry.tags:
            if tag not in self._tags:
                self._tags[tag] = []
            self._tags[tag].append(entry.id)
        
        return entry

    def get_context(self, context_id: UUID) -> Optional[SystemContextEntry]:
        """Get a specific context entry by ID."""
        return self.contexts.get(context_id)

    def get_contexts_by_category(self, category: str) -> List[SystemContextEntry]:
        """Get all context entries in a category."""
        context_ids = self._categories.get(category, [])
        return [self.contexts[cid] for cid in context_ids if cid in self.contexts]

    def get_contexts_by_tags(self, tags: List[str], match_all: bool = True) -> List[SystemContextEntry]:
        """
        Get context entries by tags.
        
        Args:
            tags: List of tags to match
            match_all: If True, entries must have all tags. If False, any tag matches.
        """
        if not tags:
            return []
            
        matching_ids = set()
        for i, tag in enumerate(tags):
            tag_ids = set(self._tags.get(tag, []))
            if i == 0:
                matching_ids = tag_ids
            else:
                if match_all:
                    matching_ids &= tag_ids  # Intersection
                else:
                    matching_ids |= tag_ids  # Union
                    
        return [self.contexts[cid] for cid in matching_ids if cid in self.contexts]

    def search_contexts(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[SystemContextEntry]:
        """
        Search contexts by content and optional filters.
        
        Args:
            query: Text to search for
            category: Optional category filter
            tags: Optional tags filter
        """
        # Start with all contexts or category-filtered contexts
        if category:
            contexts = self.get_contexts_by_category(category)
        else:
            contexts = list(self.contexts.values())
        
        # Apply tag filtering if specified
        if tags:
            tagged_contexts = set(self.get_contexts_by_tags(tags))
            contexts = [c for c in contexts if c in tagged_contexts]
        
        # Filter by query
        query = query.lower()
        return [
            context for context in contexts
            if query in context.name.lower() or 
               query in context.content.lower() or 
               (context.description and query in context.description.lower())
        ]

    def format_system_prompt(
        self,
        context_ids: List[UUID],
        header: str = "Using the following system context:",
        separator: str = "\n\n---\n\n"
    ) -> str:
        """
        Format multiple context entries into a system prompt.
        
        Args:
            context_ids: List of context entry IDs to include
            header: Header text for the prompt
            separator: Separator between contexts
        """
        contexts = []
        for cid in context_ids:
            entry = self.get_context(cid)
            if entry:
                contexts.append(f"{entry.name}:\n{entry.format_content()}")
        
        if not contexts:
            return ""
            
        return f"{header}{separator}{separator.join(contexts)}"

    def format_task_context(
        self,
        task_id: str,
        context_ids: List[UUID],
        query: Optional[str] = None
    ) -> Optional[str]:
        """
        Format context entries for a specific task.
        
        Args:
            task_id: ID of the task
            context_ids: List of context entry IDs to include
            query: Optional query to filter contents
        """
        if query:
            # For now, just use the query to match against the names/descriptions
            # In the future, this could use more sophisticated matching
            matching_ids = [
                cid for cid in context_ids
                if self._content_matches_query(self.get_context(cid), query)
            ]
            context_ids = matching_ids
            
        return self.format_system_prompt(
            context_ids,
            header=f"Task {task_id} system context:",
            separator="\n\n"
        )

    def _content_matches_query(self, context: Optional[SystemContextEntry], query: str) -> bool:
        """Check if a context entry matches a query."""
        if not context or not query:
            return False
            
        query = query.lower()
        return (
            query in context.name.lower() or
            query in context.content.lower() or
            (context.description and query in context.description.lower()) or
            any(query in tag.lower() for tag in context.tags)
        )