import pytest
from pathlib import Path
import json
from datetime import datetime, timedelta
from src.server.controllers.task_tree_state_manager import TaskTreeStateManager
from src.server.controllers.tasks_tree_controller import (
    TaskTreeManager, TaskNode, TaskStatus, ExecutionConfig,
    ExecutionStrategy, TaskExecutionError
)
from src.server.models.task import Task

class MockTask:
    def __init__(self, task: Task):
        self.id = task.id
        self.name = task.name
        self.description = task.description
        self.tasksmanager_id = task.tasksmanager_id
        self.messages = task.messages
        self.chat_sessions = task.chat_sessions
        self.toolsets = task.toolsets
        self.created_at = task.created_at
        self.updated_at = task.updated_at
        self.config = task.config
        self.use_context = task.use_context
        self.contexts = task.contexts

    async def run(self, context):
        print(f"MockTask.run called with context: {context}")  # Debug print
        return f"Result from {self.id}"

@pytest.fixture
def temp_state_dir(tmp_path):
    return str(tmp_path / "task_trees")

@pytest.fixture
def state_manager(temp_state_dir):
    return TaskTreeStateManager(base_path=temp_state_dir)

@pytest.fixture
def sample_tree():
    manager = TaskTreeManager()
    
    # Create tasks with different states
    tasks = [
        Task(id="1", name="Root"),
        Task(id="2", name="Running Task"),
        Task(id="3", name="Failed Task"),
        Task(id="4", name="Completed Task")
    ]
    
    # Create nodes with mock tasks
    for task in tasks:
        node = manager.create_node(task)
        node.task = MockTask(task)  # Use MockTask instead of original Task
        # Set execution config with proper defaults
        node.execution_config = ExecutionConfig(
            strategy=ExecutionStrategy.SEQUENTIAL,
            execute_children=True,
            propagate_context=True,
            fail_fast=False
        )
    
    # Set up tree structure
    manager.set_as_root("1")
    manager.add_child("1", "2")
    manager.add_child("1", "3")
    manager.add_child("1", "4")
    
    print("\nTree structure after setup:")  # Debug print
    for node_id, node in manager.nodes.items():
        print(f"Node {node_id}:")
        print(f"  Children: {[child.task.id for child in node.children]}")
        print(f"  Task type: {type(node.task)}")
        print(f"  Config: {node.execution_config}")
    
    # Set different states
    manager.nodes["2"].state.status = TaskStatus.RUNNING
    manager.nodes["3"].state.status = TaskStatus.FAILED
    manager.nodes["4"].state.status = TaskStatus.COMPLETED
    
    # Add execution times and metadata for node 4 (Completed Task)
    now = datetime.now()
    node4 = manager.nodes["4"]
    node4.state.started_at = now - timedelta(minutes=5)
    node4.state.completed_at = now
    node4.state.execution_duration = 300  # 5 minutes in seconds
    node4.state.metadata = {"success": True}
    
    # Add execution history for completed task
    node4.state.execution_history.append({
        "timestamp": (now - timedelta(minutes=5)).isoformat(),
        "old_status": TaskStatus.PENDING.value,
        "new_status": TaskStatus.RUNNING.value
    })
    node4.state.execution_history.append({
        "timestamp": now.isoformat(),
        "old_status": TaskStatus.RUNNING.value,
        "new_status": TaskStatus.COMPLETED.value
    })
    
    return manager

class TestStateManagement:
    @pytest.mark.asyncio
    async def test_state_persistence(self, state_manager, sample_tree):
        print("\nTree structure before saving:")
        for node_id, node in sample_tree.nodes.items():
            print(f"Node {node_id}:")
            print(f"  Status: {node.state.status}")
            print(f"  Children: {[child.task.id for child in node.children]}")
        
        # Save state
        success = await state_manager.save_tree_state("test_tree", sample_tree)
        assert success
        
        # Load state
        state_data = await state_manager.load_tree_state("test_tree")
        assert state_data is not None
        
        print("\nLoaded state data:")
        print(json.dumps(state_data, indent=2))
        
        # Verify state data
        assert state_data["metadata"]["tree_id"] == "test_tree"
        assert len(state_data["root_nodes"]) == 1
        assert state_data["root_nodes"][0]["task_id"] == "1"

    @pytest.mark.asyncio
    async def test_state_restoration(self, state_manager, sample_tree):
        # Save original state
        print("\nOriginal tree before saving:")
        for node_id, node in sample_tree.nodes.items():
            print(f"Node {node_id}:")
            print(f"  Status: {node.state.status}")
            print(f"  Children: {[child.task.id for child in node.children]}")
            print(f"  Task: {node.task.id} ({type(node.task)})")
        
        await state_manager.save_tree_state("test_tree", sample_tree)
        
        # Load and print state data
        state_data = await state_manager.load_tree_state("test_tree")
        print("\nLoaded state data:")
        print(json.dumps(state_data, indent=2))
        
        # Create new manager and restore state
        new_manager = TaskTreeManager()
        
        # Create tasks and nodes first
        tasks = [
            Task(id="1", name="Root"),
            Task(id="2", name="Running Task"),
            Task(id="3", name="Failed Task"),
            Task(id="4", name="Completed Task")
        ]
        
        # Create nodes with mock tasks
        for task in tasks:
            node = new_manager.create_node(task)
            node.task = MockTask(task)
            node.execution_config = ExecutionConfig(
                strategy=ExecutionStrategy.SEQUENTIAL,
                execute_children=True,
                propagate_context=True,
                fail_fast=False
            )
        
        # Rebuild tree structure
        new_manager.set_as_root("1")
        new_manager.add_child("1", "2")
        new_manager.add_child("1", "3")
        new_manager.add_child("1", "4")
        
        print("\nTree structure before state restoration:")
        for node_id, node in new_manager.nodes.items():
            print(f"Node {node_id}:")
            print(f"  Status: {node.state.status}")
            print(f"  Children: {[child.task.id for child in node.children]}")
            print(f"  Task: {node.task.id} ({type(node.task)})")
        
        # Now restore the state
        new_manager.restore_state(state_data)
        
        print("\nRestored tree structure:")
        for node_id, node in new_manager.nodes.items():
            print(f"Node {node_id}:")
            print(f"  Status: {node.state.status}")
            print(f"  Children: {[child.task.id for child in node.children]}")
            print(f"  Task: {node.task.id} ({type(node.task)})")
        
        print("\nComparing original and restored trees:")
        for node_id in sample_tree.nodes:
            orig_node = sample_tree.nodes[node_id]
            new_node = new_manager.nodes[node_id]
            print(f"\nNode {node_id}:")
            print(f"  Original status: {orig_node.state.status}")
            print(f"  Restored status: {new_node.state.status}")
            print(f"  Original children: {[c.task.id for c in orig_node.children]}")
            print(f"  Restored children: {[c.task.id for c in new_node.children]}")
        
        # Verify restored state
        assert len(new_manager.nodes) == len(sample_tree.nodes), (
            f"Node count mismatch. Original: {len(sample_tree.nodes)}, "
            f"Restored: {len(new_manager.nodes)}"
        )
        
        # Verify each node's state
        for node_id in sample_tree.nodes:
            assert node_id in new_manager.nodes, f"Node {node_id} missing from restored tree"
            orig_node = sample_tree.nodes[node_id]
            new_node = new_manager.nodes[node_id]
            
            assert new_node.state.status == orig_node.state.status, (
                f"Status mismatch for node {node_id}. "
                f"Original: {orig_node.state.status}, "
                f"Restored: {new_node.state.status}"
            )
            
            assert isinstance(new_node.task, MockTask), (
                f"Task type mismatch for node {node_id}. "
                f"Expected MockTask, got {type(new_node.task)}"
            )
            
            orig_children = {c.task.id for c in orig_node.children}
            new_children = {c.task.id for c in new_node.children}
            assert new_children == orig_children, (
                f"Children mismatch for node {node_id}. "
                f"Original: {orig_children}, "
                f"Restored: {new_children}"
            )

    @pytest.mark.asyncio
    async def test_execution_history(self, sample_tree):
        node = sample_tree.nodes["1"]
        
        # Simulate state transitions
        node.state.update_status(TaskStatus.RUNNING)
        node.state.update_status(TaskStatus.COMPLETED)
        
        print("\nExecution history:")
        for entry in node.state.execution_history:
            print(f"  {entry}")
        
        # Verify history
        assert len(node.state.execution_history) == 2
        assert node.state.execution_history[0]["old_status"] == TaskStatus.PENDING.value
        assert node.state.execution_history[0]["new_status"] == TaskStatus.RUNNING.value
        assert node.state.execution_history[1]["new_status"] == TaskStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_state_cleanup(self, state_manager, sample_tree, monkeypatch):
        # Mock datetime for consistent testing
        current_time = datetime(2024, 1, 1)
        old_time = datetime(2023, 1, 1)
        
        # Track which files have been "deleted"
        deleted_files = set()
        
        class MockDateTime:
            _now = current_time
            
            @classmethod
            def now(cls):
                return cls._now
                
            @classmethod
            def fromtimestamp(cls, timestamp):
                return datetime.fromtimestamp(timestamp)
        
        # Mock Path.stat() and Path.unlink() for file operations
        class MockStat:
            def __init__(self, mtime):
                self.st_mtime = mtime
                
        def mock_stat(self):
            # Convert Path to string for comparison
            path_str = str(self)
            if "old.json" in path_str:
                return MockStat(old_time.timestamp())
            return MockStat(current_time.timestamp())
        
        def mock_unlink(self, missing_ok=False):
            print(f"Mocked unlink called for {self}")
            deleted_files.add(str(self))
            return True
        
        def mock_exists(self):
            return str(self) not in deleted_files
        
        def mock_glob(self, pattern):
            # Return both files for *.json pattern
            if pattern == "*.json":
                base_dir = Path(state_manager.base_path)
                all_files = [
                    base_dir / "recent.json",
                    base_dir / "old.json"
                ]
                # Filter out deleted files
                return [f for f in all_files if str(f) not in deleted_files]
            return []
                
        # Patch all necessary path operations
        monkeypatch.setattr(Path, "stat", mock_stat)
        monkeypatch.setattr(Path, "unlink", mock_unlink)
        monkeypatch.setattr(Path, "exists", mock_exists)
        monkeypatch.setattr(Path, "glob", mock_glob)
        monkeypatch.setattr("src.server.controllers.task_tree_state_manager.datetime", MockDateTime)
        monkeypatch.setattr("datetime.datetime", MockDateTime)
        
        print("\nSetting up test files:")
        print(f"Current time: {current_time}")
        print(f"Old time: {old_time}")
        
        # Save states with different ages
        await state_manager.save_tree_state("recent", sample_tree)
        await state_manager.save_tree_state("old", sample_tree)
        
        print("\nSaved states:")
        states = await state_manager.list_saved_trees()
        for state in states:
            file_path = Path(state_manager.base_path) / f"{state['tree_id']}.json"
            mtime = file_path.stat().st_mtime
            print(f"  {state['tree_id']}: {datetime.fromtimestamp(mtime)}")
        
        # Clean up old states (30 days = 2592000 seconds)
        deleted = await state_manager.cleanup_old_states(max_age_days=30)
        print(f"\nDeleted {deleted} old states")
        print(f"Deleted files: {deleted_files}")
        
        # Verify only recent state remains
        remaining_states = await state_manager.list_saved_trees()
        print("\nRemaining states:")
        for state in remaining_states:
            print(f"  {state['tree_id']}")
        
        assert deleted == 1, f"Expected 1 state to be deleted, but {deleted} were deleted"
        assert len(remaining_states) == 1, f"Expected 1 state to remain, but found {len(remaining_states)}"
        assert remaining_states[0]["tree_id"] == "recent", (
            f"Expected 'recent' state to remain, but found {remaining_states[0]['tree_id']}"
        )

    @pytest.mark.asyncio
    async def test_state_versioning(self, state_manager, sample_tree):
        # Save state with version
        await state_manager.save_tree_state("test_tree", sample_tree)
        
        # Load state and verify version
        state_data = await state_manager.load_tree_state("test_tree")
        assert state_data["metadata"]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_execution_stats(self, sample_tree):
        node = sample_tree.nodes["4"]  # Completed task
        
        # Set up execution times
        now = datetime.now()
        node.state.started_at = now - timedelta(minutes=5)
        node.state.completed_at = now
        
        # Get and print stats for debugging
        stats = node.get_execution_stats()
        print("\nExecution stats:")
        print(json.dumps(stats, indent=2))
        print(f"\nNode state details:")
        print(f"Started at: {node.state.started_at}")
        print(f"Completed at: {node.state.completed_at}")
        print(f"Duration: {node.state.execution_duration}")
        
        # Basic assertions
        assert stats["status"] == TaskStatus.COMPLETED.value
        assert "started_at" in stats
        assert "completed_at" in stats
        
        # Duration should match the time difference
        duration = (node.state.completed_at - node.state.started_at).total_seconds()
        assert stats["execution_duration"] == duration
        
        # Metadata assertions
        assert stats["metadata"]["success"] is True

    @pytest.mark.asyncio
    async def test_state_corruption_handling(self, state_manager, sample_tree):
        # Save valid state
        await state_manager.save_tree_state("test_tree", sample_tree)
        
        # Corrupt the file
        state_file = Path(state_manager.base_path) / "test_tree.json"
        with open(state_file, "w") as f:
            f.write("invalid json")
        
        # Attempt to load corrupted state
        state_data = await state_manager.load_tree_state("test_tree")
        assert state_data is None

    @pytest.mark.asyncio
    async def test_atomic_state_saving(self, state_manager, sample_tree):
        # Save state
        await state_manager.save_tree_state("test_tree", sample_tree)
        
        # Verify no temporary files remain
        temp_files = list(Path(state_manager.base_path).glob("*.tmp"))
        assert len(temp_files) == 0
        
        # Verify state file exists
        state_file = Path(state_manager.base_path) / "test_tree.json"
        assert state_file.exists()

    @pytest.mark.asyncio
    async def test_state_metadata(self, state_manager, sample_tree):
        # Add custom metadata
        sample_tree.nodes["1"].state.metadata["custom_key"] = "custom_value"
        
        # Save and load state
        await state_manager.save_tree_state("test_tree", sample_tree)
        state_data = await state_manager.load_tree_state("test_tree")
        
        print("\nLoaded state data:")
        print(json.dumps(state_data, indent=2))
        
        # Create new manager and restore
        new_manager = TaskTreeManager()
        
        # Create tasks and nodes first
        tasks = [
            Task(id="1", name="Root"),
            Task(id="2", name="Running Task"),
            Task(id="3", name="Failed Task"),
            Task(id="4", name="Completed Task")
        ]
        
        # Create nodes with mock tasks
        for task in tasks:
            node = new_manager.create_node(task)
            node.task = MockTask(task)
            node.execution_config = ExecutionConfig(
                strategy=ExecutionStrategy.SEQUENTIAL,
                execute_children=True,
                propagate_context=True,
                fail_fast=False
            )
        
        # Rebuild tree structure
        new_manager.set_as_root("1")
        new_manager.add_child("1", "2")
        new_manager.add_child("1", "3")
        new_manager.add_child("1", "4")
        
        print("\nTree structure before state restoration:")
        for node_id, node in new_manager.nodes.items():
            print(f"Node {node_id}:")
            print(f"  Status: {node.state.status}")
            print(f"  Children: {[child.task.id for child in node.children]}")
            print(f"  Metadata: {node.state.metadata}")
        
        # Now restore the state
        new_manager.restore_state(state_data)
        
        print("\nRestored tree structure:")
        for node_id, node in new_manager.nodes.items():
            print(f"Node {node_id}:")
            print(f"  Status: {node.state.status}")
            print(f"  Children: {[child.task.id for child in node.children]}")
            print(f"  Metadata: {node.state.metadata}")
        
        # Verify metadata preserved
        assert new_manager.nodes["1"].state.metadata["custom_key"] == "custom_value" 