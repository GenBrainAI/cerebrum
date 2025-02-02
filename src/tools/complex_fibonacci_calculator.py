class ComplexFibonacciCalculator:
    def __init__(self, first, second):
        self.first = first
        self.second = second

    def generate_sequence(self, n):
        sequence = [self.first, self.second]
        for _ in range(2, n):
            next_value = sequence[-1] + sequence[-2]
            sequence.append(next_value)
        return sequence

# Example usage
# calculator = ComplexFibonacciCalculator(complex(0, 1), complex(0, 2))
# sequence = calculator.generate_sequence(10)
# print(sequence)