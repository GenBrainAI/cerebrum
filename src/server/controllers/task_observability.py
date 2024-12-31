import sys
from io import StringIO
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from enum import Enum
import asyncio
from queue import Queue
from threading import Lock

class ObservabilityLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class TeeStdout:
    """Custom stdout that writes to both original stdout and a StringIO buffer."""
    def __init__(self, original_stdout, string_buffer):
        self.original_stdout = original_stdout
        self.string_buffer = string_buffer

    def write(self, text):
        self.original_stdout.write(text)
        self.string_buffer.write(text)
        
    def flush(self):
        self.original_stdout.flush()
        self.string_buffer.flush()

class ObservabilityEntry:
    def __init__(
        self,
        message: str,
        level: ObservabilityLevel = ObservabilityLevel.INFO,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.level = level
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "level": self.level.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

class TaskObservabilityManager:
    """Manages observability for task execution including stdout capture and state monitoring."""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.original_stdout = sys.stdout
        self.output_buffer = StringIO()
        self._last_output_pos = 0
        self.entries: List[ObservabilityEntry] = []
        self._buffer_lock = Lock()
        self._entry_queue = Queue()
        self.logger = logging.getLogger(__name__)
        self.tee_stdout = TeeStdout(self.original_stdout, self.output_buffer)
        self._capture_active = False

    def start_capture(self):
        """Start capturing stdout"""
        if not self._capture_active:
            print("\n📝 Starting output capture for task:", self.task_id)
            sys.stdout = self.tee_stdout
            self._capture_active = True
            self.add_entry("Started output capture", ObservabilityLevel.INFO)
            # Immediately process any buffered output
            self._process_current_output()
        return self

    def stop_capture(self):
        """Stop capturing and restore original stdout"""
        if self._capture_active:
            # Process any remaining output before stopping
            self._process_current_output()
            sys.stdout = self.original_stdout
            self._capture_active = False
            self.add_entry("Stopped output capture", ObservabilityLevel.INFO)
            print("\n✅ Stopped output capture for task:", self.task_id)

    def _process_current_output(self):
        """Process current output in buffer and add as entries."""
        with self._buffer_lock:
            current_output = self.output_buffer.getvalue()
            if len(current_output) > self._last_output_pos:
                new_output = current_output[self._last_output_pos:]
                self._last_output_pos = len(current_output)
                
                # Split and process each line
                for line in new_output.splitlines():
                    if line.strip():  # Only process non-empty lines
                        self.add_entry(
                            line.strip(),
                            ObservabilityLevel.INFO,
                            metadata={"output_type": "stdout"}
                        )

    def get_new_output(self) -> str:
        """Get any new output since last check and process it."""
        if self._capture_active:
            self._process_current_output()
        with self._buffer_lock:
            current_output = self.output_buffer.getvalue()
            if len(current_output) > self._last_output_pos:
                new_output = current_output[self._last_output_pos:]
                self._last_output_pos = len(current_output)
                return new_output
        return ""

    def add_entry(
        self,
        message: str,
        level: ObservabilityLevel = ObservabilityLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add an observability entry"""
        # Clean up message by removing extra newlines and whitespace
        message = message.strip()
        if message:  # Only add non-empty messages
            entry = ObservabilityEntry(message, level, metadata=metadata)
            self.entries.append(entry)
            self._entry_queue.put(entry)

    def add_state_update(self, old_state: str, new_state: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a state transition entry"""
        message = f"Task state changed from {old_state} to {new_state}"
        self.add_entry(
            message,
            ObservabilityLevel.INFO,
            metadata={
                "state_transition": True,
                "old_state": old_state,
                "new_state": new_state,
                **(metadata or {})
            }
        )

    def add_execution_stats(self, stats: Dict[str, Any]):
        """Add execution statistics entry"""
        self.add_entry(
            "Execution statistics updated",
            ObservabilityLevel.INFO,
            metadata={"execution_stats": stats}
        )

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all observability entries"""
        return [entry.to_dict() for entry in self.entries]

    def get_new_entries(self) -> List[Dict[str, Any]]:
        """Get any new entries since last check"""
        entries = []
        while not self._entry_queue.empty():
            entry = self._entry_queue.get()
            entries.append(entry.to_dict())
        return entries

    async def monitor_execution(self, interval: float = 0.1):
        """Continuously monitor for new output and entries"""
        try:
            while self._capture_active:
                # Process any new output
                self._process_current_output()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(interval)

        except Exception as e:
            self.logger.error(f"Error in execution monitoring: {str(e)}")
            self.add_entry(
                f"Monitoring error: {str(e)}",
                ObservabilityLevel.ERROR
            )

    def __enter__(self):
        """Context manager entry"""
        self.start_capture()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_capture()
        if exc_type:
            self.add_entry(
                f"Error during execution: {str(exc_val)}",
                ObservabilityLevel.ERROR,
                metadata={"error_type": exc_type.__name__}
            ) 