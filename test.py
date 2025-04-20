import os
import logging
import json
import boto3
from botocore.exceptions import ClientError
import pandas
import pandas
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def read_locals_tf(directory):
  result = []
  for root, dirs, files in os.walk(directory):
    for file_name in files:
      if file_name == "locals.tf":
        file_path = os.path.join(root, file_name)
        with open(file_path, "r") as file:
          relative_path = os.path.relpath(root, directory)
          result.append(f"{relative_path}\n---\n{file.read()}\n")
  return "\n".join(result)

def read_monitor_tf(directory, target_file_name):
  for root, dirs, files in os.walk(directory):
    for file_name in files:
      if file_name == target_file_name:
        file_path = os.path.join(root, file_name)
        with open(file_path, "r") as file:
          return file.read()

def read_modules_tf(directory, target_file_name="modules/monitor/main.tf"):
  for root, dirs, files in os.walk(directory):
    for file_name in files:
      if file_name == os.path.basename(target_file_name):
        file_path = os.path.join(root, file_name)
        relative_path = os.path.relpath(root, directory)
        with open(file_path, "r") as file:
          return f"{relative_path}\n---\n{file.read()}\n"
  return ""

def aws_bedrock(prompt):
  session = boto3.Session(profile_name="tcpip_power")
  bedrock = session.client("bedrock-runtime", region_name="ap-northeast-1")
  model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
  system_prompt = """\
    The following Terraform code defines several calls to the Datadog Monitor module.

    Datadog Alert Design List (Title) Example

    ```
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "array",
      "title": "Datadog Alert Design Schema",
      "description": "Schema for Datadog alert design document",
      "items": {
        "type": "object",
        "properties": {
          "モニター名": {
            "type": "string",
            "description": "モニターの名前"
          },
          "タイプ": {
            "type": "string",
            "description": "モニターのタイプ (例: query alert)"
          },
          "クエリ": {
            "type": "string",
            "description": "Datadogモニターのクエリ"
          },
          "評価期間": {
            "type": "string",
            "description": "評価期間 (例: 5分)"
          },
          "通知先": {
            "type": "string",
            "description": "通知先 (例: Slackチャンネル)"
          },
          "タグ": {
            "type": "string",
            "description": "モニターに関連付けられたタグ"
          },
          "アラートメッセージ": {
            "type": "string",
            "description": "アラート発生時のメッセージ"
          },
          "備考": {
            "type": "string",
            "description": "モニターに関する備考"
          },
          "dev 閾値条件": {
            "type": "string",
            "description": "開発環境の閾値条件"
          },
          "stg 閾値条件": {
            "type": "string",
            "description": "ステージング環境の閾値条件"
          },
          "prd 閾値条件": {
            "type": "string",
            "description": "本番環境の閾値条件"
          }
        },
        "required": [
          "モニター名",
          "タイプ",
          "クエリ",
          "評価期間",
          "通知先",
          "タグ",
          "アラートメッセージ",
          "備考",
          "dev 閾値条件",
          "stg 閾値条件",
          "prd 閾値条件"
        ]
      }
    }
    ````

    ・ Please output an **Alert Design Document (json table format)** for each alert in the following format as described above.
    ・ Do not include env in the title of the monitor.
    ・ The terraform code should be placed with reference to locals.tf.
    ・ The Alert Message column should be extracted from the terraform code and put the values as they are while expanding local. (e.g., message value) )
        sample)
          ```
          message = <<-EOT

          EOT
          ```
          Create the value while expanding local.tf for the contents of
    ・ Output should be in Japanese.
    ・ Create columns for local dev, stg, and prd environments, respectively.
    ・ The final result of this should be saved as a json file, so it should not contain unnecessary strings.
    ・ Here's the Alert Design Document in JSON table format for the given Terraform code: Do not include strings such as "Here's the Alert Design Document in JSON table format for the given Terraform code:", only json.

    Finally, check the json for the correct form and correct any problems until they are no longer a problem.
  """

  payload = {
      "anthropic_version": "bedrock-2023-05-31",
      "system": system_prompt,
      "messages": [
          {"role": "user", "content": prompt}
      ],
      "max_tokens": 4096,
      "temperature": 0,
      "top_p": 1,
      "top_k": 0,
  }
  try:
      response = bedrock.invoke_model(
          modelId=model_id,
          body=json.dumps(payload),
          contentType="application/json",
          accept="application/json"
      )
  except ClientError as e:
      logger.error(f"Bedrock model invocation failed: {e}")
      return None
  content = json.loads(response.get("body").read().decode("utf-8"))
  return content.get("content", [{}])[0].get("text")

def clean_cell(cell):
    if isinstance(cell, str):
        cell = cell.replace("\n", "<br>").replace("|", "\\|")
        cell = cell.replace("{", "\\{").replace("}", "\\}")
        cell = re.sub(r"(\$\{.*\})(<br>|$)", r"\1 \2", cell)
        cell = re.sub(r"(<br>)", r" \1 ", cell)
        return cell.strip()
    return cell

def output_md():
with open("output.json", "r", encoding="utf-8") as file:
    raw_data = file.read()
data = json.loads(raw_data)
if isinstance(data, str):
    data = json.loads(data)
if isinstance(data, dict):
    df = pd.DataFrame([data])
elif isinstance(data, list):
    df = pd.DataFrame(data)
else:
    raise ValueError("The format of the JSON data cannot be converted to a DataFrame")

df = df.applymap(clean_cell)

schema_columns = [
    "モニター名", "タイプ", "クエリ", "評価期間", "通知先", "タグ",
    "アラートメッセージ", "備考", "dev 閾値条件", "stg 閾値条件", "prd 閾値条件"
]
df = df[schema_columns]

markdown_table = df.to_markdown(index=False)

with open("output.md", "w", encoding="utf-8") as md_file:
    md_file.write(markdown_table)

print("Saved to Markdown file: output.md")


if __name__ == "__main__":
  target_directory = "test_data"
  locals_str=read_locals_tf(target_directory)
  target_file_name = "aurora_monitor.tf"
  monitor_str=read_monitor_tf(target_directory, target_file_name)
  modules_str=read_modules_tf(target_directory)
  combined_str = f"{locals_str}\n{monitor_str}\n{modules_str}\n"
  output=aws_bedrock(combined_str)
  logger.info(output)

  output_file = "output.json"
  with open(output_file, "w", encoding="utf-8") as f:
      json.dump(output, f, ensure_ascii=False, indent=4)

