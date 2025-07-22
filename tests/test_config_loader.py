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

    def test_minimal_config(self):
        # 最小限の設定
        config_data = {
            "bedrock": {
                "system_prompt": "test prompt",
                "payload": {
                    "anthropic_version": "test",
                    "max_tokens": 100,
                    "temperature": 0,
                    "top_p": 1,
                    "top_k": 0
                },
                "output_json": {}
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

        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(self.config_path)

        # Verify that default values are applied
        default_config = get_default_config()
        self.assertEqual(
            config["schema_columns"],
            default_config["schema_columns"]
        )
        self.assertEqual(
            config["output"].get("template"),
            default_config["output"]["template"]
        )

    def test_custom_config(self):
        # Custom configuration
        config_data = {
            "bedrock": {
                "system_prompt": "test prompt",
                "payload": {
                    "anthropic_version": "test",
                    "max_tokens": 100,
                    "temperature": 0,
                    "top_p": 1,
                    "top_k": 0
                },
                "output_json": {}
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
                "markdown_path": "output.md",
                "template": "# {{ title }}"
            },
            "schema_columns": ["name", "value"]
        }

        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(self.config_path)

        # Verify that custom settings are retained
        self.assertEqual(config["schema_columns"], ["name", "value"])
        self.assertEqual(config["output"]["template"], "# {{ title }}")

    def test_template_file_config(self):
        # テンプレートファイルを使用する設定
        config_data = {
            "bedrock": {
                "system_prompt": "test prompt",
                "payload": {
                    "anthropic_version": "test",
                    "max_tokens": 100,
                    "temperature": 0,
                    "top_p": 1,
                    "top_k": 0
                },
                "output_json": {}
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
                "markdown_path": "output.md",
                "template": {
                    "path": "template.md.j2"
                }
            }
        }

        with open(self.config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(self.config_path)

        # Verify that the template file configuration is retained
        self.assertEqual(
            config["output"]["template"],
            {"path": "template.md.j2"}
        )


if __name__ == "__main__":
    unittest.main()
