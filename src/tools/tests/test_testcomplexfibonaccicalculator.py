# Unit Tests for Complex Number Fibonacci Calculator

import unittest
from src.tools.complexfibonaccicalculator import ComplexFibonacciCalculator

class TestComplexFibonacciCalculator(unittest.TestCase):
    def test_initialization(self):
        calc = ComplexFibonacciCalculator(complex(1, 1), complex(1, 2))
        self.assertEqual(calc.start1, complex(1, 1))
        self.assertEqual(calc.start2, complex(1, 2))
        self.assertEqual(calc.sequence, [complex(1, 1), complex(1, 2)])

    def test_add_complex_numbers(self):
        calc = ComplexFibonacciCalculator(complex(0, 0), complex(0, 0))
        result = calc.add_complex_numbers(complex(1, 1), complex(2, 2))
        self.assertEqual(result, complex(3, 3))

    def test_generate_sequence(self):
        calc = ComplexFibonacciCalculator(complex(1, 1), complex(1, 2))
        sequence = calc.generate_sequence(5)
        expected_sequence = [complex(1, 1), complex(1, 2), complex(2, 3), complex(3, 5), complex(5, 8)]
        self.assertEqual(sequence, expected_sequence)

    def test_generate_sequence_edge_cases(self):
        calc = ComplexFibonacciCalculator(complex(0, 0), complex(0, 0))
        sequence = calc.generate_sequence(3)
        expected_sequence = [complex(0, 0), complex(0, 0), complex(0, 0)]
        self.assertEqual(sequence, expected_sequence)

if __name__ == '__main__':
    unittest.main()
