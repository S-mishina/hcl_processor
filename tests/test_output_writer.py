import json
import os
import shutil
import tempfile
import unittest

from src.hcl_processor.output_writer import output_md


class TestOutputWriter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.json_path = os.path.join(self.temp_dir, "test.json")
        self.md_path = os.path.join(self.temp_dir, "test.md")

    def tearDown(self):
        # Recursively delete the temporary directory and its contents
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_template(self):
        # Test data
        test_data = [
            {
                "name": "test_alert",
                "description": "test description",
                "severity": "high",
                "threshold": "80%",
                "evaluation_period": "5m",
                "extra_field": "should not appear"
            }
        ]
        
        # Create a JSON file
        with open(self.json_path, "w") as f:
            json.dump(test_data, f)

        # Minimal configuration
        config = {
            "output": {
                "json_path": self.json_path,
                "markdown_path": self.md_path
            },
            "schema_columns": [
                "name",
                "description",
                "severity",
                "threshold",
                "evaluation_period"
            ]
        }

        # Execute the test
        output_md("Test Title", config)

        # Verify the results
        self.assertTrue(os.path.exists(self.md_path))
        with open(self.md_path, "r") as f:
            content = f.read()
            
        # Verify the expected output
        expected_header = "| " + " | ".join(config["schema_columns"]) + " |"
        expected_row = "| " + " | ".join([
            "test_alert",
            "test description",
            "high",
            "80%",
            "5m"
        ]) + " |"
        
        self.assertIn("#### Test Title", content)
        self.assertIn(expected_header, content)
        self.assertIn(expected_row, content)
        self.assertNotIn("extra_field", content)

    def test_custom_template_string(self):
        # Test data
        test_data = [{"name": "test", "value": "123"}]
        
        with open(self.json_path, "w") as f:
            json.dump(test_data, f)

        # Config using a custom template
        config = {
            "output": {
                "json_path": self.json_path,
                "markdown_path": self.md_path,
                "template": "# {{ title }}\n{% for item in data %}* {{ item.name }}: {{ item.value }}{% endfor %}"
            },
            "schema_columns": ["name", "value"]
        }

        output_md("Custom Test", config)

        with open(self.md_path, "r") as f:
            content = f.read()
            
        self.assertIn("# Custom Test", content)
        self.assertIn("* test: 123", content)

    def test_custom_template_file(self):
        # Test data
        test_data = [{"name": "test", "value": "123"}]
        
        with open(self.json_path, "w") as f:
            json.dump(test_data, f)

        # Create the template file
        template_path = os.path.join(self.temp_dir, "test_template.md.j2")
        with open(template_path, "w") as f:
            f.write("## {{ title }}\n{% for item in data %}* {{ item.name }}: {{ item.value }}{% endfor %}")

        # Config using a template file
        config = {
            "output": {
                "json_path": self.json_path,
                "markdown_path": self.md_path,
                "template": {"path": template_path}
            },
            "schema_columns": ["name", "value"]
        }

        output_md("File Template Test", config)

        with open(self.md_path, "r") as f:
            content = f.read()
            
        self.assertIn("## File Template Test", content)
        self.assertIn("* test: 123", content)

    def test_missing_template(self):
        # Test data
        test_data = [{"name": "test"}]
        
        with open(self.json_path, "w") as f:
            json.dump(test_data, f)

        # Config where no template is specified
        config = {
            "output": {
                "json_path": self.json_path,
                "markdown_path": self.md_path
            },
            "schema_columns": ["name"]
        }

        # Verify that the default template is used
        output_md("No Template Test", config)

        with open(self.md_path, "r") as f:
            content = f.read()
            
        self.assertIn("#### No Template Test", content)
        self.assertIn("| name |", content)
        self.assertIn("| test |", content)


if __name__ == "__main__":
    unittest.main()
