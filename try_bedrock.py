import os
import boto3

client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-2"))
resp = client.converse(
    modelId=os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
    messages=[{"role": "user", "content": [{"text": "Say hello in five words."}]}],
)
print(resp["output"]["message"]["content"][0]["text"])