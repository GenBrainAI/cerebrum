import unittest
from src.tools.complexfibonaccicalculator import ComplexFibonacciCalculator

class TestComplexFibonacciCalculator(unittest.TestCase):
    def test_generate_sequence(self):
        calculator = ComplexFibonacciCalculator()
        self.assertEqual(calculator.generate_sequence(0), [])
        self.assertEqual(calculator.generate_sequence(1), [complex(0, 1)])
        self.assertEqual(calculator.generate_sequence(2), [complex(0, 1), complex(0, 2)])
        self.assertEqual(calculator.generate_sequence(3), [complex(0, 1), complex(0, 2), complex(0, 3)])

    def test_custom_start_values(self):
        calculator = ComplexFibonacciCalculator(complex(1, 1), complex(1, 2))
        self.assertEqual(calculator.generate_sequence(3), [complex(1, 1), complex(1, 2), complex(2, 3)])

if __name__ == '__main__':
    unittest.main()