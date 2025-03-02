import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from scripts.initialize_self_aware import initialize_self_aware
from src.server.self_aware_integration import SelfAwareSystem

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_codebase_dir(temp_dir):
    """Create a directory with test codebase files."""
    test_dir = Path(temp_dir) / "test_codebase"
    test_dir.mkdir(exist_ok=True)
    
    # Create some test files
    (test_dir / "test_file.py").write_text("def test_function():\n    return 'Hello, World!'")
    (test_dir / "README.md").write_text("# Test Codebase\nThis is a test codebase for testing.")
    
    yield test_dir

@pytest.mark.asyncio
async def test_initialize_self_aware(temp_dir, test_codebase_dir):
    """Test initializing the Self-Aware Cerebrum system."""
    base_path = os.path.join(temp_dir, "self_aware")
    
    # Mock the setup_vector_store function
    mock_vector_result = {
        "total_files": 2,
        "indexed_files": 2,
        "skipped_files": 0,
        "errors": 0
    }
    
    # Mock the SelfAwareSystem class
    mock_system = MagicMock(spec=SelfAwareSystem)
    mock_system.initialize = AsyncMock()
    
    # Patch the necessary functions
    with patch('scripts.initialize_self_aware.setup_vector_store', return_value=mock_vector_result), \
         patch('scripts.initialize_self_aware.SelfAwareSystem', return_value=mock_system):
        
        # Call the initialize_self_aware function
        system = await initialize_self_aware(
            codebase_root=str(test_codebase_dir),
            base_path=base_path,
            setup_vector=True,
            incremental=False
        )
        
        # Check that the system was initialized correctly
        assert system == mock_system
        mock_system.initialize.assert_called_once()
        
        # Check that the base directory was created
        assert os.path.exists(base_path)

@pytest.mark.asyncio
async def test_initialize_self_aware_skip_vector(temp_dir, test_codebase_dir):
    """Test initializing the Self-Aware Cerebrum system with vector store setup skipped."""
    base_path = os.path.join(temp_dir, "self_aware")
    
    # Mock the SelfAwareSystem class
    mock_system = MagicMock(spec=SelfAwareSystem)
    mock_system.initialize = AsyncMock()
    
    # Patch the necessary functions
    with patch('scripts.initialize_self_aware.setup_vector_store') as mock_setup_vector, \
         patch('scripts.initialize_self_aware.SelfAwareSystem', return_value=mock_system):
        
        # Call the initialize_self_aware function with setup_vector=False
        system = await initialize_self_aware(
            codebase_root=str(test_codebase_dir),
            base_path=base_path,
            setup_vector=False,
            incremental=False
        )
        
        # Check that the system was initialized correctly
        assert system == mock_system
        mock_system.initialize.assert_called_once()
        
        # Check that setup_vector_store was not called
        mock_setup_vector.assert_not_called()
        
        # Check that the base directory was created
        assert os.path.exists(base_path)

@pytest.mark.asyncio
async def test_initialize_self_aware_incremental(temp_dir, test_codebase_dir):
    """Test initializing the Self-Aware Cerebrum system with incremental vector store setup."""
    base_path = os.path.join(temp_dir, "self_aware")
    
    # Mock the setup_vector_store function
    mock_vector_result = {
        "total_files": 2,
        "indexed_files": 0,
        "unchanged_files": 2,
        "skipped_files": 0,
        "errors": 0
    }
    
    # Mock the SelfAwareSystem class
    mock_system = MagicMock(spec=SelfAwareSystem)
    mock_system.initialize = AsyncMock()
    
    # Patch the necessary functions
    with patch('scripts.initialize_self_aware.setup_vector_store', return_value=mock_vector_result) as mock_setup_vector, \
         patch('scripts.initialize_self_aware.SelfAwareSystem', return_value=mock_system):
        
        # Call the initialize_self_aware function with incremental=True
        system = await initialize_self_aware(
            codebase_root=str(test_codebase_dir),
            base_path=base_path,
            setup_vector=True,
            incremental=True
        )
        
        # Check that the system was initialized correctly
        assert system == mock_system
        mock_system.initialize.assert_called_once()
        
        # Check that setup_vector_store was called with incremental=True
        mock_setup_vector.assert_called_once_with(
            codebase_root=str(test_codebase_dir),
            base_path=os.path.join(base_path, "vector_store"),
            incremental=True
        )
        
        # Check that the base directory was created
        assert os.path.exists(base_path)

@pytest.mark.asyncio
async def test_initialize_self_aware_system_components(temp_dir, test_codebase_dir):
    """Test that all system components are initialized correctly."""
    base_path = os.path.join(temp_dir, "self_aware")
    
    # Mock the setup_vector_store function
    mock_vector_result = {
        "total_files": 2,
        "indexed_files": 2,
        "skipped_files": 0,
        "errors": 0
    }
    
    # Create mock components
    mock_parameter_manager = MagicMock()
    mock_parameter_manager.initialize = AsyncMock()
    
    mock_knowledge_system = MagicMock()
    mock_knowledge_system.initialize = AsyncMock()
    
    mock_cognitive_orchestrator = MagicMock()
    mock_cognitive_orchestrator.initialize = AsyncMock()
    
    # Create a real SelfAwareSystem with mock components
    with patch('scripts.initialize_self_aware.setup_vector_store', return_value=mock_vector_result), \
         patch('src.server.self_aware_integration.AIParameterManager', return_value=mock_parameter_manager), \
         patch('src.server.self_aware_integration.KnowledgeIntegrationSystem', return_value=mock_knowledge_system), \
         patch('src.server.self_aware_integration.CognitiveLoopOrchestrator', return_value=mock_cognitive_orchestrator), \
         patch('src.server.self_aware_integration.SelfAwareSystem.register_specialized_workers', new_callable=AsyncMock):
        
        # Call the initialize_self_aware function
        system = await initialize_self_aware(
            codebase_root=str(test_codebase_dir),
            base_path=base_path,
            setup_vector=True,
            incremental=False
        )
        
        # Check that all components were initialized
        mock_parameter_manager.initialize.assert_called_once()
        mock_knowledge_system.initialize.assert_called_once()
        mock_cognitive_orchestrator.initialize.assert_called_once()
        system.register_specialized_workers.assert_called_once()

@pytest.mark.asyncio
async def test_initialize_self_aware_error_handling(temp_dir, test_codebase_dir):
    """Test error handling during initialization."""
    base_path = os.path.join(temp_dir, "self_aware")
    
    # Mock the setup_vector_store function to raise an exception
    mock_setup_vector = AsyncMock(side_effect=Exception("Test error"))
    
    # Mock the SelfAwareSystem class
    mock_system = MagicMock(spec=SelfAwareSystem)
    mock_system.initialize = AsyncMock()
    
    # Patch the necessary functions
    with patch('scripts.initialize_self_aware.setup_vector_store', mock_setup_vector), \
         patch('scripts.initialize_self_aware.SelfAwareSystem', return_value=mock_system), \
         pytest.raises(Exception) as excinfo:
        
        # Call the initialize_self_aware function
        await initialize_self_aware(
            codebase_root=str(test_codebase_dir),
            base_path=base_path,
            setup_vector=True,
            incremental=False
        )
    
    # Check that the exception was raised
    assert "Test error" in str(excinfo.value)
    
    # Check that the base directory was still created
    assert os.path.exists(base_path) 