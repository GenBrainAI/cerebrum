"""Unit tests for the PyExec tool."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.server.tools.py_exec import PyExec

class TestPyExec(unittest.TestCase):
    """Test cases for the PyExec tool."""
    
    def setUp(self):
        """Set up test environment."""
        self.py_exec = PyExec()
        
        # Create a temporary script file for testing
        self.temp_script = tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False)
        self.temp_script.write('import sys\nprint("Hello, World!")\nprint(f"Arguments: {sys.argv[1:]}")')
        self.temp_script.close()
        
        # Create a calculator script for testing
        self.calculator_script = tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False)
        self.calculator_script.write('''
import sys

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        print("Error: Division by zero", file=sys.stderr)
        sys.exit(1)
    return a / b

def main():
    if len(sys.argv) < 4:
        print("Usage: calculator.py <operation> <number1> <number2>", file=sys.stderr)
        print("Operations: add, subtract, multiply, divide", file=sys.stderr)
        sys.exit(1)
    
    operation = sys.argv[1].lower()
    
    try:
        num1 = float(sys.argv[2])
        num2 = float(sys.argv[3])
    except ValueError:
        print("Error: Arguments must be numbers", file=sys.stderr)
        sys.exit(1)
    
    if operation == "add":
        result = add(num1, num2)
        print(f"{num1} + {num2} = {result}")
    elif operation == "subtract":
        result = subtract(num1, num2)
        print(f"{num1} - {num2} = {result}")
    elif operation == "multiply":
        result = multiply(num1, num2)
        print(f"{num1} * {num2} = {result}")
    elif operation == "divide":
        result = divide(num1, num2)
        print(f"{num1} / {num2} = {result}")
    else:
        print(f"Error: Unknown operation '{operation}'", file=sys.stderr)
        print("Operations: add, subtract, multiply, divide", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
''')
        self.calculator_script.close()
        
    def tearDown(self):
        """Clean up test environment."""
        # Remove temporary script files
        try:
            os.unlink(self.temp_script.name)
            os.unlink(self.calculator_script.name)
        except:
            pass
    
    def test_run_script_without_args(self):
        """Test running a script without arguments."""
        result = self.py_exec.run_script(self.temp_script.name)
        
        self.assertIsInstance(result, str)
        self.assertIn("Hello, World!", result)
        self.assertIn("Arguments: []", result)
        self.assertNotIn("Errors:", result)
    
    def test_run_script_with_args(self):
        """Test running a script with arguments."""
        result = self.py_exec.run_script(self.temp_script.name, ["arg1", "arg2"])
        
        self.assertIsInstance(result, str)
        self.assertIn("Hello, World!", result)
        self.assertIn("Arguments: ['arg1', 'arg2']", result)
        self.assertNotIn("Errors:", result)
    
    def test_run_script_nonexistent_file(self):
        """Test running a nonexistent script."""
        with self.assertRaises(FileNotFoundError):
            self.py_exec.run_script("nonexistent_file.py")
    
    def test_run_code_without_args(self):
        """Test running code from a string without arguments."""
        code = 'import sys\nprint("Hello from string!")\nprint(f"Arguments: {sys.argv[1:]}")'
        result = self.py_exec.run_code(code)
        
        self.assertIsInstance(result, str)
        self.assertIn("Hello from string!", result)
        self.assertIn("Arguments: []", result)
        self.assertNotIn("Errors:", result)
    
    def test_run_code_with_args(self):
        """Test running code from a string with arguments."""
        code = 'import sys\nprint("Hello from string!")\nprint(f"Arguments: {sys.argv[1:]}")'
        result = self.py_exec.run_code(code, ["arg1", "arg2"])
        
        self.assertIsInstance(result, str)
        self.assertIn("Hello from string!", result)
        self.assertIn("Arguments: ['arg1', 'arg2']", result)
        self.assertNotIn("Errors:", result)
    
    def test_run_code_with_syntax_error(self):
        """Test running code with a syntax error."""
        code = 'print("Incomplete string'  # Missing closing quote
        result = self.py_exec.run_code(code)
        
        self.assertIsInstance(result, str)
        self.assertIn("SyntaxError", result)
        self.assertIn("Execution failed with exit code:", result)
    
    def test_run_code_with_runtime_error(self):
        """Test running code with a runtime error."""
        code = 'import nonexistent_module'
        result = self.py_exec.run_code(code)
        
        self.assertIsInstance(result, str)
        self.assertIn("ModuleNotFoundError", result)
        self.assertIn("Execution failed with exit code:", result)
    
    def test_run_code_with_division_by_zero(self):
        """Test running code with a division by zero error."""
        code = 'print("This code will cause a runtime error")\nx = 10 / 0'
        result = self.py_exec.run_code(code)
        
        self.assertIsInstance(result, str)
        self.assertIn("ZeroDivisionError", result)
        self.assertIn("This code will cause a runtime error", result)
        self.assertIn("Execution failed with exit code:", result)
    
    def test_calculator_addition(self):
        """Test running the calculator script with addition operation."""
        result = self.py_exec.run_script(self.calculator_script.name, ["add", "5", "3"])
        
        self.assertIsInstance(result, str)
        self.assertIn("5.0 + 3.0 = 8.0", result)
        self.assertNotIn("Errors:", result)
    
    def test_calculator_subtraction(self):
        """Test running the calculator script with subtraction operation."""
        result = self.py_exec.run_script(self.calculator_script.name, ["subtract", "10", "4"])
        
        self.assertIsInstance(result, str)
        self.assertIn("10.0 - 4.0 = 6.0", result)
        self.assertNotIn("Errors:", result)
    
    def test_calculator_multiplication(self):
        """Test running the calculator script with multiplication operation."""
        result = self.py_exec.run_script(self.calculator_script.name, ["multiply", "6", "7"])
        
        self.assertIsInstance(result, str)
        self.assertIn("6.0 * 7.0 = 42.0", result)
        self.assertNotIn("Errors:", result)
    
    def test_calculator_division(self):
        """Test running the calculator script with division operation."""
        result = self.py_exec.run_script(self.calculator_script.name, ["divide", "20", "5"])
        
        self.assertIsInstance(result, str)
        self.assertIn("20.0 / 5.0 = 4.0", result)
        self.assertNotIn("Errors:", result)
    
    def test_calculator_division_by_zero(self):
        """Test running the calculator script with division by zero."""
        result = self.py_exec.run_script(self.calculator_script.name, ["divide", "10", "0"])
        
        self.assertIsInstance(result, str)
        self.assertIn("Error: Division by zero", result)
        self.assertIn("Execution failed with exit code:", result)
    
    def test_calculator_invalid_operation(self):
        """Test running the calculator script with an invalid operation."""
        result = self.py_exec.run_script(self.calculator_script.name, ["power", "2", "3"])
        
        self.assertIsInstance(result, str)
        self.assertIn("Error: Unknown operation 'power'", result)
        self.assertIn("Execution failed with exit code:", result)
    
    def test_calculator_missing_arguments(self):
        """Test running the calculator script with missing arguments."""
        result = self.py_exec.run_script(self.calculator_script.name, ["add"])
        
        self.assertIsInstance(result, str)
        self.assertIn("Usage: calculator.py <operation> <number1> <number2>", result)
        self.assertIn("Execution failed with exit code:", result)
    
    def test_calculator_code_execution(self):
        """Test running calculator logic directly as code."""
        code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        print("Error: Division by zero")
        return None
    return a / b

# Get operation and numbers from command-line arguments
import sys

if len(sys.argv) < 4:
    print("Usage: <operation> <number1> <number2>")
    sys.exit(1)

operation = sys.argv[1].lower()
num1 = float(sys.argv[2])
num2 = float(sys.argv[3])

if operation == "add":
    result = add(num1, num2)
    print(f"{num1} + {num2} = {result}")
elif operation == "subtract":
    result = subtract(num1, num2)
    print(f"{num1} - {num2} = {result}")
elif operation == "multiply":
    result = multiply(num1, num2)
    print(f"{num1} * {num2} = {result}")
elif operation == "divide":
    result = divide(num1, num2)
    if result is not None:
        print(f"{num1} / {num2} = {result}")
else:
    print(f"Error: Unknown operation '{operation}'")
    sys.exit(1)
"""
        result = self.py_exec.run_code(code, ["add", "12", "8"])
        
        self.assertIsInstance(result, str)
        self.assertIn("12.0 + 8.0 = 20.0", result)
        self.assertNotIn("Errors:", result)
    
    def test_factorial_calculation(self):
        """Test running code that calculates factorial."""
        code = """
import sys

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

if len(sys.argv) > 1:
    try:
        n = int(sys.argv[1])
        print(f"Factorial of {n} is {factorial(n)}")
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid integer")
else:
    print("No number provided for factorial calculation")
"""
        result = self.py_exec.run_code(code, ["5"])
        
        self.assertIsInstance(result, str)
        self.assertIn("Factorial of 5 is 120", result)
        self.assertNotIn("Errors:", result)
    
    def test_command_line_arguments_sum(self):
        """Test running code that sums command-line arguments."""
        code = """
import sys

print("Command-line arguments:")
for i, arg in enumerate(sys.argv[1:]):
    print(f"  Argument {i+1}: {arg}")

if len(sys.argv) > 1:
    try:
        total = sum(float(arg) for arg in sys.argv[1:])
        print(f"Sum of numeric arguments: {total}")
    except ValueError:
        print("Not all arguments are numeric")
"""
        result = self.py_exec.run_code(code, ["10", "20", "30"])
        
        self.assertIsInstance(result, str)
        self.assertIn("Command-line arguments:", result)
        self.assertIn("Argument 1: 10", result)
        self.assertIn("Argument 2: 20", result)
        self.assertIn("Argument 3: 30", result)
        self.assertIn("Sum of numeric arguments: 60.0", result)
        self.assertNotIn("Errors:", result)

if __name__ == "__main__":
    unittest.main() 