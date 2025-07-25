import os
import tempfile
import unittest
from unittest.mock import patch

from src.hcl_processor.utils import ensure_directory_exists


class TestUtils(unittest.TestCase):
    """Test cases for utils module"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after tests"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_ensure_directory_exists_with_existing_directory(self):
        """Test ensure_directory_exists with an existing directory"""
        # Create a test file path in existing directory
        test_file = os.path.join(self.test_dir, "test.txt")
        
        # Should not raise any exception
        ensure_directory_exists(test_file)
        
        # Directory should still exist
        self.assertTrue(os.path.exists(self.test_dir))

    def test_ensure_directory_exists_creates_new_directory(self):
        """Test ensure_directory_exists creates new directory"""
        # Create a file path in non-existing directory
        new_dir = os.path.join(self.test_dir, "new_folder", "subfolder")
        test_file = os.path.join(new_dir, "test.txt")
        
        # Directory should not exist initially
        self.assertFalse(os.path.exists(new_dir))
        
        # Call function
        ensure_directory_exists(test_file)
        
        # Directory should now exist
        self.assertTrue(os.path.exists(new_dir))

    def test_ensure_directory_exists_handles_nested_paths(self):
        """Test ensure_directory_exists with deeply nested paths"""
        # Create deeply nested path
        nested_path = os.path.join(
            self.test_dir, "level1", "level2", "level3", "test.txt"
        )
        
        # Call function
        ensure_directory_exists(nested_path)
        
        # All directories should be created
        expected_dir = os.path.join(self.test_dir, "level1", "level2", "level3")
        self.assertTrue(os.path.exists(expected_dir))

    @patch('src.hcl_processor.utils.os.makedirs')
    def test_ensure_directory_exists_handles_permission_error(self, mock_makedirs):
        """Test ensure_directory_exists handles permission errors gracefully"""
        # Mock os.makedirs to raise PermissionError
        mock_makedirs.side_effect = PermissionError("Permission denied")
        
        test_file = os.path.join(self.test_dir, "restricted", "test.txt")
        
        # Should raise PermissionError
        with self.assertRaises(PermissionError):
            ensure_directory_exists(test_file)

    @patch('src.hcl_processor.utils.os.makedirs')
    def test_ensure_directory_exists_handles_other_os_errors(self, mock_makedirs):
        """Test ensure_directory_exists handles other OS errors"""
        # Mock os.makedirs to raise OSError
        mock_makedirs.side_effect = OSError("Disk full")
        
        test_file = os.path.join(self.test_dir, "error_dir", "test.txt")
        
        # Should raise OSError
        with self.assertRaises(OSError):
            ensure_directory_exists(test_file)

    def test_ensure_directory_exists_with_file_name_only(self):
        """Test ensure_directory_exists with just a file name (no directory)"""
        # File name without directory separator
        ensure_directory_exists("test.txt")
        
        # Should not raise any exception
        # Current directory should still exist
        self.assertTrue(os.path.exists("."))

    def test_ensure_directory_exists_with_empty_string(self):
        """Test ensure_directory_exists with empty string"""
        # Should not raise exception
        ensure_directory_exists("")

    def test_ensure_directory_exists_with_root_path(self):
        """Test ensure_directory_exists with root-like path"""
        # Use a path that starts from root but goes to test dir
        root_style_path = os.path.join("/", "tmp", "test_file.txt")
        
        # Should handle without issues (might create or use existing /tmp)
        # We won't actually test creation in /tmp for safety
        try:
            ensure_directory_exists(root_style_path)
        except (PermissionError, OSError):
            # Expected if we don't have permission to create in /tmp
            pass


if __name__ == '__main__':
    unittest.main()
