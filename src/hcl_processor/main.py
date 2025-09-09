import logging
import os
import sys

from botocore.exceptions import (ClientError, EndpointConnectionError,
                                 ReadTimeoutError)

from .cli import parse_args
from .config_loader import load_config, load_system_config
from .file_processor import run_hcl_file_workflow
from .logger_config import setup_logger, log_exception
from .utils import reset_markdown_file


def main() -> int:
    """
    Main function to load configurations, process files, and handle errors.
    Returns:
        int: Exit code indicating success or failure.
    """
    EXIT_SYSTEM_CONFIG_ERROR = 1
    args = parse_args()
    config_path = args.config_file

    # Setup unified logging
    log_level = logging.DEBUG if args.debug else logging.INFO

    # Setup root hcl_processor logger first for all child loggers
    setup_logger("hcl_processor", level=log_level)

    # Setup main logger
    logger = setup_logger("hcl_processor.main", level=log_level)
    try:
        system_config = load_system_config()
        logger.debug(f"Loaded system_config:\n {system_config}")
    except Exception as e:
        log_exception(logger, e, "Failed to load system_config")
        return EXIT_SYSTEM_CONFIG_ERROR

    try:
        config = load_config(config_path)
    except ValueError as e:
        log_exception(logger, e, f"Failed to load config from {config_path}")
        return system_config["system_call"]["exit_config_error"]

    resource = config["input"]["resource_data"]

    # Reset markdown file once at the start of command execution
    reset_markdown_file(config["output"]["markdown_path"])

    try:
        if resource.get("files"):
            logger.info("Processing files...")
            logger.info(f"{len(resource['files'])} files found to process.")
            for file_path in resource["files"]:
                try:
                    run_hcl_file_workflow(file_path, config, system_config)
                except Exception as e:
                    log_exception(logger, e, f"Failed processing file {file_path}")
                    continue
        elif resource.get("folder"):
            logger.info("Processing folder...")
            logger.info(f"Processing all .tf files in folder: {resource['folder']}")

            # Collect all .tf files in deterministic order
            tf_files = []
            tf_extension = system_config["constants"]["file_processing"]["terraform_extension"]

            for root, _, files in os.walk(resource["folder"]):
                for file_name in sorted(files):  # Sort within directory
                    if file_name.endswith(tf_extension):
                        tf_files.append(os.path.join(root, file_name))

            # Sort all collected files for consistent processing order
            tf_files.sort()

            logger.info(f"{len(tf_files)} files found to process.")

            # Process files in deterministic order
            for file_path in tf_files:
                try:
                    run_hcl_file_workflow(file_path, config, system_config)
                except Exception as e:
                    log_exception(logger, e, f"Failed processing file {file_path}")
                    continue
        if system_config["system_call"]["exit_success"] == 0:
            logger.info("All files processed successfully.")
        else:
            logger.error("Some files failed to process.")
        return system_config["system_call"]["exit_success"]

    except (EndpointConnectionError, ReadTimeoutError, ClientError) as e:
        log_exception(logger, e, "Bedrock API error")
        return system_config["system_call"]["exit_bedrock_error"]

    except Exception as e:
        log_exception(logger, e, "Unhandled exception")
        return system_config["system_call"]["exit_unknown_error"]


if __name__ == "__main__":
    sys.exit(main())
