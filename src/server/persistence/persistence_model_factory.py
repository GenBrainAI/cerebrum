from typing import Optional
from .persistence_model import PersistenceModelBase
from .in_memory_persistence import InMemoryPersistenceModel


class PersistenceModelFactory:
    _instance: Optional[PersistenceModelBase] = None

    @classmethod
    def persistence_model(cls, type: str = "inmemory") -> PersistenceModelBase:
        # Check if we're in a Streamlit context
        try:
            import streamlit as st
            # Initialize instance if it doesn't exist
            if cls._instance is None:
                print("🆕 Creating new persistence model")
                if type == "inmemory":
                    cls._instance = InMemoryPersistenceModel()
                else:
                    raise NotImplementedError(f"Unknown persistence model type: {type}")

            # Check if streamlit session state is available and properly initialized
            session_state_available = hasattr(st, 'session_state') and isinstance(st.session_state, dict)
            
            if session_state_available and 'persistence_model' in st.session_state:
                print("🔄 Using existing persistence model from session state")
                return st.session_state.persistence_model
            
            # Store instance in session state if possible
            if session_state_available:
                try:
                    st.session_state.persistence_model = cls._instance
                    print("✅ Stored new persistence model in session state")
                except Exception as e:
                    # Fall back to singleton if we can't store in session state
                    print(f"⚠️ Could not store in session state: {str(e)}")
                
            return cls._instance
            
        except ImportError:
            # Non-Streamlit context - use regular singleton pattern
            if cls._instance is None:
                if type == "inmemory":
                    cls._instance = InMemoryPersistenceModel()
                else:
                    raise NotImplementedError(f"Unknown persistence model type: {type}")
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance - mainly for testing purposes"""
        cls._instance = None
        try:
            import streamlit as st
            if hasattr(st, 'session_state') and isinstance(st.session_state, dict) and 'persistence_model' in st.session_state:
                del st.session_state.persistence_model
        except (ImportError, AttributeError):
            pass
