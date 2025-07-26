import argparse


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    Returns:
        Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="CLI tool for Terraform + Bedrock processing"
    )
    parser.add_argument(
        "--config_file",
        type=str,
        required=True,
        help="Path to the main config.yaml file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (default: INFO level)"
    )
    return parser.parse_args()
