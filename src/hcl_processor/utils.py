import logging
import os

logger = logging.getLogger(__name__)


def reset_markdown_file(markdown_path):
    """
    Reset the markdown output file if it exists.
    
    Args:
        markdown_path (str): Path to the markdown file to reset
        
    Returns:
        bool: True if file was reset, False if file didn't exist
    """
    if os.path.exists(markdown_path):
        logger.info(f"Reset existing markdown file: {markdown_path}")
        os.remove(markdown_path)
        return True
    return False


def ensure_directory_exists(file_path):
    """
    Ensure the directory exists for the given file path.
    
    Args:
        file_path (str): Path to the file (directory will be created for this file)
    """
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
