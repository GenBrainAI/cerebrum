from __future__ import annotations
import sys
import inspect
import importlib.util
from typing import Any, Dict, List, Type, Union, get_origin, get_args
from pathlib import Path
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from uuid import uuid4
import os
import types

from ..models.tools_descriptors import ToolType
from ..tools.tools_catalog import ToolsCatalog, tools_catalog
from ..models.tools_descriptors import ParameterInfo, ToolMetadata, ReturnInfo

# Create singleton instance of ToolsCatalog and initialize it
tools_catalog = ToolsCatalog()
tools_catalog._initialize_default_tools()  # Ensure default tools are loaded
print("\n🔧 Tools catalog initialized with tools:", tools_catalog.list_tools())

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

def is_type_hint(obj: Any) -> bool:
    """Check if an object is a type hint."""
    # Check for typing module objects
    if hasattr(obj, '__module__') and obj.__module__ == 'typing':
        return True
    # Check for _SpecialForm (Any, Union, etc)
    if hasattr(obj, '_name') and hasattr(obj, '_special'):
        return True
    # Check for GenericAlias (List[str], Dict[str, int], etc)
    if hasattr(obj, '__origin__'):
        return True
    return False

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
            print(f"\n📂 Default tools directory: {self.default_tools_dir}")

    @property
    def tools_catalog(self) -> ToolsCatalog:
        """Get the global tools catalog instance."""
        return tools_catalog

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
            print("\n🚀 Initializing dynamic tools loader...")
            
            # Ensure tools catalog is initialized with default tools
            if not tools_catalog.DEFAULT_TOOLS:
                print("📦 Initializing default tools in catalog...")
                tools_catalog._initialize_default_tools()
            
            # Load tools from directory
            print("\n📂 Loading tools from directory...")
            tools = self.load_tools_from_directory(self.default_tools_dir)
            print(f"✅ Loaded {len(tools)} tools from directory")
            
            # Start watching for changes
            print("\n👀 Starting file watcher...")
            self.start_file_watching()
            print("✅ File watcher started")
            
            # Print final tool count
            all_tools = tools_catalog.list_tools()
            print(f"\n📊 Total tools available: {len(all_tools)}")
            print("Tool categories:")
            categories = {}
            for tool in all_tools:
                category = tool.split('.')[0] if '.' in tool else 'root'
                categories[category] = categories.get(category, 0) + 1
            for category, count in categories.items():
                print(f"  - {category}: {count} tools")
            
            return tools
            
        except Exception as e:
            print(f"\n❌ Error initializing tools loader: {str(e)}")
            traceback.print_exc()
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

    def _register_function(self, func, module_name: str, func_name: str, registered_tools: List[str]):
        """Register a function with proper metadata."""
        try:
            qualified_name = f"{module_name}.{func_name}"
            print(f"\n🔧 Registering function: {qualified_name}")
            
            # Skip if it's a type hint
            if is_type_hint(func):
                print("   ⚠️ Skipping type hint")
                return
                
            # Skip if not callable
            if not callable(func):
                print("   ⚠️ Skipping non-callable object")
                return
            
            docstring = inspect.getdoc(func) or ""
            if docstring:
                print(f"   📝 Docstring: {docstring.split()[0]}...")
            
            # Get signature
            sig = inspect.signature(func)
            print("   📋 Parameters:")
            parameters = []
            for param_name, param in sig.parameters.items():
                param_type = self._type_to_string(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                print(f"      - {param_name}: {param_type}")
                parameters.append({
                    "name": param_name,
                    "type": param_type,
                    "required": param.default == inspect.Parameter.empty,
                    "description": f"Parameter {param_name}",
                    "default": None if param.default == inspect.Parameter.empty else param.default
                })
            
            # Get return type
            return_type = self._type_to_string(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else "Any"
            print(f"   📤 Return type: {return_type}")
            
            # Create metadata
            metadata = {
                "tool_type": ToolType.PYTHON_FUNCTION,
                "description": docstring,
                "parameters": parameters,
                "original_obj": func,
                "return_type": return_type,
                "return_description": "Return value",
                "async_tool": inspect.iscoroutinefunction(func)
            }
            
            # Register with catalog
            tools_catalog.register_tool(qualified_name, metadata)
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
            
            # Skip if it's a type hint
            if is_type_hint(cls):
                print("   ⚠️ Skipping type hint")
                return
            
            docstring = inspect.getdoc(cls) or ""
            if docstring:
                print(f"   📝 Class docstring: {docstring.split()[0]}...")
            
            # Create instance
            try:
                print("   🔨 Creating instance...")
                instance = cls()
                print("   ✅ Instance created")
            except Exception as e:
                print(f"   ❌ Error instantiating class {qualified_name}: {str(e)}")
                return
            
            # Create class metadata
            class_metadata = {
                "tool_type": ToolType.CLASS_METHOD,
                "description": docstring,
                "parameters": [],
                "original_obj": cls,
                "return_type": "Any",
                "return_description": "Class instance",
                "async_tool": False
            }
            
            # Register class with catalog
            tools_catalog.register_tool(qualified_name, class_metadata)
            registered_tools.append(qualified_name)
            print(f"✅ Registered class: {qualified_name}")
            
            # Register instance methods
            print("\n   📋 Registering methods:")
            for method_name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
                if method_name.startswith('_'):
                    continue
                
                method_qualified_name = f"{qualified_name}.{method_name}"
                
                try:
                    sig = inspect.signature(method)
                    method_docstring = inspect.getdoc(method) or ""
                    if method_docstring:
                        print(f"      - Method: {method_name}")
                        print(f"        📝 Method docstring: {method_docstring.split()[0]}...")
                    
                    # Get parameters
                    print("        📋 Parameters:")
                    parameters = []
                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                        param_type = self._type_to_string(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                        print(f"           - {param_name}: {param_type}")
                        parameters.append({
                            "name": param_name,
                            "type": param_type,
                            "required": param.default == inspect.Parameter.empty,
                            "description": f"Parameter {param_name}",
                            "default": None if param.default == inspect.Parameter.empty else param.default
                        })
                    
                    # Get return type
                    return_type = self._type_to_string(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else "Any"
                    print(f"        📤 Return type: {return_type}")
                    
                    # Create method metadata
                    method_metadata = {
                        "tool_type": ToolType.CLASS_METHOD,
                        "description": method_docstring,
                        "parameters": parameters,
                        "original_obj": method,
                        "return_type": return_type,
                        "return_description": "Return value",
                        "async_tool": inspect.iscoroutinefunction(method)
                    }
                    
                    # Register method with catalog
                    tools_catalog.register_tool(method_qualified_name, method_metadata)
                    registered_tools.append(method_qualified_name)
                    print(f"        ✅ Registered method: {method_qualified_name}")
                    
                except Exception as e:
                    print(f"        ❌ Error registering method {method_qualified_name}: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"❌ Error registering class {qualified_name}: {str(e)}")
            import traceback
            traceback.print_exc()

    def _register_instance(self, instance: Any, module_name: str, instance_name: str, registered_tools: List[str]):
        """Register an instance with proper metadata."""
        try:
            qualified_name = f"{module_name}.{instance_name}"
            
            # Skip if it's a type hint
            if is_type_hint(instance):
                print(f"   ⚠️ Skipping type hint: {qualified_name}")
                return
                
            # Skip if not an object instance
            if isinstance(instance, (type, types.ModuleType)):
                print(f"   ⚠️ Skipping non-instance: {qualified_name}")
                return
            
            print(f"\n🔧 Registering instance: {qualified_name}")
            docstring = inspect.getdoc(instance) or ""
            if docstring:
                print(f"   📝 Instance docstring: {docstring.split()[0]}...")
            
            # Create instance metadata
            instance_metadata = {
                "tool_type": ToolType.CLASS_METHOD,
                "description": docstring,
                "parameters": [],
                "original_obj": instance,
                "return_type": "Any",
                "return_description": "Instance",
                "async_tool": False
            }
            
            # Register instance with catalog
            tools_catalog.register_tool(qualified_name, instance_metadata)
            registered_tools.append(qualified_name)
            
            # Register instance methods
            print("   📋 Registering methods:")
            for method_name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
                if method_name.startswith('_'):
                    continue
                
                method_qualified_name = f"{qualified_name}.{method_name}"
                
                try:
                    sig = inspect.signature(method)
                    method_docstring = inspect.getdoc(method) or ""
                    if method_docstring:
                        print(f"      - Method: {method_name}")
                        print(f"        📝 Method docstring: {method_docstring.split()[0]}...")
                    
                    # Get parameters
                    print("        📋 Parameters:")
                    parameters = []
                    for param_name, param in sig.parameters.items():
                        if param_name == 'self':
                            continue
                        param_type = self._type_to_string(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                        print(f"           - {param_name}: {param_type}")
                        parameters.append({
                            "name": param_name,
                            "type": param_type,
                            "required": param.default == inspect.Parameter.empty,
                            "description": f"Parameter {param_name}",
                            "default": None if param.default == inspect.Parameter.empty else param.default
                        })
                    
                    # Get return type
                    return_type = self._type_to_string(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else "Any"
                    print(f"        📤 Return type: {return_type}")
                    
                    # Create method metadata
                    method_metadata = {
                        "tool_type": ToolType.CLASS_METHOD,
                        "description": method_docstring,
                        "parameters": parameters,
                        "original_obj": method,
                        "return_type": return_type,
                        "return_description": "Return value",
                        "async_tool": inspect.iscoroutinefunction(method)
                    }
                    
                    # Register method with catalog
                    tools_catalog.register_tool(method_qualified_name, method_metadata)
                    registered_tools.append(method_qualified_name)
                    print(f"        ✅ Registered method: {method_qualified_name}")
                    
                except Exception as e:
                    print(f"        ❌ Error registering method {method_qualified_name}: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"❌ Error registering instance {qualified_name}: {str(e)}")
            import traceback
            traceback.print_exc()

    def load_tools_from_directory(self, directory_path: Union[str, Path]) -> List[str]:
        """Load tools from a directory."""
        try:
            print(f"\n📂 Loading tools from directory: {directory_path}")
            directory_path = Path(directory_path)
            registered_tools = []
            
            # Add directory to Python path
            print("   Adding directory to Python path...")
            directory_str = str(directory_path)
            if directory_str not in sys.path:
                sys.path.insert(0, directory_str)
            
            # Create __init__.py if it doesn't exist
            print("   Creating __init__.py file...")
            init_file = directory_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
            
            # Create package name from directory name
            package_name = directory_path.name
            
            # Load __init__.py first to establish package
            try:
                spec = importlib.util.spec_from_file_location(package_name, init_file)
                if spec is not None and spec.loader is not None:
                    package = importlib.util.module_from_spec(spec)
                    sys.modules[package_name] = package
                    spec.loader.exec_module(package)
            except Exception as e:
                print(f"   ⚠️ Warning: Could not load __init__.py: {str(e)}")
            
            print("\n   Scanning for Python files...")
            for file_path in directory_path.glob("*.py"):
                if file_path.name == "__init__.py":
                    continue
                    
                print(f"\n   📄 Processing file: {file_path.name}")
                module_name = f"{package_name}.{file_path.stem}"
                
                try:
                    print(f"      Importing module: {module_name}")
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec is None or spec.loader is None:
                        print(f"      ❌ Failed to create module spec for {module_name}")
                        continue
                        
                    module = importlib.util.module_from_spec(spec)
                    module.__package__ = package_name
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    self._loaded_modules[module_name] = module
                    print(f"      ✅ Module imported: {module_name}")
                    
                    print("      🔍 Scanning module for tools...")
                    for name, obj in inspect.getmembers(module):
                        if name.startswith('_'):
                            continue
                            
                        print(f"         - Found attribute: {name}")
                        if inspect.isfunction(obj):
                            print(f"           Registering function: {name}")
                            self._register_function(obj, file_path.stem, name, registered_tools)
                        elif inspect.isclass(obj):
                            print(f"           Registering class: {name}")
                            self._register_class(obj, file_path.stem, name, registered_tools)
                        elif not inspect.ismodule(obj):
                            print(f"           Registering instance: {name}")
                            self._register_instance(obj, file_path.stem, name, registered_tools)
                            
                except Exception as e:
                    print(f"      ❌ Error loading module {module_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            print("\n   Cleaning up Python path...")
            if directory_str in sys.path:
                sys.path.remove(directory_str)
            
            print(f"\n✅ Registered {len(registered_tools)} tools")
            return registered_tools
            
        except Exception as e:
            print(f"❌ Error loading tools from directory: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

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
        
        # Find the fully qualified module name
        full_module_name = None
        for loaded_name in self._loaded_modules:
            if loaded_name.endswith(f".{module_name}") or loaded_name == module_name:
                full_module_name = loaded_name
                break
        
        if not full_module_name:
            print(f"❌ Module {module_name} not found in loaded modules")
            return []
            
        # Unregister existing tools
        self._unregister_module(module_name)
        
        # Get module file path
        module = self._loaded_modules[full_module_name]
        file_path = inspect.getfile(module)
        directory_path = str(Path(file_path).parent)
        package_name = Path(directory_path).name
        
        registered_tools = []
        
        # Add directory to Python path temporarily
        print(f"   Adding directory to path: {directory_path}")
        sys.path.insert(0, directory_path)
        
        try:
            # Reload the module
            print(f"   📦 Loading module spec from: {file_path}")
            spec = importlib.util.spec_from_file_location(full_module_name, file_path)
            if not spec or not spec.loader:
                print(f"   ❌ Could not load spec for module {full_module_name}")
                return []
                
            module = importlib.util.module_from_spec(spec)
            module.__package__ = package_name
            sys.modules[full_module_name] = module
            spec.loader.exec_module(module)
            self._loaded_modules[full_module_name] = module
            print(f"   ✅ Module reloaded successfully")
            
            # Re-register tools
            print("   🔍 Scanning for tools...")
            for name, obj in inspect.getmembers(module):
                if name.startswith('_'):
                    continue
                    
                print(f"      - Found attribute: {name}")
                if inspect.isfunction(obj):
                    print(f"        Registering function: {name}")
                    self._register_function(obj, module_name, name, registered_tools)
                elif inspect.isclass(obj):
                    print(f"        Registering class: {name}")
                    self._register_class(obj, module_name, name, registered_tools)
                elif not inspect.ismodule(obj):
                    print(f"        Registering instance: {name}")
                    self._register_instance(obj, module_name, name, registered_tools)
                    
        except Exception as e:
            print(f"❌ Error reloading module {full_module_name}: {str(e)}")
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
