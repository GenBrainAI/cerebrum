from typing import Dict, List, Type, Any
import inspect
import docstring_parser
from src.server.models.tools_desrriptors import DocstringInfo, ParameterInfo, ReturnInfo

def parse_docstring(obj: Any) -> DocstringInfo:
    """
    Parse a function or method's docstring to extract complete information.
    
    Args:
        obj: The function or method to parse
        
    Returns:
        DocstringInfo containing the parsed information
        
    Example:
        >>> def example_func(param1: str, param2: int = 0) -> bool:
        ...     '''
        ...     Example function description.
        ...     
        ...     Args:
        ...         param1: First parameter description
        ...         param2: Second parameter description
        ...     
        ...     Returns:
        ...         Description of return value
        ...     '''
        ...     pass
        >>> info = parse_docstring(example_func)
    """
    # Get the docstring and type hints
    docstring = obj.__doc__ or ""
    type_hints = get_type_hints(obj)
    
    # Parse with docstring_parser
    parsed = docstring_parser.parse(docstring)
    
    # Get base description
    description = parsed.short_description
    if parsed.long_description:
        description += "\n\n" + parsed.long_description
    
    # Get signature for default values
    signature = inspect.signature(obj)
    
    # Process parameters
    parameters = []
    for param_name, param in signature.parameters.items():
        if param_name == 'self':  # Skip self parameter for methods
            continue
            
        # Get type hint
        param_type = type_hints.get(param_name)
        
        # Get docstring description
        param_doc = next((p.description for p in parsed.params if p.arg_name == param_name), "")
        
        # Get default value and determine if required
        has_default = param.default != inspect.Parameter.empty
        default_value = param.default if has_default else None
        
        param_info = ParameterInfo(
            name=param_name,
            type_hint=param_type,
            description=param_doc,
            default=default_value,
            required=not has_default
        )
        parameters.append(param_info)
    
    # Process return info
    return_type = type_hints.get('return')
    return_desc = parsed.returns.description if parsed.returns else ""
    
    returns = ReturnInfo(
        type_hint=return_type,
        description=return_desc
    )
    
    return DocstringInfo(
        description=description,
        parameters=parameters,
        returns=returns
    )

def extract_class_methods_info(cls: Type) -> Dict[str, DocstringInfo]:
    """
    Extract docstring information for all public methods of a class.
    
    Args:
        cls: The class to analyze
        
    Returns:
        Dictionary mapping method names to their DocstringInfo
    """
    method_info = {}
    
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('_'):  # Only process public methods
            method_info[name] = parse_docstring(method)
            
    return method_info

def validate_docstring_completeness(info: DocstringInfo) -> List[str]:
    """
    Validate that a docstring has all required components.
    
    Args:
        info: DocstringInfo to validate
        
    Returns:
        List of validation warnings/errors
    """
    warnings = []
    
    if not info.description:
        warnings.append("Missing or empty description")
        
    for param in info.parameters:
        if not param.description:
            warnings.append(f"Missing description for parameter {param.name}")
        if param.type_hint is None:
            warnings.append(f"Missing type hint for parameter {param.name}")
            
    if not info.returns.description:
        warnings.append("Missing return value description")
    if info.returns.type_hint is None:
        warnings.append("Missing return type hint")
        
    return warnings

# Example usage and testing
if __name__ == "__main__":
    # Example function with complete docstring
    def example_function(text: str, repeat: int = 1) -> str:
        """
        Repeat the given text a specified number of times.
        
        Args:
            text: The text to repeat
            repeat: Number of times to repeat the text
            
        Returns:
            The repeated text string
        """
        return text * repeat
    
    # Parse and validate
    info = parse_docstring(example_function)
    warnings = validate_docstring_completeness(info)
    
    # Print results
    print("Description:", info.description)
    print("\nParameters:")
    for param in info.parameters:
        print(f"  {param.name}: {param.description} (type: {param.type_hint}, required: {param.required})")
    print("\nReturns:", info.returns.description)
    print("\nValidation warnings:", warnings)
