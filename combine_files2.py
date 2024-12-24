import os
import fnmatch

def should_exclude_file(filename, exclude_items, exclude_patterns):
    """Check if a file should be excluded based on exact matches and patterns."""
    if filename.startswith('.') or filename in exclude_items:
        return True
    return any(fnmatch.fnmatch(filename, pattern) for pattern in exclude_patterns)

def combine_files(extensions, directory=".", recursive=False, exclude_items=None, exclude_patterns=None, max_file_size_kb=100):
    """Combines files with the given extensions into a single file.

    Args:
        extensions: A list of file extensions to include (e.g., ['.txt', '.log']).
        directory: The directory to start searching for files.
        recursive: A flag to determine if the search should be recursive.
        exclude_items: A list of exact file or directory names to exclude.
        exclude_patterns: A list of glob patterns to exclude (e.g., 'test_*.py').
        max_file_size_kb: Maximum size of individual files to include (in KB).
    """

    if exclude_items is None:
        exclude_items = []
    if exclude_patterns is None:
        exclude_patterns = []

    with open("combined_code.txt", "w") as outfile:
        if recursive:
            for root, dirs, files in os.walk(directory):
                # Exclude specified directories and hidden directories
                dirs[:] = [d for d in dirs if not should_exclude_file(d, exclude_items, exclude_patterns)]
                
                for filename in files:
                    if should_exclude_file(filename, exclude_items, exclude_patterns):
                        continue
                        
                    base, ext = os.path.splitext(filename)
                    if ext in extensions:
                        file_path = os.path.join(root, filename)
                        
                        # Skip files larger than max_file_size_kb
                        file_size_kb = os.path.getsize(file_path) / 1024
                        if file_size_kb > max_file_size_kb:
                            print(f"Skipping large file: {file_path} ({file_size_kb:.1f}KB)")
                            continue
                            
                        print(f"Including: {file_path}")
                        outfile.write(f"\n{'='*80}\n")
                        outfile.write(f"File: {file_path}\n")
                        outfile.write(f"{'='*80}\n\n")
                        try:
                            with open(file_path, "r", encoding='utf-8') as infile:
                                outfile.write(infile.read())
                            outfile.write("\n\n")
                        except Exception as e:
                            print(f"Error reading {file_path}: {e}")
        else:
            for filename in os.listdir(directory):
                if should_exclude_file(filename, exclude_items, exclude_patterns):
                    continue
                    
                base, ext = os.path.splitext(filename)
                if ext in extensions:
                    file_path = os.path.join(directory, filename)
                    
                    # Skip files larger than max_file_size_kb
                    file_size_kb = os.path.getsize(file_path) / 1024
                    if file_size_kb > max_file_size_kb:
                        print(f"Skipping large file: {file_path} ({file_size_kb:.1f}KB)")
                        continue
                        
                    print(f"Including: {file_path}")
                    outfile.write(f"\n{'='*80}\n")
                    outfile.write(f"File: {file_path}\n")
                    outfile.write(f"{'='*80}\n\n")
                    try:
                        with open(file_path, "r", encoding='utf-8') as infile:
                            outfile.write(infile.read())
                        outfile.write("\n\n")
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")

if __name__ == "__main__":
    file_extensions = ['.py']
    exclude_items = [
        # Directories
        'integration', 'experimental', '__pycache__', 'tests', 'notebooks',
        'pages', '.pytest_cache', '.vscode', '.idea', '.github', 'test_context_db',
        'test_persistent_state', 'db', 'sms_logs', 'context_db', 'persistent_state',
        'state_setup', 'models', 'assistant',  # Additional directories to exclude
        
        # Files
        'combine_files.py', 'security_api.py', 'crew_playground.py',
        'domain_integration.py', 'state_setup.py', 'state_setup_context2task.py',
        'setup.py', 'conftest.py'
    ]
    
    exclude_patterns = [
        'test_*.py',      # Test files
        '*_test.py',      # Test files (alternate naming)
        '*.config.py',    # Configuration files
        '*.conf.py',      # Configuration files
        'setup_*.py',     # Setup files
        '*_setup.py',     # Setup files
    ]
    
    combine_files(
        file_extensions,
        recursive=True,
        exclude_items=exclude_items,
        exclude_patterns=exclude_patterns,
        max_file_size_kb=100
    )
    print("Files combined successfully into 'combined_code.txt'")
