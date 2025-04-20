def get_system_config():
    """
    Returns the system configuration for the HCL processor.
    """
    system_config = {
        "system_prompt": (
            """
            (ENGLISH)\n"
              - Output must strictly be in JSON format.\n"
              - Every required field must be present.\n"
              - The output must end with \"]\".\n"
              - Before printing, validate the JSON structure internally.\n"
            The final result of this should be saved as a json file, so it should not contain unnecessary strings.\n"
            Finally, check the json for the correct form and correct any problems until they are no longer a problem.\n"
            Here's the Alert Design Document in JSON table format for the given Terraform code: Do not include strings such as \"Here's the Alert Design Document in JSON table format for the given Terraform code:\", only json.
          """
        ),
        "system_call": {
            "exit_success": 0,
            "exit_system_config_error": 1,
            "exit_config_error": 2,
            "exit_file_read_error": 3,
            "exit_validation_error": 4,
            "exit_bedrock_error": 5,
            "exit_unknown_error": 99,
        },
        "default_bedrock": {
            "timeout_config": {
                "read_timeout": 120,
                "connect_timeout": 120,
                "retries": {
                    "max_attempts": 5,
                    "mode": "standard",
                },
            },
            "payload": {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0,
                "top_p": 1,
                "top_k": 0,
            },
        },
    }
    return system_config
