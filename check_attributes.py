#!/usr/bin/env python
import os
import sys
import logging
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Import necessary modules
from src.server.persistence.persistence_model_factory import PersistenceModelFactory
from src.server.tools.tools_catalog import ToolsCatalog

def check_persistence_model():
    """Print out all attributes of the persistence model."""
    try:
        # Initialize the tools catalog (required for some operations)
        tools_catalog = ToolsCatalog()  # Get singleton instance
        # No need to call initialize_default_tools as it's called in __init__
        
        # Initialize persistence model
        persistence_model = PersistenceModelFactory().persistence_model()
        
        # Print all attributes
        logging.info(f"All attributes of persistence model: {dir(persistence_model)}")
        
        # Print more detailed information about CRUD handlers
        for attr in dir(persistence_model):
            if not attr.startswith("_"):  # Skip private attributes
                try:
                    value = getattr(persistence_model, attr)
                    if hasattr(value, "list") and callable(value.list):
                        logging.info(f"CRUD handler: {attr}")
                        logging.info(f"  Methods: {[m for m in dir(value) if not m.startswith('_')]}")
                except Exception as e:
                    logging.warning(f"Error accessing {attr}: {str(e)}")
        
        return True
    except Exception as e:
        logging.error(f"Error checking persistence model: {str(e)}")
        return False

if __name__ == "__main__":
    check_persistence_model() 