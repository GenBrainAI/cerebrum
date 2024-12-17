

class TreeView:
    def __init__(self):
        self.expanded_nodes = set()
        
    def render_tree(self, data, node_type):
        """Render hierarchical data as an interactive tree."""
        if node_type == "tasks":
            return self._render_task_tree(data)
        elif node_type == "tools":
            return self._render_tools_tree(data)
        else:
            return self._render_agent_tree(data)