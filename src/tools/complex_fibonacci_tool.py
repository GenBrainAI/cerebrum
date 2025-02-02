class ComplexFibonacciCalculator:
    def __init__(self, start1: complex, start2: complex) -> None:
        """
        Initialize the calculator with two starting complex numbers.

        :param start1: The first complex number in the sequence.
        :param start2: The second complex number in the sequence.
        """
        self.start1 = start1
        self.start2 = start2
        self.sequence = [start1, start2]

    def add_complex_numbers(self, a: complex, b: complex) -> complex:
        """
        Adds two complex numbers and returns the result.

        :param a: The first complex number.
        :param b: The second complex number.
        :return: The sum of the two complex numbers.
        """
        return a + b

    def generate_sequence(self, n: int) -> list:
        """
        Generates the first `n` numbers of the Fibonacci sequence.

        :param n: The number of Fibonacci numbers to generate.
        :return: A list containing the first `n` numbers of the sequence.
        """
        while len(self.sequence) < n:
            next_value = self.add_complex_numbers(self.sequence[-1], self.sequence[-2])
            self.sequence.append(next_value)
        return self.sequence[:n]

# Example usage
# Initialize the calculator with complex numbers i+i and i+2i
calculator = ComplexFibonacciCalculator(complex(1, 1), complex(1, 2))

# Generate the first 10 numbers in the sequence
sequence = calculator.generate_sequence(10)
print(sequence)