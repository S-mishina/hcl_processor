import os
import time
from contextlib import contextmanager
from typing import Generator
from .logger_config import get_logger, log_operation_start, log_operation_success, log_operation_failure


logger = get_logger("utils")


def reset_markdown_file(markdown_path: str) -> bool:
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


@contextmanager
def measure_time(operation_name: str, logger_instance=None) -> Generator[None, None, None]:
    """
    Context manager to measure and log execution time of operations.

    Args:
        operation_name (str): Name of the operation being measured
        logger_instance: Logger instance to use (defaults to module logger)

    Yields:
        None

    Example:
        with measure_time("file processing", logger):
            # Your code here
            process_file()
    """

    if logger_instance is None:
        logger_instance = logger

    start_time = time.time()
    log_operation_start(logger_instance, operation_name)

    try:
        yield
        processing_time = time.time() - start_time
        log_operation_success(logger_instance, operation_name)
        logger_instance.info(f"Processing time: {processing_time:.2f}s")
    except Exception as e:
        processing_time = time.time() - start_time
        log_operation_failure(logger_instance, operation_name, e)
        logger_instance.error(f"Processing time before failure: {processing_time:.2f}s")
        raise


def ensure_directory_exists(file_path: str) -> None:
    """
    Ensure the directory exists for the given file path.

    Args:
        file_path (str): Path to the file (directory will be created for this file)
    """
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
