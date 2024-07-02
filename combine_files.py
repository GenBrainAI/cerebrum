import os

def combine_files(extensions, directory=".", recursive=False, exclude_dirs=None):
    """Combines files with the given extensions into a single file.

    Args:
        extensions: A list of file extensions (e.g., ['.txt', '.log']).
        directory: The directory to start searching for files.
        recursive: A flag to determine if the search should be recursive.
        exclude_dirs: A list of directory names to exclude from the search.
    """

    if exclude_dirs is None:
        exclude_dirs = []

    with open("combined_output.txt", "w") as outfile:
        if recursive:
            print("Recursive")
            for root, dirs, files in os.walk(directory):
                # Exclude specified directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for filename in files:
                    print(f"filename: {filename}")
                    base, ext = os.path.splitext(filename)
                    if ext.lower() in extensions:
                        file_path = os.path.join(root, filename)
                        outfile.write(f"<{file_path}>\n\n")
                        with open(file_path, "r") as infile:
                            outfile.write(infile.read())
                        outfile.write("\n\n")
        else:
            for filename in os.listdir(directory):
                base, ext = os.path.splitext(filename)
                if ext.lower() in extensions:
                    file_path = os.path.join(directory, filename)
                    outfile.write(f"<{file_path}>\n\n")
                    with open(file_path, "r") as infile:
                        outfile.write(infile.read())
                    outfile.write("\n\n")

if __name__ == "__main__":
    file_extensions = ['.py', '.md']  #'.yaml', '.yml',
    exclude_directories = ['crewai', 'crewAI-examples']
    combine_files(file_extensions, recursive=True, exclude_dirs=exclude_directories)
    print("Files combined successfully into 'combined_output.txt'")
