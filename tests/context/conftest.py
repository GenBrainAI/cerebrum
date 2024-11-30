import pytest
import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from src.server.context.vector_store import VectorStore, VectorStoreConfig
from src.server.context.knowledge_base import KnowledgeBase

@pytest.fixture(scope="function")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def vector_store_config(temp_dir):
    """Fixture for VectorStore configuration."""
    return VectorStoreConfig(
        persist_directory=os.path.join(temp_dir, "vector_store"),
        collection_name="test_collection",
        embedding_model="text-embedding-3-small",
        batch_size=10,
        max_retries=2,
        retry_delay=1,
        connection_timeout=5,
        max_concurrent_requests=2,
        metadata_schema={
            "file_path": str,
            "type": str,
            "tags": list
        }
    )

@pytest.fixture
def vector_store(vector_store_config):
    """Fixture for VectorStore instance with cleanup."""
    store = VectorStore(vector_store_config)
    return store

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def knowledge_base(temp_dir):
    """Fixture for KnowledgeBase instance with cleanup."""
    kb = KnowledgeBase(temp_dir)
    return kb  # Cleanup happens via temp_dir fixture

@pytest.fixture
def sample_code_content():
    """Sample code content for testing."""
    return {
        "test.py": """
def example_function():
    \"\"\"Example function for testing.\"\"\"
    return True

class ExampleClass:
    def method(self):
        pass
""",
        "utils.py": """
import os
from datetime import datetime

def utility_function():
    \"\"\"Utility function for testing.\"\"\"
    pass
"""
    }

@pytest.fixture
def sample_domain_knowledge():
    """Sample domain knowledge entries for testing."""
    return [
        {
            "content": "Python is a high-level programming language.",
            "domain": "programming",
            "metadata": {
                "tags": ["python", "language"],
                "type": "definition"
            }
        },
        {
            "content": "Vector stores are used for semantic search.",
            "domain": "databases",
            "metadata": {
                "tags": ["vector-db", "search"],
                "type": "concept"
            }
        }
    ]

@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "file_path": "test.py",
        "type": "code",
        "tags": ["python", "test"],
        "created_at": datetime.now().isoformat()
    }

# Context-specific fixtures
@pytest.fixture
def context_query():
    """Sample context query for testing."""
    return {
        "query": "python function example",
        "filters": {"type": "code"},
        "limit": 5
    }