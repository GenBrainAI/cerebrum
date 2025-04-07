"""
Tool request checker and fixer for CrewAI tools.

This module provides a tool interceptor that can fix common errors
in tool requests made by CrewAI agents.
"""

import logging
import json
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class CrewAIToolChecker:
    """
    Tool request checker and fixer for CrewAI tools.
    
    This class provides methods to check and fix common errors in tool 
    requests made by CrewAI agents.
    """
    
    @staticmethod
    def check_and_fix_serper_request(tool_name: str, args: Any) -> Dict[str, Any]:
        """
        Check and fix SerperDevTool and search tool requests.
        
        This method checks for common errors in SerperDevTool and other search
        tool requests and fixes them when possible.
        
        Args:
            tool_name: The name of the tool being called
            args: The arguments passed to the tool
            
        Returns:
            Dict[str, Any]: The fixed arguments, or the original args if no fix needed
        """
        fixed_args = args
        is_search_tool = "search" in tool_name.lower() or "serper" in tool_name.lower()
        
        # Don't process non-search tools
        if not is_search_tool:
            return fixed_args
            
        logger.info(f"Checking search tool request: {tool_name} with args: {args}")
        
        # Log the exact type and representation of args for debugging
        logger.info(f"Args type: {type(args)}, repr: {repr(args)}")
        
        # Case 0: Edge case - handle empty args
        if args is None or args == {}:
            logger.warning("Agent passed empty or None args to search tool")
            fixed_args = {"search_query": "general information", "kwargs": {}}
            logger.info(f"Fixed args: {fixed_args}")
            return fixed_args
        
        # Case 1: Agent passed the literal string "search_query" instead of using it as a parameter name
        if isinstance(args, str) and args.strip() == "search_query":
            logger.warning(f"Agent passed literal 'search_query' string as argument")
            # Fix by creating a generic search query
            fixed_args = {"search_query": "general information", "kwargs": {}}
            logger.info(f"Fixed args: {fixed_args}")
            return fixed_args
        
        # Case 1.1: Agent passed the literal string '"search_query"' (with quotes) - this is the specific error we're seeing
        if isinstance(args, str) and (args.strip() == '"search_query"' or args.strip() == "'search_query'"):
            logger.warning(f"Agent passed quoted 'search_query' string as argument")
            # Fix by creating a generic search query
            fixed_args = {"search_query": "general information", "kwargs": {}}
            logger.info(f"Fixed args: {fixed_args}")
            return fixed_args
            
        # Case 2: Agent used a dict with "search_query" as a value instead of a key
        if isinstance(args, dict) and "search_query" not in args:
            for key, value in args.items():
                if isinstance(value, str) and (value.strip() == "search_query" or value.strip() == '"search_query"' or value.strip() == "'search_query'"):
                    logger.warning(f"Agent used 'search_query' as a value for parameter {key}")
                    # Fix by using the parameter name as context for a new search query
                    fixed_args = {"search_query": f"information about {key}", "kwargs": {}}
                    logger.info(f"Fixed args: {fixed_args}")
                    return fixed_args
        
        # Case 3: Agent passed a dict but forgot to add search_query
        if isinstance(args, dict) and len(args) == 1 and "search_query" not in args:
            # If there's only one parameter and it's not search_query, use it as search_query
            key, value = next(iter(args.items()))
            if isinstance(value, str) and value.strip():
                logger.warning(f"Agent passed {key}={value} without search_query parameter")
                fixed_args = {"search_query": value, "kwargs": {}}
                logger.info(f"Fixed args: {fixed_args}")
                return fixed_args
                
        # Add kwargs if it's missing for SerperDevTool
        if isinstance(args, dict) and "search_query" in args and "kwargs" not in args:
            fixed_args = args.copy()
            fixed_args["kwargs"] = {}
            logger.info(f"Added empty kwargs parameter for search tool")
            return fixed_args
            
        # Return the original args if no fixes were needed or applicable
        return fixed_args 