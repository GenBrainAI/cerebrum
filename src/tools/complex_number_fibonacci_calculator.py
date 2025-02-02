def generate_complex_fibonacci(start1, start2, n):
    """
    Generates a Fibonacci sequence for complex numbers.

    :param start1: First complex number in the sequence.
    :param start2: Second complex number in the sequence.
    :param n: The number of terms in the sequence.
    :return: A list of complex numbers representing the Fibonacci sequence.
    """
    sequence = [start1, start2]
    for _ in range(2, n):
        next_term = sequence[-1] + sequence[-2]
        sequence.append(next_term)
    return sequence
