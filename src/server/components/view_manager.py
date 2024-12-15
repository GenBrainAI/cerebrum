# src/server/controllers/view_manager.py
class ViewManager:
    def __init__(self):
        self.current_view = None
        self.tree_view = TreeView()
        
    async def switch_view(self, view_name: str):
        """Handle view transitions and state management."""
        self.current_view = view_name
        await self._load_view_state(view_name)