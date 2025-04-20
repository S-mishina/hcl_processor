import json
import boto3
import logging
from botocore.config import Config
from botocore.exceptions import EndpointConnectionError, ReadTimeoutError, ClientError
import logging
logger = logging.getLogger(__name__)

def aws_bedrock(prompt, modules_data, config, system_config):
    '''
    Call the AWS Bedrock API with the given prompt and configuration.
    Args:
        prompt (str): The prompt to send to the Bedrock API.
        modules_data (str): Additional data for modules.
        config (dict): Configuration for the Bedrock API.
        system_config (dict): System configuration.
    Returns:
        str: The response from the Bedrock API.
    Raises:
        Exception: If the Bedrock API call fails or the response cannot be parsed.
    '''
    timeout_config = {
        "read_timeout": config["bedrock"].get("read_timeout", system_config["default_bedrock"]["timeout_config"]["read_timeout"]),
        "connect_timeout": config["bedrock"].get("connect_timeout", system_config["default_bedrock"]["timeout_config"]["connect_timeout"]),
        "retries": config["bedrock"].get("retries", {"max_attempts": system_config["default_bedrock"]["timeout_config"]["retries"]["max_attempts"], "mode": system_config["default_bedrock"]["timeout_config"]["retries"]["mode"]})
    }
    bedrock_config = Config(**timeout_config)
    profile_name = config.get("aws_profile", "tcpip_power")
    session = boto3.Session(profile_name=profile_name)
    bedrock = session.client('bedrock-runtime', region_name='ap-northeast-1', config=bedrock_config)

    modules_enabled = config.get("modules", {}).get("enabled", True)
    modules_data_str = modules_data if (modules_data is not None) else ""

    final_system_prompt = (
        system_config["system_prompt"] +
        "\n" +
        config["bedrock"]["system_prompt"] +
        "\nSchema:\n" +
        json.dumps(config["bedrock"]["output_json"], ensure_ascii=False)
    )
    final_system_prompt = final_system_prompt.replace("{modules_data}", modules_data_str if modules_enabled else "")

    payload = {
        "system": final_system_prompt,
        "messages": [{"role": "user", "content": prompt}],
        "anthropic_version": config["bedrock"]["payload"].get("anthropic_version", system_config["default_bedrock"]["payload"]["anthropic_version"]),
        "max_tokens": config["bedrock"]["payload"].get("max_tokens", system_config["default_bedrock"]["payload"]["max_tokens"]),
        "temperature": config["bedrock"]["payload"].get("temperature", system_config["default_bedrock"]["payload"]["temperature"]),
        "top_p": config["bedrock"]["payload"].get("top_p", system_config["default_bedrock"]["payload"]["top_p"]),
        "top_k": config["bedrock"]["payload"].get("top_k", system_config["default_bedrock"]["payload"]["top_k"])
    }
    logger.debug(f"Final payload:\n {payload}")
    try:
        response = bedrock.invoke_model(
            modelId=config["bedrock"].get("model_id", "anthropic.claude-3-5-sonnet-20240620-v1:0"),
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )
        logger.debug(f"Bedrock response:\n {response}")
        try:
            content = json.loads(response.get("body").read().decode("utf-8"))
            return content.get("content", [{}])[0].get("text")
        except (AttributeError, json.JSONDecodeError) as e:
            logger.debug(f"{e}")
            logger.error(f"Failed to parse Bedrock response: {type(e).__name__}")
            raise
    except EndpointConnectionError as e:
        logger.debug(f"{e}")
        logger.error(f"Bedrock endpoint connection failed: {type(e).__name__}")
        raise
    except ReadTimeoutError as e:
        logger.debug(f"{e}")
        logger.error(f"Bedrock read timeout: {type(e).__name__}")
        raise
    except ClientError as e:
        logger.debug(f"{e}")
        logger.error(f"Bedrock client error: {type(e).__name__}")
        raise
    except Exception as e:
        logger.debug(f"{e}")
        logger.error(f"Unexpected error during Bedrock invocation: {type(e).__name__}")
        raise
