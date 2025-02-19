from typing import Optional, Any
import asyncio
from datetime import datetime
import streamlit as st
from pathlib import Path
import json
import traceback

class StatePersistenceManager:
    """Manages state persistence with debounced saving."""
    
    def __init__(self):
        print("\n🔧 Initializing StatePersistenceManager")
        self._save_pending = False
        self._last_save: Optional[datetime] = None
    
    async def save_state(self, persistence_model: Any) -> None:
        """Save the state immediately to disk."""
        print("\n💾 Starting state save...")
        print(f"  Persistence model: {persistence_model is not None}")
        
        try:
            print("\n📝 Starting save process...")
            print(f"  Persistence model available: {persistence_model is not None}")
            
            print("  Converting model to JSON")
            state_json = persistence_model.to_json()
            print("  JSON conversion successful")
            
            # Save to file using the appropriate path
            state_dir = Path(__file__).parent.parent.parent.parent / "state"
            metadata_path = state_dir / "metadata.json"
            
            print(f"  State directory exists: {state_dir.exists()}")
            print(f"  Checking metadata at: {metadata_path}")
            print(f"  Metadata exists: {metadata_path.exists()}")
            
            if metadata_path.exists():
                print("  Reading metadata file")
                with open(metadata_path) as f:
                    metadata = json.load(f)
                    print(f"  Metadata content: {metadata}")
                    state_file = metadata.get("last_used_state")
                    if state_file:
                        print(f"  Found state file: {state_file}")
                        state_path = state_dir / state_file
                        print(f"  State path exists: {state_path.exists()}")
                        print(f"  Saving to: {state_path}")
                        with open(state_path, "w") as f:
                            f.write(state_json)
                            print(f"✅ State successfully saved to {state_file}")
                    else:
                        print("❌ No state file found in metadata")
            else:
                print("❌ Metadata file not found")
            
            print("  Updating save status")
            self._last_save = datetime.now()
            self._save_pending = False
            st.session_state.save_status = "saved"
            st.session_state.last_save_time = datetime.now().timestamp()
            print("✅ Save process completed successfully")
            
        except Exception as e:
            print(f"❌ Error saving state: {str(e)}")
            print(f"  Stack trace: {traceback.format_exc()}")
            self._save_pending = False
            st.session_state.save_status = None 