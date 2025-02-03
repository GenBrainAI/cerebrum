from __future__ import annotations
import os
import sys
import inspect
import importlib.util
from typing import Any, Dict, List, Optional, Type, Union
from pathlib import Path
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from uuid import uuid4

from ..tools.tools_catalog import ToolsCatalog, tools_catalog
from ..models.tools_descriptors import ParameterInfo, ToolMetadata, ToolType, ReturnInfo
from ..persistence.in_memory_persistence import InMemoryPersistenceModel
from ..persistence.persistence_model_factory import PersistenceModelFactory

# Create singleton instance of ToolsCatalog
tools_catalog = ToolsCatalog()

class ToolsDirectoryHandler(FileSystemEventHandler):
    """Handler for file system events in the tools directory."""
    
    def __init__(self, tools_loader: DynamicToolsLoader):
        self.tools_loader = tools_loader
        self._last_reload_time = 0
        self._debounce_seconds = 1  # Debounce time to prevent multiple reloads

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            print(f"\n🔄 File modified: {event.src_path}")
            current_time = time.time()
            if current_time - self._last_reload_time > self._debounce_seconds:
                self._last_reload_time = current_time
                print("🔄 Reloading tools catalog...")
                self.tools_loader.reload_all_tools()
                print("✅ Tools catalog reloaded")

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            print(f"\n📝 New file created: {event.src_path}")
            current_time = time.time()
            if current_time - self._last_reload_time > self._debounce_seconds:
                self._last_reload_time = current_time
                print("🔄 Reloading tools catalog...")
                self.tools_loader.reload_all_tools()
                print("✅ Tools catalog reloaded")

    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith('.py'):
            print(f"\n🗑️ File deleted: {event.src_path}")
            current_time = time.time()
            if current_time - self._last_reload_time > self._debounce_seconds:
                self._last_reload_time = current_time
                print("🔄 Reloading tools catalog...")
                self.tools_loader.reload_all_tools()
                print("✅ Tools catalog reloaded")

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
            self.default_tools_dir = Path(__file__).parent.parent.parent / "tools"
            self._observer = None
            DynamicToolsLoader._initialized = True

    def start_file_watching(self):
        """Start watching the tools directory for changes."""
        if self._observer is None:
            self._observer = Observer()
            event_handler = ToolsDirectoryHandler(self)
            self._observer.schedule(event_handler, str(self.default_tools_dir), recursive=False)
            self._observer.start()
            print(f"Started watching directory: {self.default_tools_dir}")

    def stop_file_watching(self):
        """Stop watching the tools directory."""
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            print("Stopped watching tools directory")

    def reload_all_tools(self) -> List[str]:
        """Reload all tools and return the list of registered tools."""
        try:
            print("\n🔄 Starting tools reload process...")
            print("1. Clearing existing tool registrations...")
            
            # Clear all existing tool registrations
            for module_name in list(self._loaded_modules.keys()):
                try:
                    print(f"   - Unregistering module: {module_name}")
                    self._unregister_module(module_name)
                except Exception as e:
                    print(f"   ❌ Error unregistering module {module_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
            self._loaded_modules.clear()
            print("✅ Cleared existing registrations")
            
            # Load all tools again
            print("\n2. Loading tools from directory...")
            tools = self.load_tools_from_directory(self.default_tools_dir)
            print(f"✅ Loaded {len(tools)} tools")
            
            print("\n✅ Tools reload completed")
            return tools
            
        except Exception as e:
            print(f"\n❌ Error in reload_all_tools: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def initialize(self):
        """Initialize the tools loader and start watching for changes."""
        try:
            # Load tools from directory
            tools = self.load_tools_from_directory(self.default_tools_dir)
            
            # Start watching for changes
            self.start_file_watching()
            
            return tools
        except Exception as e:
            print(f"Error initializing tools loader: {str(e)}")
            return []

    def _type_to_string(self, type_hint: Any) -> str:
        """Convert a type hint to a string representation."""
        if isinstance(type_hint, type):
            return type_hint.__name__
        if hasattr(type_hint, "__origin__"):
            origin = type_hint.__origin__.__name__
            args = ", ".join(self._type_to_string(arg) for arg in type_hint.__args__)
            return f"{origin}[{args}]"
        return str(type_hint)

    def _register_function(self, func: Any, module_name: str, func_name: str, registered_tools: List[str]):
        """Register a function with proper metadata."""
        try:
            qualified_name = f"{module_name}.{func_name}"
            print(f"\n🔧 Registering function: {qualified_name}")
            
            sig = inspect.signature(func)
            docstring = inspect.getdoc(func) or ""
            print(f"   📝 Docstring: {docstring.split()[0]}...")
            
            # Extract parameters
            parameters = []
            print("   📋 Parameters:")
            for param_name, param in sig.parameters.items():
                param_type = self._type_to_string(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                default = param.default if param.default != inspect.Parameter.empty else None
                print(f"      - {param_name}: {param_type}")
                parameters.append(ParameterInfo(
                    name=param_name,
                    type_hint=param_type,
                    description=f"Parameter {param_name}",
                    required=param.default == inspect.Parameter.empty,
                    default=default
                ))
            
            # Get return type
            return_type = self._type_to_string(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else "Any"
            print(f"   📤 Return type: {return_type}")
            
            # Create metadata
            metadata = ToolMetadata(
                name=qualified_name,
                description=docstring,
                tool_type=ToolType.PYTHON_FUNCTION,
                parameters=parameters,
                original_obj=func,
                async_tool=inspect.iscoroutinefunction(func),
                returns=ReturnInfo(
                    type_hint=return_type,
                    description="Return value"
                )
            )
            
            # Register the function
            tools_catalog._tools[qualified_name] = metadata
            tools_catalog._tool_instances[qualified_name] = func
            registered_tools.append(qualified_name)
            print(f"✅ Successfully registered function: {qualified_name}")
            
        except Exception as e:
            print(f"❌ Error registering function {qualified_name}: {str(e)}")
            import traceback
            traceback.print_exc()

    def _register_class(self, cls: Type, module_name: str, class_name: str, registered_tools: List[str]):
        """Register a class with proper metadata."""
        try:
            qualified_name = f"{module_name}.{class_name}"
            print(f"\n🔧 Registering class: {qualified_name}")
            docstring = inspect.getdoc(cls) or ""
            print(f"   📝 Class docstring: {docstring.split()[0]}...")
            
            # Create instance
            try:
                print("   🔨 Creating instance...")
                instance = cls()
                print("   ✅ Instance created")
            except Exception as e:
                print(f"   ❌ Error instantiating class {qualified_name}: {str(e)}")
                return
            
            # Register the class itself
            class_metadata = ToolMetadata(
                name=qualified_name,
                description=docstring,
                tool_type=ToolType.CLASS_METHOD,
                parameters=[],
                original_obj=cls,
                async_tool=False,
                returns=ReturnInfo(
                    type_hint="Any",
                    description="Class instance"
                )
            )
            tools_catalog._tools[qualified_name] = class_metadata
            tools_catalog._tool_instances[qualified_name] = cls
            registered_tools.append(qualified_name)
            print(f"✅ Registered class: {qualified_name}")
            
            # Register instance methods
            print("\n   📋 Registering methods:")
            for method_name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
                if method_name.startswith('_'):
                    continue
                
                print(f"      - Method: {method_name}")
                method_qualified_name = f"{qualified_name}.{method_name}"
                sig = inspect.signature(method)
                method_docstring = inspect.getdoc(method) or ""
                print(f"        📝 Method docstring: {method_docstring.split()[0]}...")
                
                # Extract parameters
                parameters = []
                print("        📋 Parameters:")
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    param_type = self._type_to_string(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                    print(f"           - {param_name}: {param_type}")
                    parameters.append(ParameterInfo(
                        name=param_name,
                        type_hint=param_type,
                        description=f"Parameter {param_name}",
                        required=param.default == inspect.Parameter.empty
                    ))
                
                # Get return type
                return_type = self._type_to_string(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else "Any"
                print(f"        📤 Return type: {return_type}")
                
                # Create metadata
                metadata = ToolMetadata(
                    name=method_qualified_name,
                    description=method_docstring,
                    tool_type=ToolType.CLASS_METHOD,
                    parameters=parameters,
                    original_obj=method,
                    async_tool=inspect.iscoroutinefunction(method),
                    returns=ReturnInfo(
                        type_hint=return_type,
                        description="Return value"
                    )
                )
                
                # Register the method
                tools_catalog._tools[method_qualified_name] = metadata
                tools_catalog._tool_instances[method_qualified_name] = method
                registered_tools.append(method_qualified_name)
                print(f"        ✅ Registered method: {method_qualified_name}")
            
        except Exception as e:
            print(f"❌ Error registering class {qualified_name}: {str(e)}")
            import traceback
            traceback.print_exc()

    def _register_instance(self, instance: Any, module_name: str, instance_name: str, registered_tools: List[str]):
        """Register an instance with proper metadata."""
        try:
            qualified_name = f"{module_name}.{instance_name}"
            docstring = inspect.getdoc(instance) or ""
            
            # Register the instance itself
            instance_metadata = ToolMetadata(
                name=qualified_name,
                description=docstring,
                tool_type=ToolType.CLASS_METHOD,
                parameters=[],
                original_obj=instance,
                async_tool=False,
                returns=ReturnInfo(
                    type_hint="Any",
                    description="Instance"
                )
            )
            tools_catalog._tools[qualified_name] = instance_metadata
            tools_catalog._tool_instances[qualified_name] = instance
            registered_tools.append(qualified_name)
            
            # Register instance methods
            for method_name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
                if method_name.startswith('_'):
                    continue
                
                method_qualified_name = f"{qualified_name}.{method_name}"
                sig = inspect.signature(method)
                method_docstring = inspect.getdoc(method) or ""
                
                # Extract parameters
                parameters = []
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                    param_type = self._type_to_string(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                    parameters.append(ParameterInfo(
                        name=param_name,
                        type_hint=param_type,
                        description=f"Parameter {param_name}",
                        required=param.default == inspect.Parameter.empty
                    ))
                
                # Get return type
                return_type = self._type_to_string(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else "Any"
                
                # Create metadata
                metadata = ToolMetadata(
                    name=method_qualified_name,
                    description=method_docstring,
                    tool_type=ToolType.CLASS_METHOD,
                    parameters=parameters,
                    original_obj=method,
                    async_tool=inspect.iscoroutinefunction(method),
                    returns=ReturnInfo(
                        type_hint=return_type,
                        description="Return value"
                    )
                )
                
                # Register the method
                tools_catalog._tools[method_qualified_name] = metadata
                tools_catalog._tool_instances[method_qualified_name] = method
                registered_tools.append(method_qualified_name)
            
        except Exception as e:
            print(f"Error registering instance {qualified_name}: {str(e)}")
            import traceback
            traceback.print_exc()

    def load_tools_from_directory(self, directory_path: Union[str, Path]) -> List[str]:
        """Dynamically load all Python modules in the given directory and register their tools."""
        directory_path = Path(directory_path)
        print(f"\n📂 Loading tools from directory: {directory_path}")
        
        if not directory_path.exists():
            print(f"❌ Directory does not exist: {directory_path}")
            raise FileNotFoundError(f"The directory {directory_path} does not exist.")

        registered_tools = []
        
        # Add directory to Python path temporarily
        print("   Adding directory to Python path...")
        sys.path.insert(0, str(directory_path))
        
        try:
            # Create an empty __init__.py if it doesn't exist
            init_file = directory_path / "__init__.py"
            if not init_file.exists():
                print("   Creating __init__.py file...")
                init_file.touch()
            
            print("\n   Scanning for Python files...")
            for file_path in directory_path.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                    
                module_name = file_path.stem
                print(f"\n   📄 Processing file: {file_path.name}")
                try:
                    # Dynamically import the module
                    print(f"      Importing module: {module_name}")
                    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
                    if not spec or not spec.loader:
                        print(f"      ❌ Could not load spec for module {module_name}")
                        continue
                        
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    self._loaded_modules[module_name] = module
                    print(f"      ✅ Module imported: {module_name}")

                    # Register tools from the module
                    print(f"      🔍 Scanning module for tools...")
                    for attr_name in dir(module):
                        if attr_name.startswith("_"):
                            continue
                            
                        attr = getattr(module, attr_name)
                        print(f"         - Found attribute: {attr_name}")
                        
                        try:
                            # Register based on type
                            if not inspect.isclass(attr) and not inspect.isfunction(attr) and hasattr(attr, '__dict__'):
                                print(f"           Registering instance: {attr_name}")
                                self._register_instance(attr, module_name, attr_name, registered_tools)
                            elif inspect.isclass(attr):
                                print(f"           Registering class: {attr_name}")
                                self._register_class(attr, module_name, attr_name, registered_tools)
                            elif inspect.isfunction(attr):
                                print(f"           Registering function: {attr_name}")
                                self._register_function(attr, module_name, attr_name, registered_tools)
                                
                        except Exception as e:
                            print(f"           ❌ Error registering {module_name}.{attr_name}: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            
                except Exception as e:
                    print(f"      ❌ Error loading module {module_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
        finally:
            # Remove directory from Python path
            print("\n   Cleaning up Python path...")
            sys.path.remove(str(directory_path))
            
        print(f"\n✅ Registered {len(registered_tools)} tools")
        return registered_tools

    def _unregister_module(self, module_name: str):
        """Unregister all tools from a module."""
        print(f"\n🗑️ Unregistering module: {module_name}")
        print(f"   Current tools in catalog: {list(tools_catalog._tools.keys())}")
        
        # Remove tools from catalog
        tools_to_remove = []
        for tool_name in list(tools_catalog._tools.keys()):
            if tool_name.startswith(module_name + "."):
                tools_to_remove.append(tool_name)
                
        print(f"   Tools to remove: {tools_to_remove}")
        
        for tool_name in tools_to_remove:
            try:
                print(f"   - Removing {tool_name}")
                del tools_catalog._tools[tool_name]
                if tool_name in tools_catalog._tool_instances:
                    del tools_catalog._tool_instances[tool_name]
                print(f"     ✅ Removed successfully")
            except Exception as e:
                print(f"     ❌ Error removing {tool_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                
        print(f"   Remaining tools in catalog: {list(tools_catalog._tools.keys())}")

    def reload_module(self, module_name: str) -> List[str]:
        """Reload a specific module and its tools."""
        print(f"\n🔄 Reloading module: {module_name}")
        
        # Unregister existing tools
        self._unregister_module(module_name)
        
        # Get module file path
        if module_name not in self._loaded_modules:
            print(f"❌ Module {module_name} not found in loaded modules")
            return []
            
        module = self._loaded_modules[module_name]
        file_path = inspect.getfile(module)
        directory_path = str(Path(file_path).parent)
        
        registered_tools = []
        
        # Add directory to Python path temporarily
        print(f"   Adding directory to path: {directory_path}")
        sys.path.insert(0, directory_path)
        
        try:
            # Reload the module
            print(f"   📦 Loading module spec from: {file_path}")
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                print(f"   ❌ Could not load spec for module {module_name}")
                return []
                
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            self._loaded_modules[module_name] = module
            print(f"   ✅ Module reloaded successfully")
            
            # Re-register tools
            print("   🔍 Scanning for tools...")
            for attr_name in dir(module):
                if attr_name.startswith("_"):
                    continue
                    
                attr = getattr(module, attr_name)
                print(f"      - Found attribute: {attr_name}")
                
                try:
                    # Register based on type
                    if not inspect.isclass(attr) and not inspect.isfunction(attr) and hasattr(attr, '__dict__'):
                        print(f"        Registering instance: {attr_name}")
                        self._register_instance(attr, module_name, attr_name, registered_tools)
                    elif inspect.isclass(attr):
                        print(f"        Registering class: {attr_name}")
                        self._register_class(attr, module_name, attr_name, registered_tools)
                    elif inspect.isfunction(attr):
                        print(f"        Registering function: {attr_name}")
                        self._register_function(attr, module_name, attr_name, registered_tools)
                        
                except Exception as e:
                    print(f"        ❌ Error registering {module_name}.{attr_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
        except Exception as e:
            print(f"❌ Error reloading module {module_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Remove directory from Python path
            print("   🧹 Cleaning up Python path")
            sys.path.remove(directory_path)
            
        print(f"✅ Module reload complete. Registered {len(registered_tools)} tools")
        return registered_tools


# Create singleton instance
tools_loader = DynamicToolsLoader()
