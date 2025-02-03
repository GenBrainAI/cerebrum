# Updated Unit tests for Complex Number Fibonacci Calculator

import unittest
from src.tools.complex_number_fibonacci_calculator import generate_fibonacci_complex  # Corrected import path

class TestComplexFibonacciCalculator(unittest.TestCase):
    def test_generate_fibonacci_complex(self):
        # Test with 5 terms
        expected_sequence = [complex(0, 2), complex(0, 3), complex(0, 5), complex(0, 8), complex(0, 13)]
        self.assertEqual(generate_fibonacci_complex(5), expected_sequence)
        
        # Test with 0 terms
        self.assertEqual(generate_fibonacci_complex(0), [])
        
        # Test with 1 term
        self.assertEqual(generate_fibonacci_complex(1), [complex(0, 2)])
        
        # Test with 2 terms
        self.assertEqual(generate_fibonacci_complex(2), [complex(0, 2), complex(0, 3)])

if __name__ == '__main__':
    unittest.main()
