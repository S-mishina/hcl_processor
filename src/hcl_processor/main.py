import logging
import os
import sys

from botocore.exceptions import (ClientError, EndpointConnectionError,
                                 ReadTimeoutError)

from .cli import parse_args
from .config_loader import load_config, load_system_config
from .file_processor import run_hcl_file_workflow


def main():
    """
    Main function to load configurations, process files, and handle errors.
    Returns:
        int: Exit code indicating success or failure.
    """
    EXIT_SYSTEM_CONFIG_ERROR = 1
    args = parse_args()
    config_path = args.config_file
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)
    try:
        system_config = load_system_config()
        logger.debug(f"Loaded system_config:\n {system_config}")
    except Exception as e:
        logger.debug(f"{e}")
        logger.exception(f"Failed to load system_config: {type(e).__name__}")
        return EXIT_SYSTEM_CONFIG_ERROR

    try:
        config = load_config(config_path)
    except ValueError as e:
        logger.debug(f"{e}")
        logger.exception(f"Failed to load config: {type(e).__name__}")
        return system_config["system_call"]["exit_config_error"]

    resource = config["input"]["resource_data"]
    try:
        if resource.get("files"):
            logger.info("Processing files...")
            logger.info(f"{len(resource['files'])} files found to process.")
            for file_path in resource["files"]:
                try:
                    run_hcl_file_workflow(file_path, config, system_config)
                except Exception as e:
                    logger.debug(f"{e}")
                    logger.exception(
                        f"Failed processing file {file_path}: {type(e).__name__}"
                    )
                    continue
        elif resource.get("folder"):
            logger.info("Processing folder...")
            logger.info(f"Processing all .tf files in folder: {resource['folder']}")
            for root, _, files in os.walk(resource["folder"]):
                for file_name in files:
                    if file_name.endswith(".tf"):
                        try:
                            run_hcl_file_workflow(
                                os.path.join(root, file_name), config, system_config
                            )
                        except Exception as e:
                            logger.debug(f"{e}")
                            logger.exception(
                                f"Failed processing file {file_name}: {type(e).__name__}"
                            )
                            continue
        if system_config["system_call"]["exit_success"] == 0:
            logger.info("All files processed successfully.")
        else:
            logger.error("Some files failed to process.")
        return system_config["system_call"]["exit_success"]

    except (EndpointConnectionError, ReadTimeoutError, ClientError) as e:
        logger.debug(f"{e}")
        logger.exception(f"Bedrock API error: {type(e).__name__}")
        return system_config["system_call"]["exit_bedrock_error"]

    except Exception as e:
        logger.debug(f"{e}")
        logger.exception(f"Unhandled exception: {type(e).__name__}")
        return system_config["system_call"]["exit_unknown_error"]


if __name__ == "__main__":
    sys.exit(main())
