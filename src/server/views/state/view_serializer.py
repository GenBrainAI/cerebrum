from typing import Dict, Any
from ..models.view_state import ViewState
from ..models.view_types import ViewType
from uuid import UUID

class ViewStateSerializer:
    """Handles serialization of view states."""
    
    def serialize(self, state: ViewState) -> Dict[str, Any]:
        """Convert ViewState to dictionary format."""
        return {
            'view_type': state.view_type.value,
            'expanded_nodes': list(state.expanded_nodes),
            'selected_node': str(state.selected_node) if state.selected_node else None,
            'chat_history': [
                {
                    'role': msg['role'],
                    'content': msg['content'],
                    'timestamp': msg.get('timestamp')
                }
                for msg in state.chat_history
            ],
            'task_id': state.task_id,
            'metadata': {
                key: self._serialize_value(value)
                for key, value in state.metadata.items()
            }
        }
        
    def deserialize(self, data: Dict[str, Any]) -> ViewState:
        """Convert dictionary data back to ViewState."""
        return ViewState(
            view_type=ViewType(data['view_type']),
            expanded_nodes=set(data['expanded_nodes']),
            selected_node=UUID(data['selected_node']) if data.get('selected_node') else None,
            chat_history=data['chat_history'],
            task_id=data.get('task_id'),
            metadata=self._deserialize_metadata(data.get('metadata', {}))
        )
        
    def _serialize_value(self, value: Any) -> Any:
        """Handle serialization of special types."""
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, set):
            return list(value)
        return value
        
    def _deserialize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle deserialization of metadata values."""
        result = {}
        for key, value in metadata.items():
            if key.endswith('_id'):  # Assume IDs should be UUIDs
                try:
                    result[key] = UUID(value)
                    continue
                except (ValueError, AttributeError):
                    pass
            result[key] = value
        return result 