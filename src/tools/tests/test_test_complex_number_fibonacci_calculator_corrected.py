import unittest

class TestComplexNumberFibonacciCalculator(unittest.TestCase):

    def test_sequence_generation(self):
        from complex_number_fibonacci_calculator import generate_complex_fibonacci
        start1 = 1j + 1j
        start2 = 1j + 2j
        sequence = generate_complex_fibonacci(start1, start2, 10)
        expected_sequence = [
            1j + 1j,
            1j + 2j,
            2j + 3j,
            3j + 5j,
            5j + 8j,
            8j + 13j,
            13j + 21j,
            21j + 34j,
            34j + 55j,
            55j + 89j
        ]
        self.assertEqual(sequence, expected_sequence)

    def test_edge_case_zero_length(self):
        from complex_number_fibonacci_calculator import generate_complex_fibonacci
        sequence = generate_complex_fibonacci(1j + 1j, 1j + 2j, 0)
        self.assertEqual(sequence, [])

    def test_edge_case_one_length(self):
        from complex_number_fibonacci_calculator import generate_complex_fibonacci
        sequence = generate_complex_fibonacci(1j + 1j, 1j + 2j, 1)
        self.assertEqual(sequence, [1j + 1j])

if __name__ == '__main__':
    unittest.main()
