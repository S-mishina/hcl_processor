import logging
import os
import unittest
from unittest.mock import Mock, patch, call
import tempfile

from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

from src.hcl_processor.main import main


class TestMain(unittest.TestCase):
    """Comprehensive test cases for main module"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_dir, "test_config.yaml")
        
        # Sample config content
        self.sample_config = {
            "input": {
                "resource_data": {
                    "files": ["test.tf"]
                },
                "modules": {"enabled": False},
                "local_files": [],
                "failback": {"enabled": False}
            },
            "output": {
                "json_path": os.path.join(self.test_dir, "output.json"),
                "markdown_path": os.path.join(self.test_dir, "output.md")
            },
            "bedrock": {
                "output_json": {"type": "object"}
            }
        }
        
        self.sample_system_config = {
            "system_call": {
                "exit_success": 0,
                "exit_system_config_error": 1,
                "exit_config_error": 2,
                "exit_file_read_error": 3,
                "exit_validation_error": 4,
                "exit_bedrock_error": 5,
                "exit_unknown_error": 99
            },
            "constants": {
                "file_processing": {
                    "terraform_extension": ".tf"
                }
            }
        }

    def tearDown(self):
        """Clean up after tests"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    @patch('src.hcl_processor.main.load_config')
    @patch('src.hcl_processor.main.run_hcl_file_workflow')
    @patch('src.hcl_processor.main.setup_logger')
    @patch('src.hcl_processor.main.reset_markdown_file')
    def test_main_success_with_files(self, mock_reset_markdown, mock_setup_logger, mock_workflow, mock_load_config, mock_load_system_config, mock_parse_args):
        """Test successful execution with files"""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.return_value = self.sample_system_config
        mock_load_config.return_value = self.sample_config
        
        # Execute
        result = main()
        
        # Verify
        self.assertEqual(result, 0)
        
        # Verify reset_markdown_file is called once at the start
        mock_reset_markdown.assert_called_once_with(self.sample_config["output"]["markdown_path"])
        
        self.assertEqual(mock_setup_logger.call_count, 2)
        mock_setup_logger.assert_any_call("hcl_processor", level=logging.INFO)
        mock_setup_logger.assert_any_call("hcl_processor.main", level=logging.INFO)
        mock_workflow.assert_called_once_with("test.tf", self.sample_config, self.sample_system_config)
        mock_logger.info.assert_any_call("Processing files...")
        mock_logger.info.assert_any_call("1 files found to process.")
        mock_logger.info.assert_any_call("All files processed successfully.")

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    @patch('src.hcl_processor.main.load_config')
    @patch('src.hcl_processor.main.os.walk')
    @patch('src.hcl_processor.main.run_hcl_file_workflow')
    @patch('src.hcl_processor.main.setup_logger')
    @patch('src.hcl_processor.main.reset_markdown_file')
    def test_main_success_with_folder(self, mock_reset_markdown, mock_setup_logger, mock_workflow, mock_walk, mock_load_config, mock_load_system_config, mock_parse_args):
        """Test successful execution with folder processing"""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = True  # Test debug mode
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.return_value = self.sample_system_config
        
        folder_config = self.sample_config.copy()
        folder_config["input"]["resource_data"] = {"folder": "/test/folder"}
        mock_load_config.return_value = folder_config
        
        # Mock os.walk to return test files
        mock_walk.return_value = [
            ("/test/folder", [], ["file1.tf", "file2.tf", "other.txt"])
        ]
        
        # Execute
        result = main()
        
        # Verify
        self.assertEqual(result, 0)
        
        # Verify reset_markdown_file is called once at the start
        mock_reset_markdown.assert_called_once_with(folder_config["output"]["markdown_path"])
        
        self.assertEqual(mock_setup_logger.call_count, 2)
        mock_setup_logger.assert_any_call("hcl_processor", level=logging.DEBUG)
        mock_setup_logger.assert_any_call("hcl_processor.main", level=logging.DEBUG)
        mock_logger.info.assert_any_call("Processing folder...")
        mock_logger.info.assert_any_call("Processing all .tf files in folder: /test/folder")
        
        # Verify workflow called for each .tf file
        expected_calls = [
            call("/test/folder/file1.tf", folder_config, self.sample_system_config),
            call("/test/folder/file2.tf", folder_config, self.sample_system_config)
        ]
        mock_workflow.assert_has_calls(expected_calls)

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    def test_main_system_config_failure(self, mock_load_system_config, mock_parse_args):
        """Test system config loading failure"""
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.side_effect = Exception("System config error")
        
        result = main()
        
        self.assertEqual(result, 1)  # EXIT_SYSTEM_CONFIG_ERROR

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    @patch('src.hcl_processor.main.load_config')
    def test_main_config_failure(self, mock_load_config, mock_load_system_config, mock_parse_args):
        """Test config loading failure"""
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.return_value = self.sample_system_config
        mock_load_config.side_effect = ValueError("Config error")
        
        result = main()
        
        self.assertEqual(result, 2)  # exit_config_error

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    @patch('src.hcl_processor.main.load_config')
    @patch('src.hcl_processor.main.os.walk')
    @patch('src.hcl_processor.main.setup_logger')
    def test_main_bedrock_errors_outside_loop(self, mock_setup_logger, mock_walk, mock_load_config, mock_load_system_config, mock_parse_args):
        """Test Bedrock API errors that occur outside the file processing loop"""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.return_value = self.sample_system_config
        mock_load_config.return_value = self.sample_config
        
        # Mock os.walk to raise Bedrock error
        mock_walk.side_effect = EndpointConnectionError(endpoint_url="test")
        
        # Config with folder to trigger os.walk
        folder_config = self.sample_config.copy()
        folder_config["input"]["resource_data"] = {"folder": "/test/folder"}
        mock_load_config.return_value = folder_config
        
        result = main()
        
        self.assertEqual(result, 5)  # exit_bedrock_error

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    @patch('src.hcl_processor.main.load_config')
    @patch('src.hcl_processor.main.os.walk')
    @patch('src.hcl_processor.main.setup_logger')
    def test_main_unknown_exception_outside_loop(self, mock_setup_logger, mock_walk, mock_load_config, mock_load_system_config, mock_parse_args):
        """Test handling of unknown exceptions outside the file processing loop"""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.return_value = self.sample_system_config
        mock_load_config.return_value = self.sample_config
        
        # Mock os.walk to raise unknown error
        mock_walk.side_effect = RuntimeError("Unknown error")
        
        # Config with folder to trigger os.walk
        folder_config = self.sample_config.copy()
        folder_config["input"]["resource_data"] = {"folder": "/test/folder"}
        mock_load_config.return_value = folder_config
        
        result = main()
        
        self.assertEqual(result, 99)  # exit_unknown_error

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    @patch('src.hcl_processor.main.load_config')
    @patch('src.hcl_processor.main.run_hcl_file_workflow')
    @patch('src.hcl_processor.main.setup_logger')
    def test_main_individual_file_errors_are_caught(self, mock_setup_logger, mock_workflow, mock_load_config, mock_load_system_config, mock_parse_args):
        """Test that individual file processing errors are caught and logged but don't stop execution"""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.return_value = self.sample_system_config
        mock_load_config.return_value = self.sample_config
        
        # Test different error types that should be caught in individual file processing
        test_errors = [
            EndpointConnectionError(endpoint_url="test"),
            ReadTimeoutError(endpoint_url="test"),
            ClientError({"Error": {"Code": "TestError", "Message": "Test"}}, "test_operation"),
            RuntimeError("Unknown error")
        ]
        
        for error in test_errors:
            with self.subTest(error=type(error).__name__):
                mock_workflow.side_effect = error
                result = main()
                # Individual file errors should be caught and execution continues
                self.assertEqual(result, 0)  # Should still succeed overall

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    @patch('src.hcl_processor.main.load_config')
    @patch('src.hcl_processor.main.run_hcl_file_workflow')
    @patch('src.hcl_processor.main.setup_logger')
    def test_main_file_processing_with_errors(self, mock_setup_logger, mock_workflow, mock_load_config, mock_load_system_config, mock_parse_args):
        """Test file processing where some files fail but execution continues"""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.return_value = self.sample_system_config
        
        multiple_files_config = self.sample_config.copy()
        multiple_files_config["input"]["resource_data"]["files"] = ["test1.tf", "test2.tf", "test3.tf"]
        mock_load_config.return_value = multiple_files_config
        
        # Mock workflow to fail on second file
        mock_workflow.side_effect = [None, Exception("File processing error"), None]
        
        result = main()
        
        # Should still return success (0) as it continues processing
        self.assertEqual(result, 0)
        
        # Verify all files were attempted
        self.assertEqual(mock_workflow.call_count, 3)
        
        # Verify error was logged
        mock_logger.info.assert_any_call("3 files found to process.")

    @patch('src.hcl_processor.main.parse_args')
    @patch('src.hcl_processor.main.load_system_config')
    @patch('src.hcl_processor.main.load_config')
    @patch('src.hcl_processor.main.setup_logger')
    def test_main_no_files_or_folder(self, mock_setup_logger, mock_load_config, mock_load_system_config, mock_parse_args):
        """Test execution when no files or folder specified"""
        # Setup mocks
        mock_logger = Mock()
        mock_setup_logger.return_value = mock_logger
        
        mock_args = Mock()
        mock_args.config_file = self.config_file
        mock_args.debug = False
        mock_parse_args.return_value = mock_args
        
        mock_load_system_config.return_value = self.sample_system_config
        
        # Config with no files or folder
        empty_config = self.sample_config.copy()
        empty_config["input"]["resource_data"] = {}
        mock_load_config.return_value = empty_config
        
        result = main()
        
        self.assertEqual(result, 0)
        mock_logger.info.assert_called_with("All files processed successfully.")


if __name__ == '__main__':
    unittest.main()
