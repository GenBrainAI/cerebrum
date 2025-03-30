import pytest
from datetime import datetime
import uuid
from src.server.models.tasks_manager import TasksManager, TaskSequence

def test_task_sequence_creation():
    """Test creating a task sequence in a TasksManager."""
    # Create TasksManager
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager",
        description="Test manager description"
    )
    
    # Create sequence
    sequence = TaskSequence(
        name="Test Sequence",
        description="Test sequence description",
        task_ids=["task1", "task2", "task3"]
    )
    
    # Add sequence to TasksManager
    sequence_id = tm.add_sequence(sequence)
    
    # Assertions
    assert sequence_id is not None
    assert hasattr(tm, 'task_sequences')
    assert sequence_id in tm.task_sequences
    assert tm.task_sequences[sequence_id].name == "Test Sequence"
    assert len(tm.task_sequences[sequence_id].task_ids) == 3

def test_task_sequence_update():
    """Test updating a task sequence."""
    # Create TasksManager with sequence
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager"
    )
    
    sequence = TaskSequence(
        id="seq1",
        name="Original Name",
        description="Original description",
        task_ids=["task1", "task2"]
    )
    
    tm.add_sequence(sequence)
    
    # Update sequence
    updated_sequence = TaskSequence(
        id="seq1",
        name="Updated Name",
        description="Updated description",
        task_ids=["task1", "task2", "task3"]
    )
    
    result = tm.update_sequence("seq1", updated_sequence)
    
    # Assertions
    assert result is True
    assert tm.task_sequences["seq1"].name == "Updated Name"
    assert tm.task_sequences["seq1"].description == "Updated description"
    assert len(tm.task_sequences["seq1"].task_ids) == 3

def test_task_sequence_remove():
    """Test removing a task sequence."""
    # Create TasksManager with sequence
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager"
    )
    
    sequence = TaskSequence(
        id="seq1",
        name="Test Sequence",
        task_ids=["task1", "task2"]
    )
    
    tm.add_sequence(sequence)
    
    # Remove sequence
    result = tm.remove_sequence("seq1")
    
    # Assertions
    assert result is True
    assert "seq1" not in tm.task_sequences

def test_get_sequences():
    """Test getting all sequences from a TasksManager."""
    # Create TasksManager
    tm = TasksManager(
        id=str(uuid.uuid4()),
        name="Test Manager"
    )
    
    # Add sequences
    seq1 = TaskSequence(id="seq1", name="Sequence 1", task_ids=["task1", "task2"])
    seq2 = TaskSequence(id="seq2", name="Sequence 2", task_ids=["task3", "task4"])
    
    tm.add_sequence(seq1)
    tm.add_sequence(seq2)
    
    # Get sequences
    sequences = tm.get_sequences()
    
    # Assertions
    assert len(sequences) == 2
    assert any(s.id == "seq1" for s in sequences)
    assert any(s.id == "seq2" for s in sequences) 