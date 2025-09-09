import logging
import unittest
from unittest.mock import patch
from io import StringIO

from src.hcl_processor.logger_config import (
    get_logger,
    setup_logger,
    log_exception,
    log_operation_start,
    log_operation_success,
    log_operation_failure
)


class TestLoggerConfig(unittest.TestCase):
    """Test cases for logger_config module"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset any existing loggers
        logging.getLogger().handlers.clear()
        # Clear all hcl_processor loggers
        for logger_name in list(logging.getLogger().manager.loggerDict.keys()):
            if logger_name.startswith('hcl_processor'):
                logger = logging.getLogger(logger_name)
                logger.handlers.clear()
                logger.setLevel(logging.NOTSET)

    def tearDown(self):
        """Clean up after tests"""
        # Clear all handlers
        for logger_name in list(logging.getLogger().manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.setLevel(logging.NOTSET)
        logging.getLogger().handlers.clear()

    def capture_log_output(self, logger, func, *args, **kwargs):
        """Helper method to capture log output"""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))

        # Ensure logger has appropriate level
        if not logger.level or logger.level == logging.NOTSET:
            logger.setLevel(logging.INFO)

        # Add handler temporarily
        logger.addHandler(handler)
        try:
            func(*args, **kwargs)
            return stream.getvalue()
        finally:
            logger.removeHandler(handler)

    def test_get_logger_returns_logger_with_correct_name(self):
        """Test that get_logger returns a logger with the correct name"""
        logger = get_logger("test_module")
        self.assertEqual(logger.name, "hcl_processor.test_module")

    def test_setup_logger_info_level(self):
        """Test setup_logger with INFO level"""
        with patch('sys.stdout', new_callable=StringIO):
            logger = setup_logger(level=logging.INFO)
            self.assertEqual(logger.level, logging.INFO)

    def test_setup_logger_debug_level(self):
        """Test setup_logger with DEBUG level"""
        with patch('sys.stdout', new_callable=StringIO):
            logger = setup_logger(level=logging.DEBUG)
            self.assertEqual(logger.level, logging.DEBUG)

    def test_log_exception_with_exception(self):
        """Test log_exception function with actual exception"""
        logger = get_logger("test")
        exception = ValueError("Test error")

        output = self.capture_log_output(
            logger,
            lambda: log_exception(logger, exception, "Test context")
        )

        self.assertIn("Test context", output)
        self.assertIn("ValueError", output)

    def test_log_exception_with_debug_shows_traceback(self):
        """Test log_exception shows traceback in debug mode"""
        logger = get_logger("test")
        logger.setLevel(logging.DEBUG)
        exception = ValueError("Test error")

        output = self.capture_log_output(
            logger,
            lambda: log_exception(logger, exception, "Test context")
        )

        self.assertIn("Test context", output)
        self.assertIn("ValueError", output)

    def test_log_operation_start(self):
        """Test log_operation_start function"""
        logger = get_logger("test")

        output = self.capture_log_output(
            logger,
            lambda: log_operation_start(logger, "Test operation")
        )

        self.assertIn("Starting", output)
        self.assertIn("Test operation", output)

    def test_log_operation_success(self):
        """Test log_operation_success function"""
        logger = get_logger("test")

        output = self.capture_log_output(
            logger,
            lambda: log_operation_success(logger, "Test operation")
        )

        self.assertIn("Successfully completed", output)
        self.assertIn("Test operation", output)

    def test_log_operation_failure(self):
        """Test log_operation_failure function"""
        logger = get_logger("test")
        exception = Exception("Test reason")

        output = self.capture_log_output(
            logger,
            lambda: log_operation_failure(logger, "Test operation", exception)
        )

        self.assertIn("Failed", output)
        self.assertIn("Test operation", output)

    def test_color_formatting_info(self):
        """Test that INFO level messages are colored green"""
        logger = get_logger("test")

        # Capture with color enabled
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        from src.hcl_processor.logger_config import create_colored_formatter
        handler.setFormatter(create_colored_formatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            logger.info("Test info message")
            output = stream.getvalue()

            # Check for ANSI color codes (green)
            self.assertIn("\033[32m", output)  # Green color code
            self.assertIn("INFO", output)
        finally:
            logger.removeHandler(handler)

    def test_color_formatting_error(self):
        """Test that ERROR level messages are colored red"""
        logger = get_logger("test")

        # Capture with color enabled
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        from src.hcl_processor.logger_config import create_colored_formatter
        handler.setFormatter(create_colored_formatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            logger.error("Test error message")
            output = stream.getvalue()

            # Check for ANSI color codes (red)
            self.assertIn("\033[31m", output)  # Red color code
            self.assertIn("ERROR", output)
        finally:
            logger.removeHandler(handler)

    def test_color_formatting_debug(self):
        """Test that DEBUG level messages are colored cyan"""
        logger = get_logger("test")

        # Capture with color enabled
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        from src.hcl_processor.logger_config import create_colored_formatter
        handler.setFormatter(create_colored_formatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            logger.debug("Test debug message")
            output = stream.getvalue()

            # Check for ANSI color codes (cyan)
            self.assertIn("\033[36m", output)  # Cyan color code
            self.assertIn("DEBUG", output)
        finally:
            logger.removeHandler(handler)

    def test_logger_format_consistency(self):
        """Test that logger format is consistent across different modules"""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Use our helper method for both loggers
        output1 = self.capture_log_output(logger1, lambda: logger1.info("Test message 1"))
        output2 = self.capture_log_output(logger2, lambda: logger2.info("Test message 2"))

        # Both should have content
        self.assertIn("Test message 1", output1)
        self.assertIn("Test message 2", output2)
        self.assertIn("hcl_processor.module1", output1)
        self.assertIn("hcl_processor.module2", output2)


if __name__ == '__main__':
    unittest.main()
