# Complex Number Fibonacci Calculator

def generate_fibonacci_complex(n):
    """
    Generate a Fibonacci sequence for complex numbers starting with z0 = i + i and z1 = i + 2i.
    
    Parameters:
    n (int): The number of terms to generate in the sequence.

    Returns:
    list: A list of complex numbers representing the Fibonacci sequence.
    """
    # Starting complex numbers
    z0 = complex(0, 2)  # i + i = 2i
    z1 = complex(0, 3)  # i + 2i = 3i
    
    # Initialize the sequence with the starting values
    sequence = [z0, z1]
    
    # Generate the Fibonacci sequence for complex numbers
    for i in range(2, n):
        # z_n = z_{n-1} + z_{n-2}
        next_term = sequence[i - 1] + sequence[i - 2]
        sequence.append(next_term)
    
    return sequence

def main():
    # Example usage of the Complex Number Fibonacci Calculator
    num_terms = int(input("Enter the number of terms for the complex Fibonacci sequence: "))
    
    # Generate the sequence
    fibonacci_sequence = generate_fibonacci_complex(num_terms)
    
    # Display the sequence
    for index, term in enumerate(fibonacci_sequence):
        print(f"Term {index}: {term}")

if __name__ == "__main__":
    main()
