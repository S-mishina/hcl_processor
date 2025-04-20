import argparse


def parse_args():
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
        type=str,
        help="Enable debug logging (default(INFO) Parameter is False)"
    )
    return parser.parse_args()
