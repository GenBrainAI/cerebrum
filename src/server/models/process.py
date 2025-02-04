from enum import Enum

class Process(str, Enum):
    """Process type for crew execution.
    
    Attributes:
        sequential: Execute tasks in sequence without manager oversight
        hierarchical: Execute tasks with manager oversight and review
    """
    sequential = "sequential"
    hierarchical = "hierarchical" 