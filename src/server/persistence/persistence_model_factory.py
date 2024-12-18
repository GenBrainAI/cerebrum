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
            if 'persistence_model' in st.session_state:
                print("🔄 Using existing persistence model from session state")
                return st.session_state.persistence_model
            
            # If we're in Streamlit but no instance exists yet
            if cls._instance is None:
                print("🆕 Creating new persistence model")
                if type == "inmemory":
                    cls._instance = InMemoryPersistenceModel()
                else:
                    raise NotImplementedError(f"Unknown persistence model type: {type}")
                st.session_state.persistence_model = cls._instance
                print("✅ Stored new persistence model in session state")
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
            if 'persistence_model' in st.session_state:
                del st.session_state.persistence_model
        except ImportError:
            pass
