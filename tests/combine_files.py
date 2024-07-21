import os

def combine_files(extensions, directory=".", recursive=False, exclude_items=None):
    """Combines files with the given extensions into a single file.

    Args:
        extensions: A list of file extensions to include (e.g., ['.txt', '.log']).
        directory: The directory to start searching for files.
        recursive: A flag to determine if the search should be recursive.
        exclude_items: A list of exact file or directory names to exclude.
    """

    if exclude_items is None:
        exclude_items = []

    with open("combined_output.txt", "w") as outfile:
        if recursive:
            print("Recursive")
            for root, dirs, files in os.walk(directory):
                # Exclude specified directories and hidden directories
                dirs[:] = [d for d in dirs if d not in exclude_items and not d.startswith('.')]
                for filename in files:
                    # Skip hidden files and excluded files
                    if filename.startswith('.') or filename in exclude_items:
                        continue
                    base, ext = os.path.splitext(filename)
                    if ext in extensions:  # Exact match for extensions
                        print(f"filename: {filename}")
                        file_path = os.path.join(root, filename)
                        outfile.write(f"<{file_path}>\n\n")
                        with open(file_path, "r") as infile:
                            outfile.write(infile.read())
                        outfile.write("\n\n")
        else:
            for filename in os.listdir(directory):
                # Skip hidden files and excluded files
                if filename.startswith('.') or filename in exclude_items:
                    continue
                base, ext = os.path.splitext(filename)
                if ext in extensions:  # Exact match for extensions
                    file_path = os.path.join(directory, filename)
                    outfile.write(f"<{file_path}>\n\n")
                    with open(file_path, "r") as infile:
                        outfile.write(infile.read())
                    outfile.write("\n\n")

if __name__ == "__main__":
    file_extensions = ['.py', '.ipynb']
    exclude_items = ['crewai', 'crewAI-examples', 'tests', 'experimental', '__pycache__', 'combine_files.py']
    combine_files(file_extensions, recursive=True, exclude_items=exclude_items)
    print("Files combined successfully into 'combined_output.txt'")