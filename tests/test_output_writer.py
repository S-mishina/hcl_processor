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
        # 一時ディレクトリとその中身を再帰的に削除
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_template(self):
        # テストデータ
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
        
        # JSON ファイルの作成
        with open(self.json_path, "w") as f:
            json.dump(test_data, f)

        # 最小構成のconfig
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

        # テスト実行
        output_md("Test Title", config)

        # 結果の検証
        self.assertTrue(os.path.exists(self.md_path))
        with open(self.md_path, "r") as f:
            content = f.read()
            
        # 期待される出力の検証
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
        # テストデータ
        test_data = [{"name": "test", "value": "123"}]
        
        with open(self.json_path, "w") as f:
            json.dump(test_data, f)

        # カスタムテンプレートを使用するconfig
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
        # テストデータ
        test_data = [{"name": "test", "value": "123"}]
        
        with open(self.json_path, "w") as f:
            json.dump(test_data, f)

        # テンプレートファイルの作成
        template_path = os.path.join(self.temp_dir, "test_template.md.j2")
        with open(template_path, "w") as f:
            f.write("## {{ title }}\n{% for item in data %}* {{ item.name }}: {{ item.value }}{% endfor %}")

        # テンプレートファイルを使用するconfig
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
        # テストデータ
        test_data = [{"name": "test"}]
        
        with open(self.json_path, "w") as f:
            json.dump(test_data, f)

        # テンプレートが指定されていないconfig
        config = {
            "output": {
                "json_path": self.json_path,
                "markdown_path": self.md_path
            },
            "schema_columns": ["name"]
        }

        # デフォルトテンプレートが使用されることを確認
        output_md("No Template Test", config)

        with open(self.md_path, "r") as f:
            content = f.read()
            
        self.assertIn("#### No Template Test", content)
        self.assertIn("| name |", content)
        self.assertIn("| test |", content)


if __name__ == "__main__":
    unittest.main()
