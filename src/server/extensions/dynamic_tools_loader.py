from __future__ import annotations
import os
import sys
import inspect
import importlib.util
from typing import Any, Dict, List, Optional, Type, Union
from ..tools.tools_catalog import tools_catalog
from pathlib import Path


class DynamicToolsLoader:
    """Handles dynamic loading of tools from specified directories."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DynamicToolsLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not DynamicToolsLoader._initialized:
            self._loaded_modules: Dict[str, Any] = {}
            self.default_tools_dir = Path(__file__).parent.parent.parent.parent / "src" / "server" / "extensions" / "tools"
            DynamicToolsLoader._initialized = True

    def initialize(self):
        """Initialize the tools loader and load tools from the default directory."""
        try:
            return self.load_tools_from_directory(self.default_tools_dir)
        except Exception as e:
            print(f"Error initializing tools loader: {str(e)}")
            return []

    def load_tools_from_directory(self, directory_path: Union[str, Path]) -> List[str]:
        """Dynamically load all Python modules in the given directory and register their tools.
        
        Args:
            directory_path: The path to the directory containing tool files
            
        Returns:
            List of registered tool names
            
        Raises:
            FileNotFoundError: If the directory doesn't exist
        """
        directory_path = Path(directory_path)
        if not directory_path.exists():
            raise FileNotFoundError(f"The directory {directory_path} does not exist.")

        registered_tools = []
        
        # Add directory to Python path temporarily
        sys.path.append(str(directory_path))
        
        try:
            for file_path in directory_path.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                    
                module_name = file_path.stem
                try:
                    # Dynamically import the module
                    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
                    if not spec or not spec.loader:
                        print(f"Could not load spec for module {module_name}")
                        continue
                        
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    self._loaded_modules[module_name] = module

                    # Register tools from the module
                    for attr_name in dir(module):
                        # Skip private or built-in attributes
                        if attr_name.startswith("_") or attr_name in ("__class__", "__builtins__"):
                            continue
                            
                        attr = getattr(module, attr_name)
                        qualified_name = f"{module_name}.{attr_name}"
                        
                        try:
                            # Register based on type using the enhanced register_tool
                            if inspect.isclass(attr) or callable(attr) or isinstance(attr, object):
                                tools_catalog.register_tool(attr, qualified_name)
                                registered_tools.append(qualified_name)
                                
                        except Exception as e:
                            print(f"Error registering {qualified_name}: {str(e)}")
                            continue
                            
                    print(f"Loaded tools from: {module_name}")
                    
                except Exception as e:
                    print(f"Error loading module {module_name}: {str(e)}")
                    continue
                    
        finally:
            # Remove directory from Python path
            sys.path.remove(str(directory_path))
            
        return registered_tools

    def reload_module(self, module_name: str) -> List[str]:
        """Reload a previously loaded module and update its tools.
        
        Args:
            module_name: Name of the module to reload
            
        Returns:
            List of registered tool names
            
        Raises:
            KeyError: If module was not previously loaded
        """
        if module_name not in self._loaded_modules:
            raise KeyError(f"Module {module_name} was not previously loaded")
            
        module = self._loaded_modules[module_name]
        file_path = inspect.getfile(module)
        
        # Remove old registrations
        self._unregister_module(module_name)
        
        # Reload using load_tools_from_directory to ensure consistent loading
        return self.load_tools_from_directory(Path(file_path).parent)

    def _unregister_module(self, module_name: str):
        """Remove all tool registrations from a module.
        
        Args:
            module_name: Name of the module to unregister
        """
        # Remove all tools that start with module_name
        prefix = f"{module_name}."
        
        # Get all tools by type
        all_tools = tools_catalog.list_tools_by_type()
        
        # Remove from each type of storage
        for tool_type in ["functions", "classes", "instances"]:
            to_remove = [name for name in all_tools[tool_type] if name.startswith(prefix)]
            for name in to_remove:
                if tool_type == "functions" and name in tools_catalog._functions:
                    del tools_catalog._functions[name]
                elif tool_type == "classes" and name in tools_catalog._classes:
                    del tools_catalog._classes[name]
                elif tool_type == "instances" and name in tools_catalog._instances:
                    del tools_catalog._instances[name]
                    
        # Remove from metadata storage
        to_remove = [name for name in tools_catalog.list_tools() if name.startswith(prefix)]
        for name in to_remove:
            if name in tools_catalog._tools:
                del tools_catalog._tools[name]


# Create singleton instance
tools_loader = DynamicToolsLoader()
