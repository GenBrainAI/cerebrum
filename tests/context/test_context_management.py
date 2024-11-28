# import pytest
# import os
# import tempfile
# import shutil
# from pathlib import Path
# import asyncio

# from src.server.context.context_management import ContextDatabase, CodeCatalog

# @pytest.fixture
# def temp_dir():
#     """Create a temporary directory for test files."""
#     temp_dir = tempfile.mkdtemp()
#     yield temp_dir
#     shutil.rmtree(temp_dir)

# @pytest.fixture
# def sample_code_files(temp_dir):
#     """Create sample Python files for testing."""
#     # Create a simple Python file
#     file1_path = os.path.join(temp_dir, "test1.py")
#     with open(file1_path, "w") as f:
#         f.write("""
# class TestClass:
#     def test_method(self):
#         pass

# def test_function():
#     return True
# """)

#     # Create another Python file with imports
#     file2_path = os.path.join(temp_dir, "test2.py")
#     with open(file2_path, "w") as f:
#         f.write("""
# import os
# from datetime import datetime

# def another_function():
#     pass
# """)

#     return temp_dir

# @pytest.fixture
# def context_db():
#     """Create a ContextDatabase instance for testing."""
#     db_path = tempfile.mkdtemp()
#     db = ContextDatabase(persist_directory=db_path)
#     yield db
#     shutil.rmtree(db_path)

# @pytest.fixture
# def code_catalog():
#     """Create a CodeCatalog instance for testing."""
#     return CodeCatalog()

# @pytest.mark.asyncio
# async def test_code_catalog_indexing(code_catalog, sample_code_files):
#     """Test the code catalog's ability to index and analyze Python files."""
#     await code_catalog.index_directory(sample_code_files)
    
#     # Check file indexing
#     test1_path = os.path.join(sample_code_files, "test1.py")
#     file_info = code_catalog.get_file_info(test1_path)
    
#     assert file_info is not None, "Should have indexed test1.py"
#     assert "TestClass" in file_info["classes"], "Should find TestClass"
#     assert "test_function" in file_info["functions"], "Should find test_function"
    
#     # Check imports detection
#     test2_path = os.path.join(sample_code_files, "test2.py")
#     file_info = code_catalog.get_file_info(test2_path)
    
#     assert file_info is not None, "Should have indexed test2.py"
#     assert any("import os" in imp for imp in file_info["imports"]), "Should detect os import"
#     assert any("datetime" in imp for imp in file_info["imports"]), "Should detect datetime import"

# @pytest.mark.asyncio
# async def test_context_db_metadata_filter(context_db):
#     """Test searching context with metadata filters."""
#     # Add some domain knowledge with different metadata
#     python_content = """
#     Python is a high-level programming language known for its simplicity and readability.
#     It supports multiple programming paradigms including procedural, object-oriented, and functional programming.
#     """
#     python_metadata = {
#         "domain": "programming",
#         "language": "python",
#         "type": "language_info"
#     }
#     await context_db.add_domain_knowledge(python_content, python_metadata)
    
#     ai_content = """
#     Machine learning agents can be implemented in Python using various frameworks.
#     Popular frameworks include TensorFlow, PyTorch, and scikit-learn.
#     """
#     ai_metadata = {
#         "domain": "AI",
#         "type": "framework_info"
#     }
#     await context_db.add_domain_knowledge(ai_content, ai_metadata)
    
#     # Search with metadata filter
#     results = await context_db.search_context(
#         "Python",
#         collection_name="domain_knowledge",
#         metadata_filter={"domain": "programming"}
#     )
    
#     assert results, "Should find Python-related content"
#     assert all(r["metadata"]["domain"] == "programming" for r in results), "All results should be from programming domain"

# @pytest.mark.asyncio
# async def test_large_code_ingestion(context_db, temp_dir):
#     """Test ingesting a larger number of code files with various content."""
#     # Create a more complex directory structure
#     src_dir = os.path.join(temp_dir, "src")
#     os.makedirs(os.path.join(src_dir, "utils"))
#     os.makedirs(os.path.join(src_dir, "models"))
    
#     # Create some Python files with realistic content
#     files_content = {
#         "src/utils/helpers.py": """
# def format_string(s: str) -> str:
#     \"\"\"Format a string for display.\"\"\"
#     return s.strip().lower()

# class StringUtils:
#     @staticmethod
#     def capitalize_words(text: str) -> str:
#         return ' '.join(word.capitalize() for word in text.split())
# """,
#         "src/models/user.py": """
# from datetime import datetime

# class User:
#     def __init__(self, username: str):
#         self.username = username
#         self.created_at = datetime.now()
    
#     def validate(self) -> bool:
#         return len(self.username) >= 3
# """
#     }
    
#     # Write the files
#     for file_path, content in files_content.items():
#         full_path = os.path.join(temp_dir, file_path)
#         os.makedirs(os.path.dirname(full_path), exist_ok=True)
#         with open(full_path, 'w') as f:
#             f.write(content)
    
#     # Ingest the code
#     await context_db.ingest_code_directory(os.path.join(temp_dir, "src"))
    
#     # Test searching for various aspects
#     helper_results = await context_db.search_context("format_string")
#     assert helper_results, "Should find helper function"
    
#     class_results = await context_db.search_context("User class")
#     assert class_results, "Should find User class"
    
#     # Test specific file type filtering
#     python_files = await context_db.search_context(
#         "python",
#         metadata_filter={"file_type": ".py"}
#     )
#     assert python_files, "Should find Python files"

# @pytest.mark.asyncio
# async def test_collection_stats(context_db, sample_code_files):
#     """Test getting statistics about the collections."""
#     # Add some content to both collections
#     await context_db.ingest_code_directory(sample_code_files)
    
#     domain_content = "Sample domain knowledge for testing statistics."
#     await context_db.add_domain_knowledge(domain_content, {"domain": "test"})
    
#     # Get stats
#     stats = context_db.get_collection_stats()
    
#     assert "code" in stats, "Should have code collection stats"
#     assert "domain_knowledge" in stats, "Should have domain knowledge stats"
#     assert stats["code"]["total_chunks"] > 0, "Should have some code chunks"
#     assert stats["domain_knowledge"]["total_chunks"] > 0, "Should have some domain knowledge chunks"

# @pytest.mark.asyncio
# async def test_error_handling(context_db, temp_dir):
#     """Test error handling in various scenarios."""
#     # Test with non-existent directory
#     with pytest.raises(Exception):
#         await context_db.ingest_code_directory("/nonexistent/path")
    
#     # Test with invalid file content
#     invalid_file = os.path.join(temp_dir, "invalid.py")
#     with open(invalid_file, 'w') as f:
#         f.write("This is not valid Python code )")
    
#     # Should handle invalid Python files gracefully
#     await context_db.ingest_code_directory(temp_dir)
    
#     # Test with invalid metadata filter
#     results = await context_db.search_context(
#         "test",
#         metadata_filter={"nonexistent_field": "value"}
#     )
#     assert isinstance(results, list), "Should handle invalid metadata filter gracefully"

# async def test_ingest_code_directory(context_db, sample_code_files):
#     """Test ingesting code files into the vector database."""
#     # Ingest the sample code files
#     await context_db.ingest_code_directory(sample_code_files)
    
#     # Search for content we know exists
#     results = await context_db.search_context("TestClass", collection_name="code")
#     assert results, "Should find TestClass in the code"
#     assert any("test1.py" in r["metadata"]["file_name"] for r in results)

#     # Search for content we know exists in the second file
#     results = await context_db.search_context("another_function", collection_name="code")
#     assert results, "Should find another_function in the code"
#     assert any("test2.py" in r["metadata"]["file_name"] for r in results)

# @pytest.mark.asyncio
# async def test_add_domain_knowledge(context_db):
#     """Test adding and retrieving domain knowledge."""
#     # Add some domain knowledge
#     domain_content = """
#     Domain-specific information about AI agents:
#     An AI agent is an autonomous entity that can observe and act upon an environment.
#     Agents can be simple or complex, and may use various AI/ML techniques.
#     """
#     metadata = {
#         "domain": "AI",
#         "subdomain": "agents",
#         "source": "test",
#         "timestamp": "2024-01-01"
#     }
    
#     await context_db.add_domain_knowledge(domain_content, metadata)
    
#     # Search for the added knowledge
#     results = await context_db.search_context("AI agent", collection_name="domain_knowledge")
#     assert results, "Should find domain knowledge about AI agents"
#     assert any("AI" in r["metadata"]["domain"] for r in results)

# @pytest.mark.asyncio
# async def test_combine_context(context_db, sample_code_files):
#     """Test combining code and domain knowledge context."""
#     # First add both types of content
#     await context_db.ingest_code_directory(sample_code_files)
    
#     domain_content = """
#     TestClass is a common pattern in software testing.
#     It represents a unit test class that contains test methods.
#     """
#     metadata = {
#         "domain": "software_testing",
#         "source": "test"
#     }
#     await context_db.add_domain_knowledge(domain_content, metadata)
    
#     # Search for combined context
#     results = await context_db.combine_context("TestClass")
    
#     assert "code_context" in results, "Should have code context"
#     assert "domain_context" in results, "Should have domain context"
#     assert results["code_context"], "Should find TestClass in code"
#     assert results["domain_context"], "Should find TestClass in domain knowledge"

# #TODO: Add tests for the code catalog
