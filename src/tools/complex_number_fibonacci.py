def generate_fibonacci_sequence(n_terms, start1=1+1j, start2=1+2j):
    if not isinstance(n_terms, int) or n_terms <= 0:
        raise ValueError("n_terms must be a positive integer")
    sequence = [start1, start2]
    while len(sequence) < n_terms:
        sequence.append(sequence[-1] + sequence[-2])
    return sequence