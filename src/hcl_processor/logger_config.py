"""
Logger configuration and utility module
Provides unified log formatting and level settings
"""
import logging
import sys
from typing import Optional


# ANSI color codes
LOG_COLORS = {
    'DEBUG': '\033[36m',      # Cyan
    'INFO': '\033[32m',       # Green
    'WARNING': '\033[33m',    # Yellow
    'ERROR': '\033[31m',      # Red
    'CRITICAL': '\033[35m',   # Magenta
    'RESET': '\033[0m'        # Reset
}


def create_colored_formatter() -> logging.Formatter:
    """Create a color-enabled formatter"""
    class ColoredFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_color = LOG_COLORS.get(record.levelname, LOG_COLORS['RESET'])
            reset_color = LOG_COLORS['RESET']
            record.levelname = f"{log_color}{record.levelname}{reset_color}"
            return super().format(record)

    return ColoredFormatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def setup_logger(
    name: str = __name__,
    level: int = logging.INFO,
    enable_colors: bool = True
) -> logging.Logger:
    """
    Setup unified logging configuration

    Args:
        name: Logger name
        level: Log level
        enable_colors: Enable color output

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Setup formatter
    if enable_colors and sys.stdout.isatty():
        formatter = create_colored_formatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(level)

    # Disable propagation to parent loggers
    logger.propagate = False

    return logger


def log_exception(
    logger: logging.Logger,
    exception: Exception,
    context: Optional[str] = None,
    level: int = logging.ERROR
) -> None:
    """
    Unified exception logging

    Args:
        logger: Logger instance
        exception: Exception instance
        context: Additional context information
        level: Log level
    """
    error_msg = f"{type(exception).__name__}: {str(exception)}"
    if context:
        error_msg = f"{context} - {error_msg}"

    logger.log(level, error_msg)

    # Output stack trace for DEBUG level
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Stack trace:", exc_info=True)


def log_operation_start(logger: logging.Logger, operation: str, target: str = "") -> None:
    """Log operation start"""
    message = f"Starting {operation}"
    if target:
        message += f" for {target}"
    logger.info(message)


def log_operation_success(logger: logging.Logger, operation: str, target: str = "") -> None:
    """Log operation success"""
    message = f"Successfully completed {operation}"
    if target:
        message += f" for {target}"
    logger.info(message)


def log_operation_failure(
    logger: logging.Logger,
    operation: str,
    exception: Exception,
    target: str = ""
) -> None:
    """Log operation failure"""
    context = f"Failed {operation}"
    if target:
        context += f" for {target}"
    log_exception(logger, exception, context)


def get_logger(name: str) -> logging.Logger:
    """Get unified project logger"""
    return logging.getLogger(f"hcl_processor.{name}")
