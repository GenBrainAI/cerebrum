#!/usr/bin/env python3
"""
Script to fix ChromaDB collection issues by removing references to invalid collections.
"""

import os
import sys
from pathlib import Path
import logging
import shutil
import json
import chromadb

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

def backup_chromadb():
    """Create a backup of the current ChromaDB directory."""
    try:
        base_path = os.path.join(project_root, "persistent_state", "chroma_db")
        backup_path = os.path.join(project_root, "persistent_state", f"chroma_db_backup_{int(time.time())}")
        
        if os.path.exists(base_path):
            logger.info(f"Creating backup of ChromaDB directory: {backup_path}")
            shutil.copytree(base_path, backup_path)
            logger.info(f"Backup created successfully")
            return backup_path
        else:
            logger.warning(f"ChromaDB directory not found at {base_path}")
            return None
    except Exception as e:
        logger.error(f"Failed to create backup: {str(e)}")
        return None

def fix_chroma_collections():
    """Fix ChromaDB collection issues by identifying and removing invalid collections."""
    try:
        # Initialize ChromaDB client
        base_path = os.path.join(project_root, "persistent_state", "chroma_db")
        if not os.path.exists(base_path):
            logger.error(f"ChromaDB directory not found at {base_path}")
            return False
        
        client = chromadb.PersistentClient(
            path=base_path,
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # List all collections
        all_collections = client.list_collections()
        collection_names = [c.name for c in all_collections]
        logger.info(f"Found {len(collection_names)} collections in ChromaDB: {collection_names}")
        
        # Check each collection
        valid_collections = []
        invalid_collections = []
        
        for collection in all_collections:
            try:
                # Try a simple operation to check if the collection is valid
                count = collection.count()
                logger.info(f"Collection {collection.name} is valid and contains {count} documents")
                valid_collections.append(collection.name)
            except Exception as e:
                logger.error(f"Invalid collection {collection.name}: {str(e)}")
                invalid_collections.append(collection.name)
        
        logger.info(f"Found {len(valid_collections)} valid collections and {len(invalid_collections)} invalid collections")
        
        # Remove invalid collections from the collection tracker file
        tracker_file = os.path.join(base_path, "chroma.sqlite3")
        if os.path.exists(tracker_file):
            logger.info(f"Fixing SQLite database: {tracker_file}")
            
            import sqlite3
            conn = sqlite3.connect(tracker_file)
            cursor = conn.cursor()
            
            # List all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            logger.info(f"Found tables in SQLite database: {tables}")
            
            # Check Collections table
            try:
                cursor.execute("SELECT id, name FROM Collections;")
                collections_db = cursor.fetchall()
                logger.info(f"Found {len(collections_db)} collections in database")
                
                # Remove invalid collections
                for collection_id, name in collections_db:
                    if name in invalid_collections:
                        logger.info(f"Removing invalid collection from database: {name} (ID: {collection_id})")
                        cursor.execute("DELETE FROM Collections WHERE id = ?", (collection_id,))
                        # Also try to remove from Embeddings and Metadata tables
                        try:
                            cursor.execute("DELETE FROM Embeddings WHERE collection_id = ?", (collection_id,))
                            cursor.execute("DELETE FROM Metadata WHERE collection_id = ?", (collection_id,))
                        except Exception as e:
                            logger.warning(f"Error cleaning up related tables for collection {name}: {str(e)}")
                
                conn.commit()
                logger.info(f"Database cleanup completed")
            except Exception as e:
                logger.error(f"Error accessing Collections table: {str(e)}")
            
            conn.close()
        
        # Force reload the client
        client = chromadb.PersistentClient(
            path=base_path,
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Verify fix
        all_collections = client.list_collections()
        collection_names = [c.name for c in all_collections]
        logger.info(f"After fix: Found {len(collection_names)} collections in ChromaDB: {collection_names}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to fix ChromaDB collections: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    import time
    
    # Backup first
    backup_path = backup_chromadb()
    
    # Fix collections
    logger.info("Fixing ChromaDB collections...")
    if fix_chroma_collections():
        logger.info("Successfully fixed ChromaDB collections")
    else:
        logger.error("Failed to fix ChromaDB collections") 