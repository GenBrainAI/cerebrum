# Context Development Next Steps

## Recent Changes Completed
1. Fixed knowledge base tag handling:
   - Modified `add_entry` to properly combine tags from both sources:
     - Tags passed directly via the `tags` parameter
     - Tags included in the `metadata` dictionary
   - Implemented proper storage of tags in both:
     - Top-level `tags` field
     - Within `metadata.tags`
   - Ensured proper domain storage and filtering
   - Fixed tag-based filtering in `get_entries`

## Current Issues Identified

### 1. Context-Task Association Auto-Save
**Problem:**
- Context associations to tasks appear in the tree but aren't automatically saved
- Users must manually navigate to the main page sidebar to save the state

**Proposed Solution:**
- Implement automatic state saving when context associations are modified
- Add state persistence hooks in the context management sidebar
- Consider adding a debounced auto-save mechanism to prevent excessive writes

### 2. State Loading on Non-Home Pages
**Problem:**
- When starting navigation from pages other than home, no state is loaded
- Only the home page (chat.py) automatically loads the last state

**Proposed Solution:**
- Implement consistent state loading across all pages
- Add state loading logic in a common initialization point
- Load last state automatically when:
  - No state is currently loaded
  - User is on a non-home page
  - A last state exists in metadata.json

## Implementation Tasks

### Auto-Save Feature
1. Modify `ContextManagementSidebar`:
   - Add state persistence after context tree modifications
   - Implement debounced save mechanism
   - Add visual feedback for save status

2. Update context association handlers:
   - Add auto-save triggers in context addition/removal
   - Ensure proper error handling and recovery
   - Add rollback capability for failed saves

### Global State Loading
1. Create common state loading utility:
   - Extract state loading logic from chat.py
   - Make it available to all pages
   - Add proper error handling and fallbacks

2. Modify page initialization:
   - Add state loading check in common component
   - Implement automatic loading when needed
   - Preserve user-selected states when present

## Testing Requirements
1. Add tests for auto-save functionality:
   - Verify state persistence after modifications
   - Test debounce behavior
   - Verify error handling and recovery

2. Add tests for global state loading:
   - Test state loading on different pages
   - Verify proper handling of missing states
   - Test state preservation scenarios

## Notes
- Consider adding a small UI indicator for save status
- Maintain proper error handling and user feedback
- Ensure backward compatibility with existing state files
- Consider adding state versioning for future migrations

## Code Implementation Details

### 1. Auto-Save Feature Implementation

#### a. Create State Persistence Manager
```python
# src/server/persistence/state_persistence_manager.py

from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
from pathlib import Path
import json

class StatePersistenceManager:
    """Manages state persistence with debounced saving."""
    
    def __init__(self, save_delay: float = 0.5):
        self._save_delay = save_delay
        self._save_timer: Optional[asyncio.Task] = None
        self._last_save: Optional[datetime] = None
        self._save_pending = False
    
    async def schedule_save(self, persistence_model: Any) -> None:
        """Schedule a debounced save operation."""
        self._save_pending = True
        
        if self._save_timer:
            self._save_timer.cancel()
            
        self._save_timer = asyncio.create_task(self._delayed_save(persistence_model))
    
    async def _delayed_save(self, persistence_model: Any) -> None:
        """Execute the save after delay."""
        await asyncio.sleep(self._save_delay)
        if self._save_pending:
            await persistence_model.save_state()
            self._last_save = datetime.now()
            self._save_pending = False
```

#### b. Modify ContextManagementSidebar
```python
# src/server/views/components/sidebar/context_mng_sidebar.py

class ContextManagementSidebar:
    def __init__(self, context_manager=None):
        self.context_manager = context_manager
        self.state_persistence = StatePersistenceManager()
        # ... existing initialization code ...
    
    async def _handle_context_change(self):
        """Handle context modifications."""
        if self.context_manager and self.context_manager.persistence_model:
            await self.state_persistence.schedule_save(self.context_manager.persistence_model)
            # Update UI to show save pending/complete status
            st.session_state.save_status = "pending"
```

### 2. Global State Loading Implementation

#### a. Create State Loading Utility
```python
# src/server/utils/state_loader.py

from typing import Optional
from pathlib import Path
import json

class StateLoader:
    """Utility for consistent state loading across pages."""
    
    @staticmethod
    async def load_last_state() -> Optional[str]:
        """Load the last used state if available."""
        try:
            metadata_path = Path("state/metadata.json")
            if not metadata_path.exists():
                return None
                
            with open(metadata_path) as f:
                metadata = json.load(f)
                return metadata.get("last_used_state")
        except Exception as e:
            logging.error(f"Error loading last state: {str(e)}")
            return None
    
    @staticmethod
    async def ensure_state_loaded(st_session_state: Any) -> bool:
        """Ensure a state is loaded in the session."""
        if "context_manager" not in st_session_state:
            last_state = await StateLoader.load_last_state()
            if last_state:
                # Load the state using existing loading mechanism
                await load_state(last_state)
                return True
        return False
```

#### b. Modify Page Initialization
```python
# src/server/views/pages/base_page.py

class BasePage:
    """Base class for all pages with common state loading."""
    
    async def initialize(self):
        """Initialize page state."""
        if not st.session_state.get("initialized_state"):
            await StateLoader.ensure_state_loaded(st.session_state)
            st.session_state.initialized_state = True
```

## Unit Tests

### 1. Auto-Save Feature Tests
```python
# tests/persistence/test_state_persistence.py

import pytest
from datetime import datetime, timedelta

class TestStatePersistenceManager:
    @pytest.fixture
    def persistence_manager(self):
        return StatePersistenceManager(save_delay=0.1)
    
    @pytest.mark.asyncio
    async def test_debounced_save(self, persistence_manager):
        """Test that multiple save requests are debounced."""
        mock_model = AsyncMock()
        
        # Schedule multiple saves in quick succession
        for _ in range(5):
            await persistence_manager.schedule_save(mock_model)
            await asyncio.sleep(0.05)
        
        # Wait for debounce period
        await asyncio.sleep(0.2)
        
        # Should only have saved once
        mock_model.save_state.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_status(self, persistence_manager):
        """Test save status tracking."""
        mock_model = AsyncMock()
        
        assert not persistence_manager._save_pending
        await persistence_manager.schedule_save(mock_model)
        assert persistence_manager._save_pending
        
        await asyncio.sleep(0.2)
        assert not persistence_manager._save_pending
```

### 2. State Loading Tests
```python
# tests/utils/test_state_loader.py

import pytest
from pathlib import Path

class TestStateLoader:
    @pytest.fixture
    def mock_metadata(self, tmp_path):
        metadata = {
            "last_used_state": "test_state.json",
            "last_task_id": "task1"
        }
        metadata_file = tmp_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)
        return metadata_file
    
    @pytest.mark.asyncio
    async def test_load_last_state(self, mock_metadata):
        """Test loading last state from metadata."""
        state_loader = StateLoader()
        last_state = await state_loader.load_last_state()
        assert last_state == "test_state.json"
    
    @pytest.mark.asyncio
    async def test_ensure_state_loaded(self, mock_metadata):
        """Test ensuring state is loaded in session."""
        mock_session = {}
        result = await StateLoader.ensure_state_loaded(mock_session)
        assert result
        assert "context_manager" in mock_session
    
    @pytest.mark.asyncio
    async def test_no_metadata_handling(self):
        """Test handling when no metadata exists."""
        state_loader = StateLoader()
        last_state = await state_loader.load_last_state()
        assert last_state is None
```

## Integration Tests

```python
# tests/integration/test_context_persistence.py

import pytest
from unittest.mock import AsyncMock

class TestContextPersistence:
    @pytest.fixture
    async def setup_context(self):
        """Setup test context with mock persistence."""
        context_manager = await create_test_context_manager()
        sidebar = ContextManagementSidebar(context_manager)
        return context_manager, sidebar
    
    @pytest.mark.asyncio
    async def test_auto_save_on_context_change(self, setup_context):
        """Test that context changes trigger auto-save."""
        context_manager, sidebar = await setup_context
        
        # Add a context
        await context_manager.add_context_to_task(
            task_id="test_task",
            type="vector",
            source_id="test_source"
        )
        
        # Verify save was triggered
        await asyncio.sleep(0.6)  # Wait for debounce
        assert context_manager.persistence_model.save_state.called
    
    @pytest.mark.asyncio
    async def test_state_loading_on_page_init(self, setup_context):
        """Test state loading during page initialization."""
        mock_session = {}
        page = BasePage()
        await page.initialize()
        
        assert "initialized_state" in mock_session
        assert mock_session.get("context_manager") is not None
```

## Implementation Order

1. State Persistence Manager
   - Implement base persistence manager
   - Add debounce mechanism
   - Add save status tracking

2. Context Management Integration
   - Modify sidebar to use persistence manager
   - Add save status UI elements
   - Implement context change handlers

3. State Loading Utility
   - Create base state loader
   - Implement metadata handling
   - Add session state management

4. Page Integration
   - Create base page class
   - Add state initialization
   - Implement in all pages

5. Testing
   - Implement unit tests
   - Add integration tests
   - Test edge cases and error handling

## Deployment Notes

1. Database Migration
   - No schema changes required
   - Existing state files remain compatible

2. Configuration Updates
   - Add `SAVE_DELAY` to config (default: 0.5s)
   - Add `AUTO_LOAD_STATE` flag (default: true)

3. Monitoring
   - Add save operation metrics
   - Track state loading success/failure
   - Monitor save frequency and timing 