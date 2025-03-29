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
                instance = st.session_state.persistence_model
                print(f"🔄 Using existing persistence model from session state: id={id(instance)}")
                # Debug the tasks in the existing persistence model
                try:
                    task_count = len(instance.tasks.list())
                    print(f"📊 Existing persistence model has {task_count} tasks")
                except Exception as e:
                    print(f"⚠️ Could not get task count: {str(e)}")
                return instance
            
            # If we're in Streamlit but no instance exists yet
            if cls._instance is None:
                print("🆕 Creating new persistence model")
                if type == "inmemory":
                    cls._instance = InMemoryPersistenceModel()
                    print(f"🆕 Created InMemoryPersistenceModel: id={id(cls._instance)}")
                else:
                    raise NotImplementedError(f"Unknown persistence model type: {type}")
                
                st.session_state.persistence_model = cls._instance
                print(f"✅ Stored new persistence model in session state: id={id(cls._instance)}")
            else:
                print(f"🔄 Using existing singleton persistence model: id={id(cls._instance)}")
                # Debug the tasks in the existing singleton
                try:
                    task_count = len(cls._instance.tasks.list())
                    print(f"📊 Existing singleton has {task_count} tasks")
                except Exception as e:
                    print(f"⚠️ Could not get singleton task count: {str(e)}")
            
            return cls._instance
            
        except ImportError:
            # Non-Streamlit context - use regular singleton pattern
            if cls._instance is None:
                if type == "inmemory":
                    cls._instance = InMemoryPersistenceModel()
                    print(f"🆕 Created InMemoryPersistenceModel outside Streamlit: id={id(cls._instance)}")
                else:
                    raise NotImplementedError(f"Unknown persistence model type: {type}")
            else:
                print(f"🔄 Using existing singleton outside Streamlit: id={id(cls._instance)}")
            
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
