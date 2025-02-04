"""A simple calculator tool for testing dynamic tool loading."""
from typing import Dict, Any, Optional

class Calculator:
    """A simple calculator tool that supports basic arithmetic operations."""
    
    def __init__(self):
        self.operations = {
            'add': self.add,
            'subtract': self.subtract,
            'multiply': self.multiply,
            'divide': self.divide
        }
    
    def add(self, a: float, b: float) -> float:
        """Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Sum of the numbers
        """
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """Subtract two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Difference between the numbers
        """
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Product of the numbers
        """
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """Divide two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Quotient of the numbers
            
        Raises:
            ValueError: If attempting to divide by zero
        """
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b

# Create an instance to be loaded by the dynamic tools loader
calculator = Calculator() 