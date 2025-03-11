"""Utility functions for tools catalog and tool filters."""

from typing import List, Set, Optional

def filter_container_tools(tools: List[str]) -> List[str]:
    """
    Filter out container class tools from a list of tools.
    
    This removes:
    1. Container classes like FileTool, SMSTool, etc.
    2. Tools without a dot in their name (indicating they are not method-specific)
    
    Args:
        tools: List of tool names from the catalog
        
    Returns:
        Filtered list with only method-specific tools
    """
    # List of known container tool names to filter out
    container_names = [
        "WebScraperTool", "FileTool", "MicroservicesTool", 
        "SMSTool", "GitHubTool", "URLTools", 
        "internal_file_tools", "internal_credentials_tools", 
        "internal_testing_tools", "internal_proxy_tools"
    ]
    
    # Filter out both:
    # 1. Known container tools by name
    # 2. Tools without a dot (traditional method)
    return [tool for tool in tools 
            if ('.' in tool) and 
            not any(tool == container for container in container_names)] 