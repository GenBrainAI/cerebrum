"""
Date and time utility functions for Cerebrum.

This module provides general-purpose tools for working with dates and times.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class DateTimeTools:
    """Tools for date and time operations."""
    
    def get_current_datetime(self) -> str:
        """Return the current date and time in a human-readable format.
        
        Returns:
            str: The current date and time in the format 'YYYY-MM-DD HH:MM:SS'
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_date_with_offset(self, days: int = 0, months: int = 0, years: int = 0) -> str:
        """Get a date offset from the current date.
        
        Args:
            days: Number of days to add (or subtract if negative)
            months: Number of months to add (or subtract if negative)
            years: Number of years to add (or subtract if negative)
            
        Returns:
            str: The calculated date in the format 'YYYY-MM-DD'
        """
        now = datetime.now()
        
        # Add days directly
        result_date = now + timedelta(days=days)
        
        # Add months and years by manipulating the year and month attributes
        year = result_date.year + years
        month = result_date.month + months
        
        # Adjust for month overflow
        year_adjustment = (month - 1) // 12
        month = ((month - 1) % 12) + 1
        year += year_adjustment
        
        # Create new date with adjusted year and month
        try:
            result_date = result_date.replace(year=year, month=month)
        except ValueError:
            # Handle case where the day doesn't exist in the target month (e.g., Feb 29)
            # Use the last day of the month instead
            if month == 2:
                last_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
            elif month in [4, 6, 9, 11]:
                last_day = 30
            else:
                last_day = 31
            result_date = result_date.replace(year=year, month=month, day=min(result_date.day, last_day))
        
        return result_date.strftime("%Y-%m-%d")
    
    def is_future_date(self, date_string: str) -> bool:
        """Check if a date is in the future.
        
        Args:
            date_string: Date string in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
            
        Returns:
            bool: True if the date is in the future, False otherwise
        """
        try:
            # Try to parse with time
            date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # Try to parse date only
                date_obj = datetime.strptime(date_string, "%Y-%m-%d")
            except ValueError:
                # If neither format works, return False
                return False
        
        # Compare with current date
        return date_obj > datetime.now()
    
    def format_datetime(self, date_obj: datetime, format_string: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format a datetime object using the specified format string.
        
        Args:
            date_obj: The datetime object to format
            format_string: The format string to use (default: '%Y-%m-%d %H:%M:%S')
            
        Returns:
            str: The formatted date string
        """
        return date_obj.strftime(format_string)

def get_current_datetime():
    """Return the current date and time in a human-readable format.
    
    Returns:
        str: The current date and time in the format 'YYYY-MM-DD HH:MM:SS'
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def is_future_date(date_string: str) -> bool:
    """Check if a date is in the future.
    
    Args:
        date_string: Date string in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
        
    Returns:
        bool: True if the date is in the future, False otherwise
    """
    try:
        # Try to parse with time
        date_obj = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            # Try to parse date only
            date_obj = datetime.strptime(date_string, "%Y-%m-%d")
        except ValueError:
            # If neither format works, return False
            return False
    
    # Compare with current date
    return date_obj > datetime.now()

def register_datetime_tools(catalog):
    """Register datetime tools with the tools catalog.
    
    Args:
        catalog: The tools catalog to register the tools with
        
    Returns:
        The list of registered tool names
    """
    # Create an instance of DateTimeTools
    datetime_tools = DateTimeTools()
    
    # Register the instance methods
    registered_names = catalog.register_instance(
        datetime_tools,
        "datetime_tools",
        exclude_base_methods=True,
        register_instance_itself=True
    )
    
    # Also register the standalone functions
    catalog.register_tool("datetime_tools.get_current_datetime", get_current_datetime)
    catalog.register_tool("datetime_tools.is_future_date", is_future_date)
    
    registered_names.append("datetime_tools.get_current_datetime")
    registered_names.append("datetime_tools.is_future_date")
    
    return registered_names
