import os
import json
import uuid
import boto3
from botocore.config import Config
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from aws.s3_client import get_s3_client

load_dotenv()

VECTOR_BUCKET = "campus-copilot-vectors"
INDEX_NAME    = "lectures"
EMBED_MODEL   = "amazon.titan-embed-text-v2:0"
EMBED_DIM     = 1024
# S3 Vectors is currently available in us-east-1
VECTORS_REGION = "us-east-1"


# ── Clients ────────────────────────────────────────────────────────────────────

def _creds() -> dict:
    return {
        "aws_access_key_id":     os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    }


def get_vectors_client():
    return boto3.client("s3vectors", region_name=VECTORS_REGION, **_creds())


def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION", "eu-west-1"),
        config=Config(read_timeout=120),
        **_creds(),
    )


# ── Embeddings ─────────────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    client = get_bedrock_client()
    body = json.dumps({"inputText": text[:8000], "dimensions": EMBED_DIM, "normalize": True})
    response = client.invoke_model(
        modelId=EMBED_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["embedding"]


# ── Bucket + Index setup ───────────────────────────────────────────────────────

def create_vector_bucket() -> None:
    client = get_vectors_client()

    # Create bucket if missing
    try:
        client.get_vector_bucket(vectorBucketName=VECTOR_BUCKET)
        print(f"[RAG] Vector bucket '{VECTOR_BUCKET}' already exists.")
    except client.exceptions.NotFoundException:
        client.create_vector_bucket(vectorBucketName=VECTOR_BUCKET)
        print(f"[RAG] Created vector bucket '{VECTOR_BUCKET}'.")

    # Create index if missing
    try:
        client.get_index(vectorBucketName=VECTOR_BUCKET, indexName=INDEX_NAME)
        print(f"[RAG] Index '{INDEX_NAME}' already exists.")
    except client.exceptions.NotFoundException:
        client.create_index(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            dataType="float32",
            dimension=EMBED_DIM,
            distanceMetric="cosine",
        )
        print(f"[RAG] Created index '{INDEX_NAME}' (dim={EMBED_DIM}, cosine).")


# ── Store document ─────────────────────────────────────────────────────────────

def store_document(text: str, course_name: str, file_name: str) -> int:
    # ~500 words ≈ 2500 chars, overlap ~50 words ≈ 250 chars
    splitter = RecursiveCharacterTextSplitter(chunk_size=2500, chunk_overlap=250)
    chunks = splitter.split_text(text)
    print(f"[RAG] Splitting '{file_name}' -> {len(chunks)} chunks.")

    s3  = get_s3_client()
    bucket = os.getenv("S3_BUCKET_NAME")
    client = get_vectors_client()
    vectors = []
    for i, chunk in enumerate(chunks):
        chunk_key = f"{course_name}/{file_name}/chunk_{i}_{uuid.uuid4().hex[:8]}"
        # Store full chunk text in S3 (no size limit)
        s3.put_object(
            Bucket=bucket,
            Key=f"rag-chunks/{chunk_key}.txt",
            Body=chunk.encode("utf-8"),
            ContentType="text/plain",
        )
        vector = embed(chunk)
        vectors.append({
            "key": chunk_key,
            "data": {"float32": vector},
            "metadata": {
                "course":      course_name,
                "filename":    file_name,
                "chunk_index": str(i),
                "s3_key":      f"rag-chunks/{chunk_key}.txt",
            },
        })

    # S3 Vectors accepts up to 500 vectors per request
    batch_size = 100
    for start in range(0, len(vectors), batch_size):
        batch = vectors[start:start + batch_size]
        client.put_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            vectors=batch,
        )
        print(f"[RAG]   Stored batch {start // batch_size + 1} ({len(batch)} vectors).")

    print(f"[RAG] Stored {len(vectors)} vectors for '{file_name}'.")
    return len(vectors)


# ── Search ─────────────────────────────────────────────────────────────────────

def search(query: str, course_name: str, top_k: int = 5) -> list[str]:
    client = get_vectors_client()
    query_vector = embed(query)

    response = client.query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        queryVector={"float32": query_vector},
        topK=top_k * 3,  # fetch extra, then filter by course client-side
        returnMetadata=True,
    )

    s3     = get_s3_client()
    bucket = os.getenv("S3_BUCKET_NAME")
    chunks = []
    for item in response.get("vectors", []):
        meta = item.get("metadata", {})
        if meta.get("course") == course_name:
            s3_key = meta.get("s3_key", "")
            try:
                obj = s3.get_object(Bucket=bucket, Key=s3_key)
                chunks.append(obj["Body"].read().decode("utf-8"))
            except Exception:
                chunks.append("")
        if len(chunks) >= top_k:
            break

    print(f"[RAG] Found {len(chunks)} relevant chunks for query.")
    return chunks


# ── Compare courses ───────────────────────────────────────────────────────────

def compare_courses(topic: str, course1: str, course2: str) -> str:
    print(f"[RAG] Searching '{topic}' in '{course1}'...")
    chunks1 = search(topic, course1, top_k=5)
    print(f"[RAG] Searching '{topic}' in '{course2}'...")
    chunks2 = search(topic, course2, top_k=5)

    context1 = "\n\n---\n\n".join(chunks1) if chunks1 else "No relevant content found."
    context2 = "\n\n---\n\n".join(chunks2) if chunks2 else "No relevant content found."

    system = (
        "You are an academic assistant helping students connect knowledge across courses. "
        "Base your analysis ONLY on the provided excerpts. "
        "Write all math using LaTeX ($...$ for inline, $$...$$ for block)."
    )
    user_msg = (
        f"You are an academic assistant. Here are two courses covering the topic '{topic}'.\n\n"
        f"Course 1 - {course1}:\n{context1}\n\n"
        f"Course 2 - {course2}:\n{context2}\n\n"
        f"Identify:\n"
        f"1. COMMON CONCEPTS: what both courses share\n"
        f"2. DIFFERENCES: how each course approaches it differently\n"
        f"3. COMPLEMENTARY INSIGHTS: what each course adds that the other doesn't\n"
        f"4. STUDY TIP: how to use both courses together to master this topic"
    )

    client = get_bedrock_client()
    model_id = os.getenv("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-6")
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 3000,
        "system": system,
        "messages": [{"role": "user", "content": user_msg}],
    })
    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["content"][0]["text"]


# ── Answer question ────────────────────────────────────────────────────────────

def answer_question(question: str, course_name: str) -> str:
    chunks = search(question, course_name)
    if not chunks:
        return "No relevant content found in the course materials."

    context = "\n\n---\n\n".join(chunks)

    system = (
        "You are an academic assistant. Answer the student's question using ONLY "
        "the provided course excerpts. If the answer is not in the excerpts, say "
        "'This is not covered in the provided lecture content.' "
        "Write all math using LaTeX ($...$ for inline, $$...$$ for block)."
    )
    user_msg = f"Course excerpts:\n\n{context}\n\n---\n\nQuestion: {question}"

    client = get_bedrock_client()
    model_id = os.getenv("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-6")
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "system": system,
        "messages": [{"role": "user", "content": user_msg}],
    })
    response = client.invoke_model(
        modelId=model_id,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["content"][0]["text"]
