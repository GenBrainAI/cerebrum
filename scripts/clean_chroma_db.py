#!/usr/bin/env python3
"""
Script to clean ChromaDB data and recreate directory structure.
This will delete all ChromaDB data and recreate the necessary directories.
"""

import os
import shutil
from pathlib import Path
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def clean_chroma_db():
    """Clean ChromaDB data and recreate directory structure."""
    # Define the path to the ChromaDB directory
    chroma_db_path = Path("persistent_state/chroma_db")
    
    # Check if the directory exists
    if not chroma_db_path.exists():
        logger.info(f"ChromaDB directory does not exist at {chroma_db_path}")
        # Create the directory
        chroma_db_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created empty ChromaDB directory at {chroma_db_path}")
        return
    
    # Backup the directory (optional)
    backup_path = Path("persistent_state/chroma_db_backup")
    if backup_path.exists():
        shutil.rmtree(backup_path)
    
    try:
        logger.info(f"Creating backup of ChromaDB at {backup_path}")
        shutil.copytree(chroma_db_path, backup_path)
        logger.info("Backup created successfully")
    except Exception as e:
        logger.warning(f"Failed to create backup: {str(e)}")
        response = input("Continue without backup? (y/n): ")
        if response.lower() != 'y':
            logger.info("Operation cancelled")
            return
    
    # Delete the ChromaDB directory
    try:
        logger.info(f"Deleting ChromaDB directory at {chroma_db_path}")
        shutil.rmtree(chroma_db_path)
        logger.info("ChromaDB directory deleted successfully")
    except Exception as e:
        logger.error(f"Failed to delete ChromaDB directory: {str(e)}")
        return
    
    # Recreate the directory
    try:
        logger.info(f"Recreating empty ChromaDB directory at {chroma_db_path}")
        chroma_db_path.mkdir(parents=True, exist_ok=True)
        logger.info("Empty ChromaDB directory created successfully")
    except Exception as e:
        logger.error(f"Failed to recreate ChromaDB directory: {str(e)}")
        return
    
    logger.info("ChromaDB cleanup completed successfully")

if __name__ == "__main__":
    clean_chroma_db() 