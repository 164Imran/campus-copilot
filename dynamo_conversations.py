# dynamo_conversations.py
import boto3
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TABLE_NAME = "campus-copilot-conversations"
CONV_MAX_TURNS = 6  # paires (user + assistant) gardées par session

_client = boto3.client("dynamodb", region_name=os.getenv("AWS_DEFAULT_REGION", "eu-central-1"))


def _to_dynamo(messages: list) -> dict:
    return {"S": json.dumps(messages, ensure_ascii=False)}


def _from_dynamo(attr: dict) -> list:
    return json.loads(attr["S"])


def get_conversation(session_id: str) -> list:
    try:
        r = _client.get_item(
            TableName=TABLE_NAME,
            Key={"conversation": {"S": session_id}},
        )
        item = r.get("Item")
        if item and "messages" in item:
            return _from_dynamo(item["messages"])
    except Exception as e:
        print(f"⚠️ DynamoDB get_conversation échoué ({e}), retour en mémoire vide")
    return []


def save_turn(session_id: str, role: str, content: str):
    messages = get_conversation(session_id)
    messages.append({
        "role": role,
        "content": content[:800],
        "ts": datetime.now().isoformat(),
    })
    # Garde seulement les N dernières paires
    if len(messages) > CONV_MAX_TURNS * 2:
        messages = messages[-(CONV_MAX_TURNS * 2):]
    try:
        _client.put_item(
            TableName=TABLE_NAME,
            Item={
                "conversation": {"S": session_id},
                "messages": _to_dynamo(messages),
                "last_updated": {"S": datetime.now().isoformat()},
            },
        )
    except Exception as e:
        print(f"⚠️ DynamoDB save_turn échoué ({e})")


def clear_conversation(session_id: str):
    try:
        _client.delete_item(
            TableName=TABLE_NAME,
            Key={"conversation": {"S": session_id}},
        )
    except Exception as e:
        print(f"⚠️ DynamoDB clear_conversation échoué ({e})")


def format_history(session_id: str) -> str:
    messages = get_conversation(session_id)
    if not messages:
        return ""
    lines = ["Historique de la conversation :"]
    for m in messages:
        prefix = "Étudiant" if m["role"] == "user" else "Assistant"
        lines.append(f"  {prefix}: {m['content']}")
    return "\n".join(lines)
