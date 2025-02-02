import unittest
from src.tools.complex_fibonacci_calculator import ComplexFibonacciCalculator

class TestComplexFibonacciCalculator(unittest.TestCase):
    def test_sequence_generation(self):
        calculator = ComplexFibonacciCalculator(complex(0, 1), complex(0, 2))
        expected_sequence = [complex(0, 1), complex(0, 2), complex(0, 3), complex(0, 5), complex(0, 8)]
        result = calculator.generate_sequence(5)
        self.assertEqual(result, expected_sequence)

    def test_sequence_generation_with_different_start(self):
        calculator = ComplexFibonacciCalculator(complex(1, 1), complex(1, 2))
        expected_sequence = [complex(1, 1), complex(1, 2), complex(2, 3), complex(3, 5), complex(5, 8)]
        result = calculator.generate_sequence(5)
        self.assertEqual(result, expected_sequence)

if __name__ == '__main__':
    unittest.main()