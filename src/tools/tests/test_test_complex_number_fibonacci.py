import unittest

class TestComplexNumberFibonacci(unittest.TestCase):
    def test_default_sequence(self):
        from src.tools.complex_number_fibonacci import generate_fibonacci_sequence
        self.assertEqual(generate_fibonacci_sequence(10),
                         [(1+1j), (1+2j), (2+3j), (3+5j), (5+8j), (8+13j), (13+21j), (21+34j), (34+55j), (55+89j)])

    def test_custom_starting_numbers(self):
        from src.tools.complex_number_fibonacci import generate_fibonacci_sequence
        self.assertEqual(generate_fibonacci_sequence(5, start1=2+3j, start2=3+4j),
                         [(2+3j), (3+4j), (5+7j), (8+11j), (13+18j)])

    def test_invalid_n_terms(self):
        from src.tools.complex_number_fibonacci import generate_fibonacci_sequence
        with self.assertRaises(ValueError):
            generate_fibonacci_sequence(0)
        with self.assertRaises(ValueError):
            generate_fibonacci_sequence(-5)
        with self.assertRaises(ValueError):
            generate_fibonacci_sequence('a')

if __name__ == '__main__':
    unittest.main()