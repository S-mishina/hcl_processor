#!/usr/bin/env python3
"""
Model Compatibility Checker for hcl-processor.

This tool checks which AWS Bedrock models are compatible with hcl-processor
by actually running hcl-processor with each model.

Usage:
    # Check Anthropic models (default)
    python tools/model_checker.py

    # Check specific provider
    python tools/model_checker.py --provider openai
    python tools/model_checker.py --provider amazon
    python tools/model_checker.py --provider all

    # Check specific models
    python tools/model_checker.py --models anthropic.claude-3-5-sonnet-20241022-v2:0

    # Check with specific AWS region
    python tools/model_checker.py --region us-west-2

    # Output as JSON
    python tools/model_checker.py --output json

Supported providers:
    - anthropic: Claude models
    - openai: GPT-OSS models
    - amazon: Nova models
    - mistral: Mistral/Ministral models
    - deepseek: DeepSeek models
    - qwen: Qwen models
    - other: Google, NVIDIA, MiniMax, Moonshot
    - all: All models
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml


class ModelStatus(Enum):
    """Model check result status."""

    SUCCESS = "success"
    ACCESS_DENIED = "access_denied"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ModelCheckResult:
    """Result of a model compatibility check."""

    model_id: str
    status: ModelStatus
    message: str
    exit_code: Optional[int] = None
    execution_time_sec: Optional[float] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


# Known AWS Bedrock models (ap-northeast-1)
# Text generation models only (excluding embed/rerank/image/audio models)

ANTHROPIC_MODELS = [
    # Claude 4.5
    "anthropic.claude-opus-4-5-20251101-v1:0",
    "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    # Claude 4
    "anthropic.claude-sonnet-4-20250514-v1:0",
    # Claude 3.7
    "anthropic.claude-3-7-sonnet-20250219-v1:0",
    # Claude 3.5
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    # Claude 3
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0:28k",
    "anthropic.claude-3-sonnet-20240229-v1:0:200k",
    "anthropic.claude-3-haiku-20240307-v1:0",
]

OPENAI_MODELS = [
    "openai.gpt-oss-120b-1:0",
    "openai.gpt-oss-20b-1:0",
]

AMAZON_MODELS = [
    "amazon.nova-pro-v1:0",
    "amazon.nova-lite-v1:0",
    "amazon.nova-micro-v1:0",
    "amazon.nova-2-lite-v1:0",
]

MISTRAL_MODELS = [
    "mistral.mistral-large-3-675b-instruct",
    "mistral.magistral-small-2509",
    "mistral.ministral-3-14b-instruct",
    "mistral.ministral-3-8b-instruct",
    "mistral.ministral-3-3b-instruct",
]

DEEPSEEK_MODELS = [
    "deepseek.v3-v1:0",
]

QWEN_MODELS = [
    "qwen.qwen3-235b-a22b-2507-v1:0",
    "qwen.qwen3-coder-480b-a35b-v1:0",
    "qwen.qwen3-coder-30b-a3b-v1:0",
    "qwen.qwen3-32b-v1:0",
]

OTHER_MODELS = [
    "google.gemma-3-27b-it",
    "google.gemma-3-12b-it",
    "google.gemma-3-4b-it",
    "nvidia.nemotron-nano-3-30b",
    "nvidia.nemotron-nano-12b-v2",
    "nvidia.nemotron-nano-9b-v2",
    "minimax.minimax-m2",
    "moonshot.kimi-k2-thinking",
]

# All models combined
ALL_MODELS = (
    ANTHROPIC_MODELS
    + OPENAI_MODELS
    + AMAZON_MODELS
    + MISTRAL_MODELS
    + DEEPSEEK_MODELS
    + QWEN_MODELS
    + OTHER_MODELS
)

# Provider groups for filtering
MODEL_GROUPS = {
    "anthropic": ANTHROPIC_MODELS,
    "openai": OPENAI_MODELS,
    "amazon": AMAZON_MODELS,
    "mistral": MISTRAL_MODELS,
    "deepseek": DEEPSEEK_MODELS,
    "qwen": QWEN_MODELS,
    "other": OTHER_MODELS,
    "all": ALL_MODELS,
}

PROJECT_ROOT = Path(__file__).parent.parent
E2E_DIR = PROJECT_ROOT / "e2e_tests"
BASE_CONFIG = E2E_DIR / "e2e_config.yaml"


def load_base_config() -> dict:
    """Load the base E2E config file."""
    with open(BASE_CONFIG) as f:
        return yaml.safe_load(f)


def create_test_config(
    base_config: dict, model_id: str, region: str, output_dir: Path
) -> Path:
    """Create a temporary config file with the specified model."""
    config = base_config.copy()

    # Update model and region
    config["bedrock"]["model_id"] = model_id
    config["bedrock"]["aws_region"] = region

    # Update output paths to use temp directory
    config["output"]["json_path"] = str(output_dir / "output.json")
    config["output"]["markdown_path"] = str(output_dir / "output.md")

    # Write temp config
    config_path = output_dir / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    return config_path


def run_hcl_processor(
    config_path: Path, timeout: int = 180
) -> tuple[int, str, str, float]:
    """Run hcl-processor with the specified config."""
    import time

    start_time = time.time()

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "hcl_processor.main",
                "--config_file",
                str(config_path),
            ],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
            timeout=timeout,
        )
        elapsed = time.time() - start_time
        return result.returncode, result.stdout, result.stderr, elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        return -1, "", "Timeout", elapsed


def check_model(
    model_id: str, region: str, base_config: dict, timeout: int
) -> ModelCheckResult:
    """Check if a model works with hcl-processor."""

    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)

        # Create config for this model
        config_path = create_test_config(base_config, model_id, region, output_dir)

        # Run hcl-processor
        exit_code, stdout, stderr, elapsed = run_hcl_processor(config_path, timeout)

        # Analyze result
        if exit_code == 0:
            # Check if output was actually created
            json_output = output_dir / "output.json"
            if json_output.exists():
                try:
                    with open(json_output) as f:
                        data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return ModelCheckResult(
                            model_id=model_id,
                            status=ModelStatus.SUCCESS,
                            message=f"Generated {len(data)} monitor(s)",
                            exit_code=exit_code,
                            execution_time_sec=round(elapsed, 2),
                            stdout=stdout,
                            stderr=stderr,
                        )
                except json.JSONDecodeError:
                    pass

            return ModelCheckResult(
                model_id=model_id,
                status=ModelStatus.VALIDATION_ERROR,
                message="Output validation failed",
                exit_code=exit_code,
                execution_time_sec=round(elapsed, 2),
                stdout=stdout,
                stderr=stderr,
            )

        elif exit_code == -1:
            return ModelCheckResult(
                model_id=model_id,
                status=ModelStatus.TIMEOUT,
                message=f"Timeout after {timeout}s",
                exit_code=exit_code,
                execution_time_sec=round(elapsed, 2),
                stdout=stdout,
                stderr=stderr,
            )

        else:
            # Check for access denied
            combined_output = stdout + stderr
            if "AccessDeniedException" in combined_output:
                return ModelCheckResult(
                    model_id=model_id,
                    status=ModelStatus.ACCESS_DENIED,
                    message="Model access denied",
                    exit_code=exit_code,
                    execution_time_sec=round(elapsed, 2),
                    stdout=stdout,
                    stderr=stderr,
                )

            # Extract error message
            error_msg = stderr.strip().split("\n")[-1] if stderr else "Unknown error"
            return ModelCheckResult(
                model_id=model_id,
                status=ModelStatus.ERROR,
                message=error_msg[:100],
                exit_code=exit_code,
                execution_time_sec=round(elapsed, 2),
                stdout=stdout,
                stderr=stderr,
            )


def print_results_table(results: list[ModelCheckResult]):
    """Print results as a formatted table."""
    status_symbols = {
        ModelStatus.SUCCESS: "\033[92m✓\033[0m",
        ModelStatus.ACCESS_DENIED: "\033[93m⊘\033[0m",
        ModelStatus.VALIDATION_ERROR: "\033[91m✗\033[0m",
        ModelStatus.TIMEOUT: "\033[93m⏱\033[0m",
        ModelStatus.ERROR: "\033[91m!\033[0m",
    }

    print("\n" + "=" * 90)
    print("hcl-processor Model Compatibility Check Results")
    print("=" * 90)

    print(f"{'Status':<8} {'Model ID':<50} {'Time (s)':<10} {'Result':<20}")
    print("-" * 90)

    for result in results:
        symbol = status_symbols.get(result.status, "?")
        time_str = (
            f"{result.execution_time_sec:.1f}" if result.execution_time_sec else "-"
        )
        msg = result.message[:20] if result.message else ""
        print(f"{symbol:<8} {result.model_id:<50} {time_str:<10} {msg:<20}")

    print("-" * 90)

    success_count = sum(1 for r in results if r.status == ModelStatus.SUCCESS)
    access_denied_count = sum(
        1 for r in results if r.status == ModelStatus.ACCESS_DENIED
    )
    error_count = sum(
        1
        for r in results
        if r.status
        in [ModelStatus.VALIDATION_ERROR, ModelStatus.ERROR, ModelStatus.TIMEOUT]
    )

    print(
        f"\nSummary: {success_count} working, {access_denied_count} access denied, {error_count} failed"
    )
    print("=" * 90)

    # Detailed messages for non-success
    failed_results = [r for r in results if r.status != ModelStatus.SUCCESS]
    if failed_results:
        print("\nDetails:")
        for result in failed_results:
            print(f"  [{result.status.value}] {result.model_id}")
            print(f"    → {result.message}")


def print_results_json(results: list[ModelCheckResult]):
    """Print results as JSON."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "results": [
            {
                "model_id": r.model_id,
                "status": r.status.value,
                "message": r.message,
                "exit_code": r.exit_code,
                "execution_time_sec": r.execution_time_sec,
            }
            for r in results
        ],
        "summary": {
            "total": len(results),
            "success": sum(1 for r in results if r.status == ModelStatus.SUCCESS),
            "access_denied": sum(
                1 for r in results if r.status == ModelStatus.ACCESS_DENIED
            ),
            "errors": sum(
                1
                for r in results
                if r.status
                in [
                    ModelStatus.VALIDATION_ERROR,
                    ModelStatus.ERROR,
                    ModelStatus.TIMEOUT,
                ]
            ),
        },
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Check AWS Bedrock model compatibility by running hcl-processor"
    )
    parser.add_argument(
        "--region",
        default="ap-northeast-1",
        help="AWS region (default: ap-northeast-1)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout per model in seconds (default: 180)",
    )
    parser.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Specific model IDs to check",
    )
    parser.add_argument(
        "--provider",
        choices=[
            "anthropic",
            "openai",
            "amazon",
            "mistral",
            "deepseek",
            "qwen",
            "other",
            "all",
        ],
        default="anthropic",
        help="Provider to check (default: anthropic)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed output (stdout/stderr) for each model",
    )

    args = parser.parse_args()

    # Check base config exists
    if not BASE_CONFIG.exists():
        print(f"Error: Base config not found: {BASE_CONFIG}", file=sys.stderr)
        sys.exit(1)

    # Load base config
    base_config = load_base_config()

    # Select models to check
    if args.models:
        models_to_check = args.models
    else:
        models_to_check = MODEL_GROUPS.get(args.provider, ANTHROPIC_MODELS)

    print(f"Checking {len(models_to_check)} model(s) with hcl-processor...")
    print(f"Region: {args.region}")
    print(f"Timeout: {args.timeout}s per model")
    print()

    # Check each model
    results = []
    for i, model_id in enumerate(models_to_check, 1):
        print(f"[{i}/{len(models_to_check)}] Testing {model_id}...", flush=True)
        result = check_model(model_id, args.region, base_config, args.timeout)
        results.append(result)

        if result.status == ModelStatus.SUCCESS:
            print(
                f"  → \033[92mOK\033[0m ({result.execution_time_sec:.1f}s) - {result.message}"
            )
        elif result.status == ModelStatus.ACCESS_DENIED:
            print("  → \033[93mAccess Denied\033[0m")
        else:
            print(f"  → \033[91mFailed\033[0m - {result.message}")

        # Show debug output
        if args.debug and result.status != ModelStatus.SUCCESS:
            print("\n  --- STDOUT ---")
            if result.stdout:
                for line in result.stdout.strip().split("\n")[-20:]:
                    print(f"  {line}")
            print("\n  --- STDERR ---")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-20:]:
                    print(f"  {line}")
            print()

    # Output results
    if args.output == "json":
        print_results_json(results)
    else:
        print_results_table(results)

    # Exit code
    has_working = any(r.status == ModelStatus.SUCCESS for r in results)
    sys.exit(0 if has_working else 1)


if __name__ == "__main__":
    main()
