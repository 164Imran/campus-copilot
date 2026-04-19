# bedrock_client.py
import boto3, json, os
from dotenv import load_dotenv
load_dotenv()

bedrock = boto3.client(
    "bedrock-runtime",
    region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1")
)

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5")

def call_claude(prompt: str, system_prompt: str = None, max_tokens: int = 500) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system_prompt:
        body["system"] = system_prompt

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body)
    )
    return json.loads(response["body"].read())["content"][0]["text"]

def call_claude_stream(prompt: str, system_prompt: str = None, max_tokens: int = 500):
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system_prompt:
        body["system"] = system_prompt

    response = bedrock.invoke_model_with_response_stream(
        modelId=MODEL_ID,
        body=json.dumps(body)
    )
    for event in response.get('body'):
        chunk = json.loads(event['chunk']['bytes'])
        if chunk['type'] == 'content_block_delta':
            if chunk['delta']['type'] == 'text_delta':
                yield chunk['delta']['text']


# Test direct
if __name__ == "__main__":
    print("Test Bedrock...")
    result = call_claude("Dis bonjour en une phrase")
    print(f"✅ Réponse : {result}")
