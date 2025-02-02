def generate_fibonacci_sequence(start1, start2, n):
    if not isinstance(start1, complex) or not isinstance(start2, complex):
        raise TypeError("start1 and start2 must be complex numbers")
    if not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")

    sequence = [start1, start2]
    while len(sequence) < n:
        next_term = sequence[-1] + sequence[-2]
        sequence.append(next_term)
    return sequence