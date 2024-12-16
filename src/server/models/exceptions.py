class StateError(Exception):
    """Base exception for state-related errors."""
    pass

class StateNotFoundError(StateError):
    """Raised when a state cannot be found."""
    pass

class StateValidationError(StateError):
    """Raised when state validation fails."""
    pass

class StateLockError(StateError):
    """Raised when state locking fails."""
    pass

class StateUpdateError(StateError):
    """Raised when state update fails."""
    pass 