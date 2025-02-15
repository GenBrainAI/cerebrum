#!/usr/bin/env python3

import shutil
from pathlib import Path
import chromadb
import logging
import sys
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_project_root() -> Path:
    """Get the absolute path to the project root."""
    script_path = Path(__file__).resolve()
    return script_path.parent.parent

def clean_directory(path: Path) -> None:
    """Clean a directory while preserving the directory structure."""
    if not path.exists():
        logger.info(f"Directory does not exist: {path}")
        return

    try:
        # Remove everything in the directory but keep the directory itself
        if path.exists():
            for item in path.iterdir():
                if item.is_file():
                    item.unlink()
                    logger.info(f"Removed file: {item}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    logger.info(f"Removed directory: {item}")
            logger.info(f"Cleaned directory: {path}")
    except Exception as e:
        logger.error(f"Error cleaning directory {path}: {e}")

def clean_vector_store(base_path: Path) -> None:
    """Clean vector store data."""
    vector_store_path = base_path / "persistent_state/context/vector_store"
    context_db_path = base_path / "context_db"
    
    try:
        # Clean ChromaDB
        if context_db_path.exists():
            client = chromadb.PersistentClient(path=str(context_db_path))
            collections = client.list_collections()
            for collection in collections:
                client.delete_collection(collection.name)
                logger.info(f"Deleted collection: {collection.name}")
            
            # Remove ChromaDB files
            shutil.rmtree(context_db_path)
            logger.info("Removed ChromaDB directory")
    except Exception as e:
        logger.error(f"Error cleaning ChromaDB: {e}")

    # Clean vector store directory
    clean_directory(vector_store_path)

def clean_knowledge_base(base_path: Path) -> None:
    """Clean knowledge base data."""
    kb_paths = [
        base_path / "persistent_state/knowledge_base",
        base_path / "persistent_state/global_knowledge_base"
    ]
    
    for path in kb_paths:
        clean_directory(path)

def clean_code_catalog(base_path: Path) -> None:
    """Clean code catalog data."""
    code_catalog_path = base_path / "persistent_state/context/code_catalog"
    clean_directory(code_catalog_path)

def main():
    try:
        project_root = get_project_root()
        logger.info(f"Project root: {project_root}")
        
        # Confirm with user
        response = input("This will remove all context data (but preserve states). Are you sure? (y/N): ")
        if response.lower() != 'y':
            logger.info("Operation cancelled")
            return
        
        # Clean each component
        logger.info("Starting cleanup...")
        
        clean_vector_store(project_root)
        logger.info("Vector store cleaned")
        
        clean_knowledge_base(project_root)
        logger.info("Knowledge base cleaned")
        
        clean_code_catalog(project_root)
        logger.info("Code catalog cleaned")
        
        logger.info("Cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
