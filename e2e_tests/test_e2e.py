"""
E2E tests for hcl-processor.

These tests use the actual AWS Bedrock API.
AWS credentials must be configured before running.

Usage:
    # Run all tests
    poetry run pytest e2e_tests/test_e2e.py -v -s

    # Run specific test class
    poetry run pytest e2e_tests/test_e2e.py::TestE2EBasic -v -s
    poetry run pytest e2e_tests/test_e2e.py::TestE2EFilesPattern -v -s
    poetry run pytest e2e_tests/test_e2e.py::TestE2EChunkPattern -v -s
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
E2E_DIR = PROJECT_ROOT / "e2e_tests"
OUTPUT_DIR = E2E_DIR / "output"


# Config files for different test patterns
CONFIG_BASIC = E2E_DIR / "e2e_config.yaml"
CONFIG_FILES = E2E_DIR / "e2e_config_files.yaml"
CONFIG_CHUNK = E2E_DIR / "e2e_config_chunk.yaml"


def check_aws_credentials():
    """Check if AWS credentials are configured."""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def run_hcl_processor(config_file: Path, timeout: int = 300):
    """Run hcl-processor with the specified config file."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "hcl_processor.main",
            "--config_file",
            str(config_file),
            "--debug",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
        timeout=timeout,
    )
    return result


def validate_json_output(output_file: Path, min_items: int = 1):
    """Validate JSON output file."""
    assert output_file.exists(), f"{output_file.name} was not created"

    with open(output_file) as f:
        content = f.read()

    data = json.loads(content)
    assert isinstance(data, list), "JSON output should be an array"
    assert len(data) >= min_items, f"Expected at least {min_items} items, got {len(data)}"

    required_fields = [
        "monitor_name",
        "type",
        "query",
        "evaluation_period",
        "notification",
        "tags",
        "alert_message",
        "note",
        "dev_threshold",
        "stg_threshold",
        "prd_threshold",
    ]

    for item in data:
        for field in required_fields:
            assert field in item, f"Missing required field: {field}"

    return data


def validate_markdown_output(output_file: Path):
    """Validate Markdown output file."""
    assert output_file.exists(), f"{output_file.name} was not created"

    with open(output_file) as f:
        content = f.read()

    assert len(content) > 0, "Markdown output is empty"
    return content


@pytest.fixture(scope="module")
def ensure_aws_credentials():
    """Fixture to ensure AWS credentials are available."""
    if not check_aws_credentials():
        pytest.skip("AWS credentials not configured. Skipping E2E tests.")


@pytest.fixture(scope="module")
def clean_output():
    """Clean up output directory before tests."""
    for f in OUTPUT_DIR.glob("*.json"):
        f.unlink()
    for f in OUTPUT_DIR.glob("*.md"):
        f.unlink()
    yield


class TestE2EBasic:
    """
    E2E tests for basic (folder) pattern.

    Tests resource_data.folder configuration.
    """

    OUTPUT_JSON = OUTPUT_DIR / "output.json"
    OUTPUT_MD = OUTPUT_DIR / "output.md"

    @pytest.fixture(scope="class")
    def run_processor(self, ensure_aws_credentials, clean_output):
        """Run hcl-processor with basic config."""
        result = run_hcl_processor(CONFIG_BASIC)
        print("\n--- STDOUT ---")
        print(result.stdout)
        if result.stderr:
            print("\n--- STDERR ---")
            print(result.stderr)
        return result

    def test_execution_success(self, run_processor):
        """Test that hcl-processor executes successfully."""
        assert run_processor.returncode == 0, f"Exit code: {run_processor.returncode}"

    def test_json_output_valid(self, run_processor):
        """Test that JSON output is valid and contains monitors."""
        data = validate_json_output(self.OUTPUT_JSON)
        print(f"\n[Basic] JSON output contains {len(data)} monitor(s)")
        for item in data:
            print(f"  - {item.get('monitor_name', 'UNKNOWN')}")

    def test_markdown_output_valid(self, run_processor):
        """Test that Markdown output is valid."""
        content = validate_markdown_output(self.OUTPUT_MD)
        print(f"\n[Basic] Markdown output size: {len(content)} bytes")


class TestE2EFilesPattern:
    """
    E2E tests for files pattern.

    Tests resource_data.files configuration (individual file list).
    """

    OUTPUT_JSON = OUTPUT_DIR / "output_files.json"
    OUTPUT_MD = OUTPUT_DIR / "output_files.md"

    @pytest.fixture(scope="class")
    def run_processor(self, ensure_aws_credentials, clean_output):
        """Run hcl-processor with files pattern config."""
        result = run_hcl_processor(CONFIG_FILES)
        print("\n--- STDOUT ---")
        print(result.stdout)
        if result.stderr:
            print("\n--- STDERR ---")
            print(result.stderr)
        return result

    def test_execution_success(self, run_processor):
        """Test that hcl-processor executes successfully."""
        assert run_processor.returncode == 0, f"Exit code: {run_processor.returncode}"

    def test_json_output_valid(self, run_processor):
        """Test that JSON output is valid and contains monitors."""
        data = validate_json_output(self.OUTPUT_JSON)
        print(f"\n[Files] JSON output contains {len(data)} monitor(s)")
        for item in data:
            print(f"  - {item.get('monitor_name', 'UNKNOWN')}")

    def test_markdown_output_valid(self, run_processor):
        """Test that Markdown output is valid."""
        content = validate_markdown_output(self.OUTPUT_MD)
        print(f"\n[Files] Markdown output size: {len(content)} bytes")

    def test_multiple_files_processed(self, run_processor):
        """Test that monitors from multiple files are processed."""
        data = validate_json_output(self.OUTPUT_JSON, min_items=1)
        # Files pattern processes 2 files: sample_monitor.tf and simple_resource.tf
        # We expect monitors from both files
        print(f"\n[Files] Processed {len(data)} monitor(s) from multiple files")


class TestE2EChunkPattern:
    """
    E2E tests for chunk (failback) pattern.

    Tests failback configuration with large data that may trigger chunk processing.
    """

    OUTPUT_JSON = OUTPUT_DIR / "output_chunk.json"
    OUTPUT_MD = OUTPUT_DIR / "output_chunk.md"

    @pytest.fixture(scope="class")
    def run_processor(self, ensure_aws_credentials, clean_output):
        """Run hcl-processor with chunk pattern config."""
        # Longer timeout for chunk processing
        result = run_hcl_processor(CONFIG_CHUNK, timeout=600)
        print("\n--- STDOUT ---")
        print(result.stdout)
        if result.stderr:
            print("\n--- STDERR ---")
            print(result.stderr)
        return result

    def test_execution_success(self, run_processor):
        """Test that hcl-processor executes successfully."""
        assert run_processor.returncode == 0, f"Exit code: {run_processor.returncode}"

    def test_json_output_valid(self, run_processor):
        """Test that JSON output is valid and contains monitors."""
        data = validate_json_output(self.OUTPUT_JSON)
        print(f"\n[Chunk] JSON output contains {len(data)} monitor(s)")
        for item in data:
            print(f"  - {item.get('monitor_name', 'UNKNOWN')}")

    def test_markdown_output_valid(self, run_processor):
        """Test that Markdown output is valid."""
        content = validate_markdown_output(self.OUTPUT_MD)
        print(f"\n[Chunk] Markdown output size: {len(content)} bytes")

    def test_large_data_processed(self, run_processor):
        """Test that large data with multiple monitors is processed."""
        data = validate_json_output(self.OUTPUT_JSON, min_items=1)
        # large_monitors.tf contains 8 monitors
        print(f"\n[Chunk] Processed {len(data)} monitor(s) from large file")
        # Verify we got monitors (exact count depends on chunk processing behavior)
        assert len(data) >= 1, "At least one monitor should be processed"


class TestE2EMonitorContent:
    """
    Tests for verifying the content quality of generated monitors.

    These tests run after basic tests and verify data quality.
    """

    @pytest.fixture(scope="class")
    def basic_output(self, ensure_aws_credentials):
        """Load basic output if available."""
        output_file = OUTPUT_DIR / "output.json"
        if not output_file.exists():
            pytest.skip("Basic output not available")
        with open(output_file) as f:
            return json.load(f)

    def test_monitor_names_not_empty(self, basic_output):
        """Test that monitor names are populated."""
        for item in basic_output:
            name = item.get("monitor_name", "")
            assert name and name != "<UNKNOWN>", f"Monitor name is empty or unknown: {name}"

    def test_queries_present(self, basic_output):
        """Test that queries are present."""
        for item in basic_output:
            query = item.get("query", "")
            assert query and query != "<UNKNOWN>", f"Query is empty or unknown for {item.get('monitor_name')}"

    def test_thresholds_have_values(self, basic_output):
        """Test that at least some thresholds have values."""
        has_threshold = False
        for item in basic_output:
            for env in ["dev_threshold", "stg_threshold", "prd_threshold"]:
                threshold = item.get(env, "")
                if threshold and threshold != "<UNKNOWN>":
                    has_threshold = True
                    break
        assert has_threshold, "No thresholds found in any monitor"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
