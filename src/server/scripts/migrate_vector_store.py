#!/usr/bin/env python3
"""
Migration script to move data from the old vector store implementation to the new ChromaDB implementation.

This script:
1. Identifies all data in the old vector store location
2. Migrates it to the new ChromaDB location
3. Verifies the migration was successful
"""

import os
import sys
import json
import shutil
import asyncio
from pathlib import Path
import logging
from tqdm import tqdm
import argparse

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parents[3]))

from src.server.context.vector_store import VectorStore
from src.server.context.context_database import ContextDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
OLD_VECTOR_STORE_PATH = "persistent_state/context/vector_store"
NEW_CHROMA_DB_PATH = "persistent_state/chroma_db"
BACKUP_PATH = "persistent_state/vector_store_backup"

async def migrate_vector_store():
    """Migrate data from old vector store to new ChromaDB implementation."""
    logger.info("Starting vector store migration")
    
    # Check if old vector store exists
    old_path = Path(OLD_VECTOR_STORE_PATH)
    if not old_path.exists():
        logger.info(f"Old vector store path {OLD_VECTOR_STORE_PATH} does not exist. Nothing to migrate.")
        return
    
    # Create backup of old vector store
    backup_path = Path(BACKUP_PATH)
    if backup_path.exists():
        logger.info(f"Backup path {BACKUP_PATH} already exists. Removing...")
        shutil.rmtree(backup_path)
    
    logger.info(f"Creating backup of old vector store at {BACKUP_PATH}")
    shutil.copytree(old_path, backup_path)
    logger.info("Backup created successfully")
    
    # Initialize new vector store
    new_vector_store = VectorStore(base_path=NEW_CHROMA_DB_PATH)
    context_db = ContextDatabase(persist_directory=NEW_CHROMA_DB_PATH)
    
    # Find all metadata files in the old vector store
    metadata_dir = old_path / "metadata"
    if not metadata_dir.exists():
        logger.warning(f"Metadata directory {metadata_dir} does not exist. No data to migrate.")
        return
    
    metadata_files = list(metadata_dir.glob("*.json"))
    logger.info(f"Found {len(metadata_files)} metadata files to migrate")
    
    # Process each metadata file
    migrated_count = 0
    failed_count = 0
    
    for metadata_file in tqdm(metadata_files, desc="Migrating files"):
        try:
            # Load metadata
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Extract content and other metadata
            content = metadata.pop('content', '')
            if not content:
                logger.warning(f"No content found in {metadata_file}. Skipping...")
                failed_count += 1
                continue
            
            # Generate embedding
            embeddings = await context_db._safe_embed([content])
            if not embeddings:
                logger.warning(f"Failed to generate embedding for {metadata_file}. Skipping...")
                failed_count += 1
                continue
            
            # Determine index name
            index_name = metadata.get('index_name', 'default')
            if not index_name.startswith('vs_'):
                index_name = f"vs_{index_name}"
            
            # Ensure index exists
            await new_vector_store.create_index(index_name, description=f"Migrated index for {index_name}")
            
            # Add to new vector store
            file_id = metadata_file.stem
            collection = new_vector_store._ensure_collection(index_name)
            collection.add(
                ids=[file_id],
                documents=[content],
                metadatas=[metadata],
                embeddings=[embeddings[0]]
            )
            
            migrated_count += 1
            
        except Exception as e:
            logger.error(f"Error migrating {metadata_file}: {str(e)}")
            failed_count += 1
    
    logger.info(f"Migration completed: {migrated_count} files migrated, {failed_count} files failed")
    
    # Verify migration
    indices = await new_vector_store.list_indices()
    total_documents = sum(idx['count'] for idx in indices)
    logger.info(f"New vector store contains {len(indices)} indices with {total_documents} total documents")
    
    if migrated_count > 0 and total_documents > 0:
        logger.info("Migration successful!")
        
        # Ask if user wants to delete the old vector store
        if input("Do you want to delete the old vector store? (yes/no): ").lower() == 'yes':
            logger.info(f"Deleting old vector store at {OLD_VECTOR_STORE_PATH}")
            shutil.rmtree(old_path)
            logger.info("Old vector store deleted")
        else:
            logger.info("Old vector store preserved")
    else:
        logger.warning("Migration may have failed. Please check the logs.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate vector store data to ChromaDB")
    parser.add_argument("--force", action="store_true", help="Force migration even if target directory exists")
    args = parser.parse_args()
    
    # Check if new ChromaDB path already has data
    new_path = Path(NEW_CHROMA_DB_PATH)
    if new_path.exists() and any(new_path.iterdir()) and not args.force:
        logger.warning(f"Target directory {NEW_CHROMA_DB_PATH} already contains data.")
        logger.warning("Use --force to override and continue with migration.")
        sys.exit(1)
    
    # Create target directory if it doesn't exist
    os.makedirs(NEW_CHROMA_DB_PATH, exist_ok=True)
    
    # Run migration
    asyncio.run(migrate_vector_store()) 