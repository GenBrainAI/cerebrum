"""
Codebase Vector Store for Self-Aware Cerebrum.

This module provides a vector store for codebase files, enabling semantic search
and retrieval of code snippets based on natural language queries. It uses embeddings
to represent code files and supports incremental updates to the vector store as the
codebase evolves.
"""

import os
import re
import json
import time
import uuid
import logging
import asyncio
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from dataclasses import dataclass, field, asdict

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Type for embedding vectors
Embedding = List[float]

@dataclass
class CodeFile:
    """Represents a code file in the vector store."""
    file_path: str
    content: str
    language: str
    last_modified: float
    file_hash: str
    embedding: Optional[Embedding] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, file_path: str, root_dir: str) -> 'CodeFile':
        """Create a CodeFile instance from a file path."""
        abs_path = os.path.join(root_dir, file_path)
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        # Determine language from file extension
        _, ext = os.path.splitext(file_path)
        language = cls._get_language_from_extension(ext)
        
        # Get file stats
        stats = os.stat(abs_path)
        last_modified = stats.st_mtime
        
        # Calculate file hash
        file_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        return cls(
            file_path=file_path,
            content=content,
            language=language,
            last_modified=last_modified,
            file_hash=file_hash
        )
    
    @staticmethod
    def _get_language_from_extension(ext: str) -> str:
        """Map file extension to programming language."""
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.sh': 'bash',
            '.md': 'markdown',
            '.json': 'json',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.toml': 'toml',
            '.sql': 'sql',
        }
        return language_map.get(ext.lower(), 'text')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeFile':
        """Create a CodeFile instance from a dictionary."""
        return cls(**data)

@dataclass
class CodeSnippet:
    """Represents a code snippet with context."""
    file_path: str
    content: str
    start_line: int
    end_line: int
    language: str
    relevance_score: float
    context_before: str = ""
    context_after: str = ""
    
    def to_markdown(self) -> str:
        """Format the snippet as markdown."""
        return f"""
```{self.language} - {self.file_path}:{self.start_line}-{self.end_line}
{self.content}
```

Relevance Score: {self.relevance_score:.4f}
"""

@dataclass
class VectorStoreConfig:
    """Configuration for the CodebaseVectorStore."""
    root_dir: str
    store_dir: str
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimension: int = 1536
    similarity_threshold: float = 0.7
    max_files: int = 10000
    excluded_dirs: List[str] = field(default_factory=lambda: [
        ".git", "node_modules", "venv", "env", "__pycache__", 
        "dist", "build", ".vscode", ".idea"
    ])
    excluded_patterns: List[str] = field(default_factory=lambda: [
        r"\.pyc$", r"\.class$", r"\.o$", r"\.so$", r"\.a$",
        r"\.dll$", r"\.exe$", r"\.bin$", r"\.dat$", r"\.log$"
    ])
    included_extensions: List[str] = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
        ".java", ".c", ".cpp", ".h", ".hpp", ".go", ".rs",
        ".rb", ".php", ".swift", ".kt", ".sh", ".md",
        ".json", ".yml", ".yaml", ".toml", ".sql"
    ])
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorStoreConfig':
        """Create a VectorStoreConfig instance from a dictionary."""
        return cls(**data)

class CodebaseVectorStore:
    """
    Vector store for codebase files, enabling semantic search and retrieval.
    
    This class manages embeddings for code files and provides methods for
    semantic search, incremental updates, and retrieval of relevant code snippets.
    """
    
    def __init__(self, config: VectorStoreConfig):
        """Initialize the vector store with the given configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create store directory if it doesn't exist
        os.makedirs(self.config.store_dir, exist_ok=True)
        
        # Initialize file index and embeddings
        self.files: Dict[str, CodeFile] = {}
        self.embeddings: Dict[str, Embedding] = {}
        self.embedding_matrix: Optional[np.ndarray] = None
        self.file_paths: List[str] = []
        
        # Initialize embedding provider
        self._init_embedding_provider()
        
        # Load existing store if available
        self._load_store()
    
    def _init_embedding_provider(self):
        """Initialize the embedding provider based on configuration."""
        # This is a placeholder for actual embedding provider initialization
        # In a real implementation, this would initialize OpenAI, HuggingFace, or other embedding providers
        self.logger.info(f"Initializing embedding provider: {self.config.embedding_model}")
        
        # For now, we'll use a simple mock embedding function
        self.get_embeddings = self._mock_get_embeddings
    
    def _mock_get_embeddings(self, texts: List[str]) -> List[Embedding]:
        """
        Mock embedding function for testing purposes.
        
        In a real implementation, this would call an actual embedding API.
        """
        # Generate deterministic but unique embeddings based on text content
        embeddings = []
        for text in texts:
            # Create a deterministic seed from the text
            text_hash = hashlib.md5(text.encode('utf-8')).digest()
            seed = int.from_bytes(text_hash[:4], byteorder='little')
            
            # Use the seed to generate a deterministic random embedding
            np.random.seed(seed)
            embedding = np.random.randn(self.config.embedding_dimension).tolist()
            embeddings.append(embedding)
        
        return embeddings
    
    async def _get_embeddings_async(self, texts: List[str]) -> List[Embedding]:
        """Get embeddings asynchronously."""
        # This would be an async call to an embedding API in a real implementation
        return self.get_embeddings(texts)
    
    def _load_store(self):
        """Load the vector store from disk."""
        index_path = os.path.join(self.config.store_dir, "index.json")
        embeddings_path = os.path.join(self.config.store_dir, "embeddings.json")
        
        if os.path.exists(index_path) and os.path.exists(embeddings_path):
            try:
                # Load file index
                with open(index_path, 'r') as f:
                    file_dicts = json.load(f)
                    self.files = {
                        path: CodeFile.from_dict(file_dict)
                        for path, file_dict in file_dicts.items()
                    }
                
                # Load embeddings
                with open(embeddings_path, 'r') as f:
                    self.embeddings = json.load(f)
                
                # Rebuild embedding matrix
                self._rebuild_embedding_matrix()
                
                self.logger.info(f"Loaded vector store with {len(self.files)} files")
            except Exception as e:
                self.logger.error(f"Error loading vector store: {e}")
                # Initialize empty store
                self.files = {}
                self.embeddings = {}
                self.embedding_matrix = None
                self.file_paths = []
        else:
            self.logger.info("No existing vector store found, initializing empty store")
    
    def _save_store(self):
        """Save the vector store to disk."""
        index_path = os.path.join(self.config.store_dir, "index.json")
        embeddings_path = os.path.join(self.config.store_dir, "embeddings.json")
        
        try:
            # Save file index
            with open(index_path, 'w') as f:
                file_dicts = {
                    path: code_file.to_dict()
                    for path, code_file in self.files.items()
                }
                json.dump(file_dicts, f)
            
            # Save embeddings
            with open(embeddings_path, 'w') as f:
                json.dump(self.embeddings, f)
            
            self.logger.info(f"Saved vector store with {len(self.files)} files")
        except Exception as e:
            self.logger.error(f"Error saving vector store: {e}")
    
    def _rebuild_embedding_matrix(self):
        """Rebuild the embedding matrix and file paths list."""
        self.file_paths = list(self.files.keys())
        
        if not self.file_paths:
            self.embedding_matrix = None
            return
        
        # Build embedding matrix
        embeddings_list = [self.embeddings.get(path, [0] * self.config.embedding_dimension) 
                          for path in self.file_paths]
        self.embedding_matrix = np.array(embeddings_list)
    
    def _should_include_file(self, file_path: str) -> bool:
        """Check if a file should be included in the vector store."""
        # Check if the file is in an excluded directory
        for excluded_dir in self.config.excluded_dirs:
            if f"/{excluded_dir}/" in f"/{file_path}/" or file_path.startswith(f"{excluded_dir}/"):
                return False
        
        # Check if the file matches an excluded pattern
        for pattern in self.config.excluded_patterns:
            if re.search(pattern, file_path):
                return False
        
        # Check if the file has an included extension
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in self.config.included_extensions:
            return False
        
        return True
    
    async def index_codebase(self, incremental: bool = True) -> Dict[str, Any]:
        """
        Index the codebase and update the vector store.
        
        Args:
            incremental: If True, only update files that have changed.
        
        Returns:
            A dictionary with statistics about the indexing operation.
        """
        start_time = time.time()
        stats = {
            "total_files": 0,
            "indexed_files": 0,
            "skipped_files": 0,
            "unchanged_files": 0,
            "errors": 0,
            "time_taken": 0
        }
        
        # Get all files in the codebase
        all_files = []
        for root, _, files in os.walk(self.config.root_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, self.config.root_dir)
                
                # Convert Windows paths to Unix-style
                rel_path = rel_path.replace("\\", "/")
                
                if self._should_include_file(rel_path):
                    all_files.append(rel_path)
                else:
                    stats["skipped_files"] += 1
        
        stats["total_files"] = len(all_files) + stats["skipped_files"]
        
        # Limit the number of files to index
        if len(all_files) > self.config.max_files:
            self.logger.warning(f"Too many files to index ({len(all_files)}), limiting to {self.config.max_files}")
            all_files = all_files[:self.config.max_files]
        
        # Find files to update
        files_to_update = []
        for file_path in all_files:
            try:
                abs_path = os.path.join(self.config.root_dir, file_path)
                
                # Skip if file doesn't exist
                if not os.path.exists(abs_path):
                    continue
                
                # Check if file has changed
                stats_result = os.stat(abs_path)
                last_modified = stats_result.st_mtime
                
                if incremental and file_path in self.files:
                    # Skip if file hasn't changed
                    if last_modified <= self.files[file_path].last_modified:
                        stats["unchanged_files"] += 1
                        continue
                
                files_to_update.append(file_path)
            except Exception as e:
                self.logger.error(f"Error checking file {file_path}: {e}")
                stats["errors"] += 1
        
        # Remove files that no longer exist
        files_to_remove = [path for path in self.files if path not in all_files]
        for file_path in files_to_remove:
            del self.files[file_path]
            if file_path in self.embeddings:
                del self.embeddings[file_path]
        
        # Update files in batches
        batch_size = 10  # Process 10 files at a time
        for i in range(0, len(files_to_update), batch_size):
            batch = files_to_update[i:i+batch_size]
            await self._update_files_batch(batch)
            stats["indexed_files"] += len(batch)
        
        # Rebuild embedding matrix
        self._rebuild_embedding_matrix()
        
        # Save the updated store
        self._save_store()
        
        # Update stats
        stats["time_taken"] = time.time() - start_time
        
        return stats
    
    async def _update_files_batch(self, file_paths: List[str]):
        """Update a batch of files in the vector store."""
        code_files = []
        texts = []
        
        # Load files and prepare texts for embedding
        for file_path in file_paths:
            try:
                code_file = CodeFile.from_file(file_path, self.config.root_dir)
                code_files.append(code_file)
                texts.append(code_file.content)
            except Exception as e:
                self.logger.error(f"Error loading file {file_path}: {e}")
        
        # Get embeddings for all texts
        if texts:
            embeddings = await self._get_embeddings_async(texts)
            
            # Update files and embeddings
            for code_file, embedding in zip(code_files, embeddings):
                code_file.embedding = embedding
                self.files[code_file.file_path] = code_file
                self.embeddings[code_file.file_path] = embedding
    
    async def search(self, query: str, top_k: int = 5) -> List[CodeSnippet]:
        """
        Search the codebase for relevant code snippets.
        
        Args:
            query: The search query.
            top_k: The number of results to return.
        
        Returns:
            A list of CodeSnippet objects.
        """
        if self.embedding_matrix is None:
            return []
        
        # Get query embedding
        query_embedding = await self._get_embeddings_async([query])
        query_vector = np.array(query_embedding[0]).reshape(1, -1)
        
        # Calculate similarities
        # Ensure embedding_matrix is a numpy array
        if not isinstance(self.embedding_matrix, np.ndarray):
            self.embedding_matrix = np.array(self.embedding_matrix)
            
        similarities = cosine_similarity(query_vector, self.embedding_matrix)[0]
        
        # Get top-k results
        if len(similarities) <= top_k:
            top_indices = np.argsort(similarities)[::-1]
        else:
            top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Filter by similarity threshold - use absolute value for comparison
        # This ensures that even with negative similarity scores, we still get results
        # as long as they are "similar enough" in either direction
        top_indices = [i for i in top_indices if abs(similarities[i]) >= self.config.similarity_threshold]
        
        # Create snippets
        snippets = []
        for idx in top_indices:
            file_path = self.file_paths[idx]
            code_file = self.files[file_path]
            
            # Extract relevant snippet
            snippet = self._extract_snippet(code_file, query, similarities[idx])
            snippets.append(snippet)
        
        return snippets
    
    def _extract_snippet(self, code_file: CodeFile, query: str, score: float) -> CodeSnippet:
        """Extract a relevant snippet from a code file."""
        lines = code_file.content.split('\n')
        
        # For simplicity, we'll just return the first chunk of the file
        # In a real implementation, this would use more sophisticated chunking and relevance scoring
        start_line = 0
        end_line = min(20, len(lines))
        
        content = '\n'.join(lines[start_line:end_line])
        
        return CodeSnippet(
            file_path=code_file.file_path,
            content=content,
            start_line=start_line + 1,  # 1-indexed
            end_line=end_line,
            language=code_file.language,
            relevance_score=score
        )
    
    def get_file_content(self, file_path: str) -> Optional[str]:
        """Get the content of a file in the vector store."""
        if file_path in self.files:
            return self.files[file_path].content
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        languages = {}
        total_size = 0
        
        for file in self.files.values():
            languages[file.language] = languages.get(file.language, 0) + 1
            total_size += len(file.content)
        
        return {
            "total_files": len(self.files),
            "languages": languages,
            "total_size_bytes": total_size,
            "embedding_model": self.config.embedding_model,
            "embedding_dimension": self.config.embedding_dimension,
            "store_dir": self.config.store_dir,
            "root_dir": self.config.root_dir
        }
    
    async def refresh(self) -> Dict[str, Any]:
        """Refresh the vector store with the latest codebase changes."""
        return await self.index_codebase(incremental=True)
    
    def clear(self) -> None:
        """Clear the vector store."""
        self.files = {}
        self.embeddings = {}
        self.embedding_matrix = None
        self.file_paths = []
        self._save_store()
    
    async def add_file(self, file_path: str) -> bool:
        """
        Add a single file to the vector store.
        
        Args:
            file_path: The path to the file, relative to the root directory.
        
        Returns:
            True if the file was added successfully, False otherwise.
        """
        try:
            if not self._should_include_file(file_path):
                return False
            
            code_file = CodeFile.from_file(file_path, self.config.root_dir)
            embedding = await self._get_embeddings_async([code_file.content])
            
            code_file.embedding = embedding[0]
            self.files[file_path] = code_file
            self.embeddings[file_path] = embedding[0]
            
            # Rebuild embedding matrix
            self._rebuild_embedding_matrix()
            
            # Save the updated store
            self._save_store()
            
            return True
        except Exception as e:
            self.logger.error(f"Error adding file {file_path}: {e}")
            return False
    
    def remove_file(self, file_path: str) -> bool:
        """
        Remove a file from the vector store.
        
        Args:
            file_path: The path to the file, relative to the root directory.
        
        Returns:
            True if the file was removed successfully, False otherwise.
        """
        if file_path in self.files:
            del self.files[file_path]
            
            if file_path in self.embeddings:
                del self.embeddings[file_path]
            
            # Rebuild embedding matrix
            self._rebuild_embedding_matrix()
            
            # Save the updated store
            self._save_store()
            
            return True
        
        return False 