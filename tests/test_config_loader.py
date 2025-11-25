import os
import tempfile
import unittest
import yaml

from src.hcl_processor.config_loader import load_config, get_default_config


class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config.yaml")

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)

    def _write_config(self, config_data):
        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

    def _get_base_bedrock_config(self):
        return {
            "bedrock": {
                "system_prompt": "test prompt",
                "payload": {
                    "anthropic_version": "test",
                    "max_tokens": 100,
                    "temperature": 0,
                    "top_p": 1,
                    "top_k": 0
                },
                "output_json": {"test": "schema"}
            },
            "input": {
                "resource_data": {
                    "files": ["test.tf"]
                },
                "modules": {
                    "enabled": False
                },
                "local_files": []
            },
            "output": {
                "json_path": "output.json",
                "markdown_path": "output.md"
            }
        }

    def test_load_config_with_bedrock_is_normalized(self):
        """Tests that a valid config with a 'bedrock' key is loaded and normalized correctly."""
        config_data = self._get_base_bedrock_config()
        self._write_config(config_data)

        config = load_config(self.config_path)

        # Verify internal normalization
        self.assertIn("provider_config", config)
        self.assertEqual(config["provider_config"]["name"], "bedrock")
        self.assertEqual(config["provider_config"]["settings"]["system_prompt"], "test prompt")
        self.assertEqual(config["provider_config"]["settings"]["payload"]["max_tokens"], 100)
        
        # Verify that default values are still applied
        default_config = get_default_config()
        self.assertEqual(config["schema_columns"], default_config["schema_columns"])
        self.assertEqual(config["output"].get("template"), default_config["output"]["template"])

    def test_load_config_no_provider(self):
        config_data = {
            "input": { "resource_data": {"files": ["test.tf"]}, "modules": {"enabled": False}, "local_files": [] },
            "output": {"json_path": "output.json", "markdown_path": "output.md"}
        }
        self._write_config(config_data)

        with self.assertRaisesRegex(ValueError, "No LLM provider"):
            load_config(self.config_path)

    def test_load_config_multiple_providers(self):
        config_data = {
            "bedrock": {"system_prompt": "p1", "payload": {"anthropic_version": "v1", "max_tokens": 1, "temperature": 0, "top_p": 1, "top_k": 0}, "output_json": {}},
            "gemini": {"system_prompt": "p2", "payload": {"max_output_tokens": 100, "temperature": 0.5, "top_p": 0.9}, "output_json": {}}, # Gemini config for testing
            "input": { "resource_data": {"files": ["test.tf"]}, "modules": {"enabled": False}, "local_files": [] },
            "output": {"json_path": "output.json", "markdown_path": "output.md"}
        }
        self._write_config(config_data)

        with self.assertRaisesRegex(ValueError, "Multiple LLM providers specified"):
            load_config(self.config_path)

    def test_load_config_output_json_string_conversion(self):
        config_data = self._get_base_bedrock_config()
        config_data["bedrock"]["output_json"] = '{"test_key": "test_value"}'
        self._write_config(config_data)

        config = load_config(self.config_path)
        self.assertEqual(config["provider_config"]["settings"]["output_json"], {"test_key": "test_value"})

    def test_custom_config(self):
        config_data = self._get_base_bedrock_config()
        config_data["output"]["template"] = "# {{ title }}"
        config_data["schema_columns"] = ["name", "value"]
        self._write_config(config_data)

        config = load_config(self.config_path)

        # Verify that custom settings are retained
        self.assertEqual(config["schema_columns"], ["name", "value"])
        self.assertEqual(config["output"]["template"], "# {{ title }}")
        # Verify internal normalization still happens
        self.assertEqual(config["provider_config"]["name"], "bedrock")

    def test_template_file_config(self):
        config_data = self._get_base_bedrock_config()
        config_data["output"]["template"] = {"path": "template.md.j2"}
        self._write_config(config_data)

        config = load_config(self.config_path)

        # Verify that the template file configuration is retained
        self.assertEqual(config["output"]["template"], {"path": "template.md.j2"})
        # Verify internal normalization still happens
        self.assertEqual(config["provider_config"]["name"], "bedrock")

if __name__ == "__main__":
    unittest.main()
