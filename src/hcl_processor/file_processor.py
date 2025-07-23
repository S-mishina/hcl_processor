import json
import logging
import os

import hcl2

from .bedrock_client import aws_bedrock
from .output_writer import output_md, validate_output_json

logger = logging.getLogger(__name__)


def run_hcl_file_workflow(file_path, config, system_config):
    """
    Process a hcl file and generate a JSON output.
    Args:
        file_path (str): Path to the hcl file.
        config (dict): Configuration for processing.
        system_config (dict): System configuration.
    Raises:
        FileNotFoundError: If the hcl file does not exist or is empty.
        ValueError: If the hcl file cannot be parsed.
    """
    logger.info(f"Processing {file_path}")
    locals_str = read_local_files(config["input"]["local_files"])
    hcl_raw, _ = read_tf_file(file_path)
    if hcl_raw is None:
        logger.warning(f"File not found or empty: {file_path}")
        raise FileNotFoundError(f"File not found or empty: {file_path}")
    if config["input"]["modules"].get("enabled", True):
        modules_raw, _ = read_tf_file(config["input"]["modules"]["path"])
    else:
        modules_raw = None
    try:
        resource_dict = hcl2.loads(hcl_raw)
    except Exception as e:
        logger.debug(f"{e}")
        logger.error(f"Error parsing HCL file {file_path}: {type(e).__name__}")
        raise
    try:
        combined_str = f"{locals_str}\n ---resource hcl \n {resource_dict}\n"
        logger.debug(f"Combined string:\n {combined_str}")
        output_str = aws_bedrock(combined_str, modules_raw, config, system_config)
        logger.debug(f"Output string:\n {output_str}")
        validated_output = validate_output_json(
            output_str, config["bedrock"]["output_json"]
        )
        logger.debug(f"Validated output:\n {validated_output}")
        os.makedirs(os.path.dirname(config["output"]["json_path"]), exist_ok=True)
        try:
            # TODO: Need to consider creating a temporary file.
            with open(config["output"]["json_path"], "w", encoding="utf-8") as f:
                json.dump(validated_output, f, ensure_ascii=False, indent=4)
                logger.info(
                    f"Successfully wrote JSON output to {json.dump(validated_output, f, ensure_ascii=False, indent=4)}"
                )
        except Exception as e:
            logger.debug(f"{e}")
            logger.error(f"Error writing JSON output: {type(e).__name__}")
            raise
        logger.info(f"Successfully processed file: {file_path}")
        output_md(os.path.basename(file_path).replace(".tf", ""), config)
    except json.decoder.JSONDecodeError:
        logger.error("Prompt too large or malformed JSON, retrying in chunks...")
        hcl_output = []
        # TODO: Need to review implementation
        if config["input"]["failback"]["enabled"]:
            module_name = get_modules_name(resource_dict)
            if config["input"]["failback"]["type"] == "resource":
                # TODO: Not yet guaranteed to work
                resources = resource_dict["resource"]
            else:
                resources = resource_dict["module"][0][module_name][
                    config["input"]["failback"]["options"]["target"]
                ]
            try:
                for resource in resources:
                    combined_str = f"{locals_str}\n{resource}\n"
                    partial_output = aws_bedrock(
                        combined_str, modules_raw, config, system_config
                    )
                    validated_partial = validate_output_json(
                        partial_output, config["bedrock"]["output_json"]
                    )
                    hcl_output.append(validated_partial)
            except Exception as e:
                logger.debug(f"{e}")
                logger.error(f"Error processing resource chunk: {type(e).__name__}")
                pass
            flattened_list = []
            for json_obj in hcl_output:
                try:
                    flattened_list.extend(json_obj)
                except Exception as e:
                    logger.debug(f"{e}")
                    logger.error(
                        f"Error extending flattened list with: {json_obj}, error: {type(e).__name__}"
                    )

            with open(config["output"]["json_path"], "w", encoding="utf-8") as f:
                json.dump(flattened_list, f, ensure_ascii=False, indent=4)
            output_md(os.path.basename(file_path).replace(".tf", ""), config)
        else:
            logger.error("Failback is not enabled, skipping chunk processing.")
            if not logger.isEnabledFor(logging.DEBUG):
                return
            else:
                raise


def read_tf_file(file_path):
    """
    Read a Terraform file and return its content.
    Args:
        file_path (str): Path to the Terraform file.
    Returns:
        str: Content of the Terraform file.
        str: Directory of the Terraform file.
    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read(), os.path.dirname(file_path)
    raise FileNotFoundError(f"File not found: {file_path}")


def read_local_files(local_files):
    """
    Read local files and return their content.
    Args:
        local_files (list): List of local files to read.
    Returns:
        str: Content of the local files.
    Raises:
        FileNotFoundError: If any local file does not exist.
    """
    result = []
    for entry in local_files:
        for env, path in entry.items():
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        result.append(f"{env}\n---\n{hcl2.loads(f.read())}\n")
                except Exception as e:
                    logger.error(f"Error reading local file {path}: {type(e).__name__}")
                    raise
            else:
                raise FileNotFoundError(f"Local file not found: {path}")
    return "\n".join(result)


def get_modules_name(resource_dict, search_resource="monitors"):
    """
    Extract the module name from the hcl dictionary.
    Args:
        hcl_dict (dict): The hcl dictionary.
    Returns:
        str: The module name.
    Raises:
        ValueError: If no module name is found.
    """
    for resource_name, resource_data in resource_dict.get("module", [{}])[0].items():
        if search_resource in resource_data:
            logger.info(f"resource_name: {resource_name}")
            return resource_name
    raise ValueError("No module name found in hcl_dict")
