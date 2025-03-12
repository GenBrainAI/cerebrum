from typing import Dict, Any
import streamlit as st
from pathlib import Path
import json
from datetime import datetime
from server.views.models.view_types import ViewType

class BaseView:
    def __init__(self, view_type: ViewType):
        self.view_type = view_type
        # Initialize state directory if not already set
        if 'state_dir' not in st.session_state:
            st.session_state.state_dir = self.get_state_dir()
        
    def get_state_dir(self) -> Path:
        """Get the state directory path, creating it if necessary."""
        # Get project root (assumes this file is in src/server/views/base_view.py)
        project_root = Path(__file__).parent.parent.parent.parent
        state_dir = project_root / "state"
        state_dir.mkdir(exist_ok=True)
        return state_dir
        
    def get_session_filename(self) -> str:
        """Get the default session filename for this view."""
        return f"{self.view_type.value.lower()}_view_default.json"
        
    def get_session_data(self) -> Dict[str, Any]:
        """Get the current session data to save."""
        return {
            'current_view': self.view_type,
            'current_tasksmanager_id': st.session_state.get('current_tasksmanager_id'),
            'current_task_id': st.session_state.get('current_task_id'),
            'current_session_id': st.session_state.get('current_session_id'),
            'last_access': datetime.now().isoformat()
        }
        
    def save_session(self):
        """Save the current view session."""
        session_dir = Path(st.session_state.state_dir) / "sessions"
        session_dir.mkdir(exist_ok=True)
        
        session_data = self.get_session_data()
        session_file = session_dir / self.get_session_filename()
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, default=lambda x: x.dict() if hasattr(x, 'dict') else str(x))
            
    def load_session(self):
        """Load the view session."""
        session_file = Path(st.session_state.state_dir) / "sessions" / self.get_session_filename()
        print(f"📂 Looking for session file: {session_file}")
        
        if session_file.exists():
            print(f"📂 Session file found, loading data")
            with open(session_file) as f:
                session_data = json.load(f)
                
            # Log session data for debugging
            print(f"📂 Loaded session data: {session_data}")
                
            # Restore view-specific session state
            self.restore_session_state(session_data)
            print(f"📂 Session state restored")
        else:
            print(f"📂 No session file found at {session_file}")
                
    def restore_session_state(self, session_data: Dict[str, Any]):
        """Restore session state from loaded data. Override in view classes."""
        st.session_state.current_view = session_data.get('current_view')
        st.session_state.current_tasksmanager_id = session_data.get('current_tasksmanager_id')
        st.session_state.current_task_id = session_data.get('current_task_id')
        st.session_state.current_session_id = session_data.get('current_session_id') 