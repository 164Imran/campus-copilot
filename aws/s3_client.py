import os
import json
import boto3
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("S3_BUCKET_NAME", "campus-copilot")


def get_s3_client():
    return boto3.client(
        "s3",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


# ── File upload / download ─────────────────────────────────────────────────────

def upload_file(local_path: str | Path, s3_key: str) -> str:
    get_s3_client().upload_file(str(local_path), BUCKET, s3_key)
    return s3_key


def download_file(s3_key: str, local_path: str | Path) -> Path:
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    get_s3_client().download_file(BUCKET, s3_key, str(local_path))
    return Path(local_path)


def list_objects(prefix: str = "") -> list[str]:
    paginator = get_s3_client().get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


# ── Helpers ────────────────────────────────────────────────────────────────────

def _put_json(s3_key: str, data: dict) -> str:
    get_s3_client().put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )
    return s3_key


def _get_json(s3_key: str) -> dict | None:
    try:
        response = get_s3_client().get_object(Bucket=BUCKET, Key=s3_key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except get_s3_client().exceptions.NoSuchKey:
        return None
    except Exception:
        return None


def _key_exists(s3_key: str) -> bool:
    try:
        get_s3_client().head_object(Bucket=BUCKET, Key=s3_key)
        return True
    except Exception:
        return False


# ── Summaries ──────────────────────────────────────────────────────────────────

def save_summary(course_name: str, filename: str, summary: str) -> str:
    s3_key = f"summaries/{course_name}/{filename}.json"
    data = {
        "course": course_name,
        "filename": filename,
        "summary": summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    client = get_s3_client()
    client.put_object(
        Bucket=BUCKET,
        Key=s3_key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )
    return s3_key


def get_summary(course_name: str, filename: str) -> str | None:
    s3_key = f"summaries/{course_name}/{filename}.json"
    try:
        response = get_s3_client().get_object(Bucket=BUCKET, Key=s3_key)
        data = json.loads(response["Body"].read().decode("utf-8"))
        return data.get("summary")
    except Exception:
        return None


def list_summaries() -> dict[str, list[str]]:
    keys = list_objects(prefix="summaries/")
    grouped: dict[str, list[str]] = {}
    for key in keys:
        parts = key.split("/")
        if len(parts) >= 3:
            course = parts[1]
            fname  = parts[2]
            grouped.setdefault(course, []).append(fname)
    return grouped


# ── Processed files tracker ────────────────────────────────────────────────────

PROCESSED_KEY = "user_config/processed_files.json"


def save_processed_files(urls: list[str]) -> str:
    data = {
        "processed_files": urls,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client = get_s3_client()
    client.put_object(
        Bucket=BUCKET,
        Key=PROCESSED_KEY,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )
    return PROCESSED_KEY


def get_processed_files() -> list[str]:
    try:
        response = get_s3_client().get_object(Bucket=BUCKET, Key=PROCESSED_KEY)
        data = json.loads(response["Body"].read().decode("utf-8"))
        return data.get("processed_files", [])
    except Exception:
        return []
