from typing import Dict, List, Optional, Union
from pathlib import Path
import json
import asyncio
from datetime import datetime
import io

from src.server.models.scraping_session import ScrapingSession, ScrapingTargetType, ScrapingContentType
from src.server.context.knowledge_base import KnowledgeBase
from src.server.context.chroma_vector_store import ChromaVectorStore
from src.server.context.code_catalog import CodeCatalog
from src.server.tools.web_scraper_tool import WebScraperTool
from src.server.tools.repo_scraper import RepoScraper

class ScrapingSessionManager:
    """Manager for scraping sessions and their data distribution."""
    
    def __init__(self, base_path: str = "persistent_state/context/scraping_sessions"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, ScrapingSession] = {}
        self.knowledge_base = KnowledgeBase()
        self.vector_store = ChromaVectorStore(base_path="persistent_state/context/chroma_db")
        self.code_catalog = CodeCatalog()
        self._load_sessions()
        
    def _load_sessions(self) -> None:
        """Load existing sessions from disk."""
        try:
            sessions_file = self.base_path / "sessions.json"
            if sessions_file.exists():
                with open(sessions_file, 'r') as f:
                    data = json.load(f)
                    for session_data in data.values():
                        session = ScrapingSession.from_dict(session_data)
                        self.sessions[session.id] = session
        except Exception as e:
            print(f"Error loading sessions: {str(e)}")
            
    def _save_sessions(self) -> None:
        """Save sessions to disk."""
        try:
            sessions_file = self.base_path / "sessions.json"
            with open(sessions_file, 'w') as f:
                json.dump(
                    {id: session.to_dict() for id, session in self.sessions.items()},
                    f,
                    indent=2
                )
        except Exception as e:
            print(f"Error saving sessions: {str(e)}")
            
    def create_session(
        self,
        name: str,
        description: Optional[str] = None,
        target_type: Union[str, ScrapingTargetType] = ScrapingTargetType.KNOWLEDGE_BASE,
        content_type: Union[str, ScrapingContentType] = ScrapingContentType.WEB,
        metadata: Optional[Dict] = None
    ) -> ScrapingSession:
        """Create a new scraping session."""
        if isinstance(target_type, str):
            target_type = ScrapingTargetType(target_type)
        if isinstance(content_type, str):
            content_type = ScrapingContentType(content_type)
            
        session = ScrapingSession(
            name=name,
            description=description,
            target_type=target_type,
            content_type=content_type,
            metadata=metadata
        )
        self.sessions[session.id] = session
        self._save_sessions()
        return session
        
    def get_session(self, session_id: str) -> Optional[ScrapingSession]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
        
    def list_sessions(
        self,
        target_type: Optional[Union[str, ScrapingTargetType]] = None,
        content_type: Optional[Union[str, ScrapingContentType]] = None,
        status: Optional[str] = None
    ) -> List[ScrapingSession]:
        """List sessions with optional filters."""
        sessions = list(self.sessions.values())
        
        if target_type:
            if isinstance(target_type, str):
                target_type = ScrapingTargetType(target_type)
            sessions = [s for s in sessions if s.target_type == target_type]
            
        if content_type:
            if isinstance(content_type, str):
                content_type = ScrapingContentType(content_type)
            sessions = [s for s in sessions if s.content_type == content_type]
            
        if status:
            sessions = [s for s in sessions if s.status == status]
            
        return sorted(sessions, key=lambda x: x.created_at, reverse=True)
        
    async def process_entry(self, session_id: str, entry: Dict[str, any]) -> None:
        """Process a scraped entry according to the session configuration."""
        try:
            session = self.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            # Add entry to session
            session.entries.append(entry)

            # Process entry based on target type
            if session.target_type == ScrapingTargetType.KNOWLEDGE_BASE:
                # Add to knowledge base
                await self.knowledge_base.add_knowledge(
                    content=entry["content"],
                    domain=session.name,
                    metadata=entry["metadata"]
                )
            elif session.target_type == ScrapingTargetType.VECTOR_STORE:
                # Add to vector store
                config = session.target_config or {}
                index_name = config["index_name"] or self._sanitize_index_name(session.name)
                
                # Add to vector store using add_file_to_index
                await self.vector_store.add_file_to_index(
                    index_name=index_name,
                    file_path_or_obj=io.StringIO(entry["content"]),
                    metadata=entry["metadata"]
                )
            elif session.target_type == ScrapingTargetType.CODE:
                # Add to code catalog
                await self.code_catalog.index_directory(
                    directory_path=entry["path"],
                    analyze_deps=True,
                    parse_docs=True
                )

            # Save session
            self._save_sessions()

        except Exception as e:
            print(f"Error processing entry: {str(e)}")
            import traceback
            print(f"Stack trace: {traceback.format_exc()}")
            raise
            
    def _sanitize_index_name(self, name: str) -> str:
        """Sanitize name for use as vector store index name."""
        # Replace spaces and special characters with underscores
        sanitized = ''.join(c if c.isalnum() else '_' for c in name)
        # Ensure it starts with a letter
        if not sanitized[0].isalpha():
            sanitized = 'idx_' + sanitized
        # Ensure length is between 3-63 characters
        if len(sanitized) < 3:
            sanitized = sanitized + '_index'
        elif len(sanitized) > 63:
            sanitized = sanitized[:60] + '_idx'
        return sanitized
        
    async def delete_session(self, session_id: str, delete_content: bool = False) -> bool:
        """Delete a session and optionally its content."""
        session = self.sessions.get(session_id)
        if not session:
            return False
            
        if delete_content:
            # Delete content from each target
            for target_type, config in session.target_configs.items():
                if not config["enabled"]:
                    continue
                    
                if target_type == ScrapingTargetType.KNOWLEDGE_BASE:
                    # Delete from knowledge base
                    for entry in session.entries:
                        try:
                            await self.knowledge_base.delete_knowledge(entry["id"])
                        except Exception as e:
                            print(f"Error deleting knowledge entry: {str(e)}")
                            
                elif target_type == ScrapingTargetType.VECTOR_STORE:
                    # Delete from vector store
                    index_name = config["index_name"] or self._sanitize_index_name(session.name)
                    try:
                        await self.vector_store.delete_index(index_name)
                    except Exception as e:
                        print(f"Error deleting vector store index: {str(e)}")
                        
                elif target_type == ScrapingTargetType.CODE:
                    # Delete from code catalog
                    for entry in session.entries:
                        if "code_blocks" in entry:
                            for code_block in entry["code_blocks"]:
                                try:
                                    path = f"{session.name}/{entry['metadata'].get('title', 'untitled')}.{code_block['language']}"
                                    self.code_catalog.remove_file(path)
                                except Exception as e:
                                    print(f"Error deleting code file: {str(e)}")
                                    
        # Delete session
        del self.sessions[session_id]
        self._save_sessions()
        return True 