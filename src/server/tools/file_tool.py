from datetime import datetime


def save_file(content: str, type: str, path="/tmp") -> str:
    # Determine file extension based on type
    extension_map = {
        'text': '.txt',
        'markdown': '.md',
        'html': '.html'
    }
    extension = extension_map.get(type, '.txt')

    # Create a unique file name
    file_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}{extension}"

    # Write content to the file
    with open(f"{path}/{file_name}", 'w') as file:
        file.write(content)

    return f"File written: {file_name}"
