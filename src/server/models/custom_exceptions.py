class Error(Exception):
    """Base class for other exceptions"""
    pass


class TasksManagerNotFoundError(Error):
    """Raised when the tasksmanager ID is not found"""

    def __init__(self, tasksmanager_id, message="TasksManager not found"):
        self.tasksmanager_id = tasksmanager_id
        self.message = f"{message}: {tasksmanager_id}"
        super().__init__(self.message)


class TaskNotFoundError(Error):
    """Raised when the task ID is not found"""

    def __init__(self, task_id, message="Task not found"):
        self.task_id = task_id
        self.message = f"{message}: {task_id}"
        super().__init__(self.message)


class UnsupportedTaskTypeError(Error):
    """Raised when the task type is unsupported or not found"""

    def __init__(self, task_type, message="Unsupported task type"):
        self.task_type = task_type
        self.message = f"{message}: {task_type}"
        super().__init__(self.message)


class TaskParamsNotFoundError(Error):
    """Raised when the task params is not found"""

    def __init__(self, task_type, message="Missing task parameters in the {task_type} task"):
        self.task_type = task_type
        self.message = message.format(task_type=task_type)
        super().__init__(self.message)


class TaskTypeNotFoundError(Error):
    """Raised when a task must initialize with a task type but it's not found"""

    def __init__(self, message="Task type not found. Task must initialize with task_type"):
        self.message = message
        super().__init__(self.message)


class ImportError(Error):
    """Raised when failing to import a model or module"""

    def __init__(self, model_provider, error):
        self.message = f"Failed to import {model_provider}: {error}"
        super().__init__(self.message)


class AttributeError(Error):
    """Raised when an expected attribute is missing from a module"""

    def __init__(self, model_provider, module_path, error):
        self.message = f"Module {module_path} does not define {model_provider}: {error}"
        super().__init__(self.message)


class TypeError(Error):
    """Raised when a model fails to initialize with provided parameters"""

    def __init__(self, model_provider, error):
        self.message = f"Error initializing {model_provider} with provided parameters: {error}"
        super().__init__(self.message)


class ExtractModeError(Error):
    """Raised when a model fails to initialize with provided parameters"""

    def __init__(self, mode, response):
        self.message = f"Error failed extract {mode} from llm response: {response}"
        super().__init__(self.message)
