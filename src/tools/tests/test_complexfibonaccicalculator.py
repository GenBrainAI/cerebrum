# Unit tests for Complex Number Fibonacci Calculator
import unittest
from src.tools.complexfibonaccicalculator import ComplexFibonacciCalculator

class TestComplexFibonacciCalculator(unittest.TestCase):

    def test_generate_sequence(self):
        calculator = ComplexFibonacciCalculator()
        expected_sequence_5 = [complex(0, 1), complex(0, 2), complex(0, 3), complex(0, 5), complex(0, 8)]
        self.assertEqual(calculator.generate_sequence(5), expected_sequence_5)
        
        expected_sequence_1 = [complex(0, 1)]
        self.assertEqual(calculator.generate_sequence(1), expected_sequence_1)
        
        expected_sequence_0 = []
        self.assertEqual(calculator.generate_sequence(0), expected_sequence_0)
        
        expected_sequence_2 = [complex(0, 1), complex(0, 2)]
        self.assertEqual(calculator.generate_sequence(2), expected_sequence_2)
    
    def test_custom_start_values(self):
        calculator = ComplexFibonacciCalculator(complex(1, 1), complex(1, 2))
        expected_sequence = [complex(1, 1), complex(1, 2), complex(2, 3), complex(3, 5), complex(5, 8)]
        self.assertEqual(calculator.generate_sequence(5), expected_sequence)