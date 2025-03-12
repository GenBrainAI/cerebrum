#!/usr/bin/env python3
"""
Script to fix vector store index loading issues.
This script patches the VectorStore class to properly load all indices.
"""

import os
import sys
from pathlib import Path
import logging
import importlib
import inspect
import types
from typing import List, Dict, Any, Optional

# Add project root to Python path
project_root = str(Path(__file__).parents[1])
if project_root not in sys.path:
    sys.path.append(project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def patch_vector_store():
    """Patch the VectorStore class to fix index loading issues."""
    try:
        # Import the VectorStore class
        from src.server.context.vector_store import VectorStore
        
        # Define the patched methods
        def patched_load_existing_indices(self):
            """Patched method to load existing collections from ChromaDB."""
            try:
                # Get all collections
                all_collections = self.client.list_collections()
                collection_names = [c.name for c in all_collections]
                logger.info(f"Found {len(collection_names)} collections in ChromaDB: {collection_names}")
                
                # Load all collections, not just vs_ prefixed ones
                for collection in all_collections:
                    try:
                        self.indices[collection.name] = self.client.get_collection(
                            name=collection.name,
                            embedding_function=self.embedding_function
                        )
                        logger.info(f"Loaded collection: {collection.name}")
                    except Exception as e:
                        logger.error(f"Error loading collection {collection.name}: {str(e)}")
                
                logger.info(f"Loaded {len(self.indices)} vector indices")
            except Exception as e:
                logger.error(f"Error loading existing collections: {str(e)}")
        
        def patched_reload_indices(self):
            """Patched method to reload all indices from ChromaDB."""
            try:
                self.indices.clear()  # Clear existing indices
                collections = self.client.list_collections()
                logger.info(f"Found {len(collections)} collections in ChromaDB: {[c.name for c in collections]}")
                
                # Load all collections, not just vs_ prefixed ones
                for collection in collections:
                    try:
                        self.indices[collection.name] = self.client.get_collection(
                            name=collection.name,
                            embedding_function=self.embedding_function
                        )
                        logger.info(f"Reloaded collection: {collection.name}")
                    except Exception as e:
                        logger.error(f"Error loading collection {collection.name}: {str(e)}")
                
                logger.info(f"Reloaded {len(self.indices)} vector indices")
            except Exception as e:
                logger.error(f"Error reloading indices: {str(e)}")
        
        # Apply the patches
        VectorStore._load_existing_indices = patched_load_existing_indices
        VectorStore._reload_indices = patched_reload_indices
        
        logger.info("Successfully patched VectorStore class")
        return True
    except Exception as e:
        logger.error(f"Failed to patch VectorStore class: {str(e)}")
        return False

def check_vector_store():
    """Check the current state of the vector store."""
    try:
        # Import the VectorStore class
        from src.server.context.vector_store import VectorStore
        
        # Create a VectorStore instance
        vector_store = VectorStore()
        
        # Get all collections from ChromaDB
        collections = vector_store.client.list_collections()
        logger.info(f"Found {len(collections)} collections in ChromaDB: {[c.name for c in collections]}")
        
        # Get all indices from VectorStore
        logger.info(f"Found {len(vector_store.indices)} indices in VectorStore: {list(vector_store.indices.keys())}")
        
        # Check for mismatches
        chroma_collections = set(c.name for c in collections)
        vector_indices = set(vector_store.indices.keys())
        
        missing_indices = chroma_collections - vector_indices
        if missing_indices:
            logger.warning(f"Found {len(missing_indices)} collections in ChromaDB that are not loaded in VectorStore: {missing_indices}")
        
        extra_indices = vector_indices - chroma_collections
        if extra_indices:
            logger.warning(f"Found {len(extra_indices)} indices in VectorStore that don't exist in ChromaDB: {extra_indices}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to check vector store: {str(e)}")
        return False

if __name__ == "__main__":
    # Check the current state
    logger.info("Checking current vector store state...")
    check_vector_store()
    
    # Apply the patch
    logger.info("Applying patch to VectorStore class...")
    if patch_vector_store():
        # Check the state after patching
        logger.info("Checking vector store state after patching...")
        check_vector_store()
    else:
        logger.error("Failed to apply patch") 