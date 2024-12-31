import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from typing import Dict, Any, List
import math

from src.server.context.unified_context import UnifiedContextState, ContextConfig
from src.server.context.crew_ai_knowledge_bridge import CrewAIKnowledgeBridge
from src.server.models.task import Task as CerebrumTask

class MockVectorStore:
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        return [
            {
                "content": "Vector content 1",
                "relevance": 0.9,
                "metadata": {"source": "vector_1"}
            },
            {
                "content": "Vector content 2",
                "relevance": 0.7,
                "metadata": {"source": "vector_2"}
            }
        ]

class MockKnowledgeBase:
    def get_knowledge(self, domain: str = None, tags: List[str] = None) -> List[Dict[str, Any]]:
        return [
            {
                "content": "Knowledge content 1",
                "metadata": {"domain": domain or "test", "source": "kb_1"}
            },
            {
                "content": "Knowledge content 2",
                "metadata": {"domain": domain or "test", "source": "kb_2"}
            }
        ]

class MockCodeCatalog:
    def get_file_content(self, file_id: str) -> str:
        return f"Code content for {file_id}"

@pytest_asyncio.fixture
async def unified_state():
    """Create a test unified context state instance."""
    config = ContextConfig()
    state = UnifiedContextState(config=config)
    
    # Mock the context stores
    state.vector_store = MockVectorStore()
    state.knowledge_base = MockKnowledgeBase()
    state.code_catalog = MockCodeCatalog()
    
    # Mock the context provider
    state.context_provider = AsyncMock()
    state.context_provider._get_vector_contexts.return_value = [
        {
            "type": "vector",
            "content": "Vector content 1",
            "relevance": 0.9,
            "metadata": {"source": "vector_1"}
        }
    ]
    state.context_provider._get_knowledge_contexts.return_value = [
        {
            "type": "knowledge",
            "content": "Knowledge content 1",
            "relevance": 0.8,
            "metadata": {"source": "kb_1"}
        }
    ]
    state.context_provider._get_code_contexts.return_value = [
        {
            "type": "code",
            "content": "Code content 1",
            "relevance": 0.7,
            "metadata": {"source": "code_1"}
        }
    ]
    
    return state

@pytest_asyncio.fixture
async def crew_bridge(unified_state):
    """Create a test CrewAI knowledge bridge instance."""
    return CrewAIKnowledgeBridge(unified_state)

@pytest.mark.asyncio
async def test_unified_state_initialization(unified_state):
    """Test that UnifiedContextState initializes correctly."""
    assert unified_state.config is not None
    assert unified_state.vector_store is not None
    assert unified_state.knowledge_base is not None
    assert unified_state.code_catalog is not None
    assert unified_state.context_assignments == {
        "cerebrum": {
            "tasks": {},
            "task_managers": {}
        },
        "crew_ai": {
            "agents": {},
            "tasks": {},
            "crews": {}
        }
    }

@pytest.mark.asyncio
async def test_assign_context_to_cerebrum_task(unified_state):
    """Test assigning context to a Cerebrum task."""
    task_id = "test_task_1"
    context_types = ["vector", "knowledge"]
    metadata = {"domain": "test"}
    
    await unified_state.assign_context_to_cerebrum_task(task_id, context_types, metadata)
    
    assert task_id in unified_state.context_assignments["cerebrum"]["tasks"]
    assignment = unified_state.context_assignments["cerebrum"]["tasks"][task_id]
    assert assignment["types"] == context_types
    assert assignment["metadata"] == metadata

@pytest.mark.asyncio
async def test_assign_context_to_crew_agent(unified_state):
    """Test assigning context to a CrewAI agent."""
    agent_id = "test_agent_1"
    context_types = ["vector", "knowledge"]
    metadata = {"role": "researcher"}
    
    await unified_state.assign_context_to_crew_agent(agent_id, context_types, metadata)
    
    assert agent_id in unified_state.context_assignments["crew_ai"]["agents"]
    assignment = unified_state.context_assignments["crew_ai"]["agents"][agent_id]
    assert assignment["types"] == context_types
    assert assignment["metadata"] == metadata

@pytest.mark.asyncio
async def test_get_context_for_entity_with_assignments(unified_state):
    """Test getting context for an entity with explicit assignments."""
    task_id = "test_task_1"
    context_types = ["vector", "knowledge", "code"]
    await unified_state.assign_context_to_cerebrum_task(task_id, context_types, {})
    
    contexts = await unified_state.get_context_for_entity(
        entity_type="tasks",
        framework="cerebrum",
        entity_id=task_id
    )
    
    assert len(contexts) > 0
    for context in contexts:
        assert "type" in context
        assert "content" in context
        assert "weighted_relevance" in context
        assert context["type"] in context_types

@pytest.mark.asyncio
async def test_get_context_for_entity_with_defaults(unified_state):
    """Test getting context for an entity using framework defaults."""
    task_id = "test_task_2"
    
    contexts = await unified_state.get_context_for_entity(
        entity_type="tasks",
        framework="crew_ai",
        entity_id=task_id
    )
    
    assert len(contexts) > 0
    default_types = unified_state.config.framework_configs["crew_ai"]["default_context_types"]
    for context in contexts:
        assert context["type"] in default_types
        assert context["weighted_relevance"] >= unified_state.config.framework_configs["crew_ai"]["min_relevance"]

@pytest.mark.asyncio
async def test_create_specialized_state_crew_ai(unified_state):
    """Test creating specialized state for CrewAI."""
    config = {
        "agents": [],
        "tasks": []
    }
    
    state = await unified_state.create_specialized_state("crew_ai", config)
    
    assert "crew_config" in state
    assert "context_provider" in state
    assert "crew_bridge" in state

@pytest.mark.asyncio
async def test_create_specialized_state_cerebrum(unified_state):
    """Test creating specialized state for Cerebrum."""
    state = await unified_state.create_specialized_state("cerebrum", {})
    
    assert "context_provider" in state
    assert "vector_store" in state
    assert "knowledge_base" in state
    assert "code_catalog" in state

@pytest.mark.asyncio
async def test_crew_bridge_create_knowledge(crew_bridge):
    """Test CrewAI knowledge bridge creating knowledge sources."""
    task = CerebrumTask(id="test_task_1")
    
    knowledge_sources = await crew_bridge.create_crew_knowledge(task)
    
    assert len(knowledge_sources) > 0
    for source in knowledge_sources:
        assert hasattr(source, "content")
        assert hasattr(source, "metadata")
        assert source.metadata["weighted_relevance"] >= crew_bridge.unified_state.config.framework_configs["crew_ai"]["min_relevance"]

@pytest.mark.asyncio
async def test_crew_bridge_prepare_context(crew_bridge):
    """Test CrewAI knowledge bridge preparing context."""
    task = CerebrumTask(id="test_task_1")
    
    contexts = await crew_bridge.prepare_crew_context(task)
    
    assert len(contexts) > 0
    for context in contexts:
        assert "type" in context
        assert "content" in context or "file_path" in context
        assert "metadata" in context
        assert context["metadata"]["weighted_relevance"] >= crew_bridge.unified_state.config.framework_configs["crew_ai"]["min_relevance"]

@pytest.mark.asyncio
async def test_context_weights_and_relevance(unified_state):
    """Test that context weights are applied correctly for both knowledge and vector contexts."""
    task_id = "test_task_3"
    
    # Get contexts with CrewAI weights
    crew_contexts = await unified_state.get_context_for_entity(
        entity_type="tasks",
        framework="crew_ai",
        entity_id=task_id
    )
    
    # Print configuration for debugging
    print("\nCrewAI Context Weights:")
    print(unified_state.config.framework_configs["crew_ai"]["context_weights"])
    
    # Create a map of expected contexts based on our mock data
    expected_contexts = {
        "knowledge": {
            "raw_relevance": 0.8,
            "weight": 1.0,
            "expected_weighted": 0.8
        },
        "vector": {
            "raw_relevance": 0.9,
            "weight": 0.8,
            "expected_weighted": 0.72
        }
    }
    
    # Verify weights for all context types
    for context in crew_contexts:
        context_type = context["type"]
        expected = expected_contexts[context_type]
        
        # Get the raw relevance and weight from config
        raw_relevance = context.get("relevance", 0)
        weight = unified_state.config.framework_configs["crew_ai"]["context_weights"][context_type]
        actual = context["weighted_relevance"]
        
        print(f"\n{context_type.capitalize()} Context Details:")
        print(f"Raw Relevance: {raw_relevance}")
        print(f"Weight from config: {weight}")
        print(f"Expected weighted relevance: {expected['expected_weighted']}")
        print(f"Actual weighted relevance: {actual}")
        
        # Verify raw relevance matches mock data
        assert raw_relevance == expected["raw_relevance"], \
            f"{context_type} raw relevance mismatch. Expected {expected['raw_relevance']}, got {raw_relevance}"
        
        # Verify weight matches config
        assert weight == expected["weight"], \
            f"{context_type} weight mismatch. Expected {expected['weight']}, got {weight}"
        
        # Verify weighted relevance is calculated correctly
        assert math.isclose(actual, expected["expected_weighted"], rel_tol=1e-9), \
            f"{context_type} weighted relevance mismatch. Expected {expected['expected_weighted']}, got {actual}"