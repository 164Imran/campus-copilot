import os
import json
import uuid
import difflib
import boto3
from botocore.config import Config
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from aws.s3_client import get_s3_client, list_summaries

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
        region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
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


# ── Parallel embeddings ────────────────────────────────────────────────────────

def embed_parallel(texts: list[str], max_workers: int = 10) -> list[list[float]]:
    """Embed multiple texts concurrently. Preserves order."""
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(embed, texts))


# ── Store document ─────────────────────────────────────────────────────────────

def store_document(text: str, course_name: str, file_name: str) -> int:
    splitter = RecursiveCharacterTextSplitter(chunk_size=2500, chunk_overlap=250)
    chunks = splitter.split_text(text)
    print(f"[RAG] Splitting '{file_name}' -> {len(chunks)} chunks.")

    # Embed all chunks in parallel
    print(f"[RAG] Embedding {len(chunks)} chunks in parallel...")
    vectors_data = embed_parallel(chunks, max_workers=10)

    s3 = get_s3_client()
    bucket = os.getenv("S3_BUCKET_NAME")
    client = get_vectors_client()

    # Upload chunk texts to S3 in parallel, collect vector records
    def _upload_chunk(args: tuple) -> dict:
        i, chunk, vector = args
        chunk_key = f"{course_name}/{file_name}/chunk_{i}_{uuid.uuid4().hex[:8]}"
        s3.put_object(
            Bucket=bucket,
            Key=f"rag-chunks/{chunk_key}.txt",
            Body=chunk.encode("utf-8"),
            ContentType="text/plain",
        )
        return {
            "key": chunk_key,
            "data": {"float32": vector},
            "metadata": {
                "course":      course_name,
                "filename":    file_name,
                "chunk_index": str(i),
                "s3_key":      f"rag-chunks/{chunk_key}.txt",
            },
        }

    with ThreadPoolExecutor(max_workers=10) as ex:
        vectors = list(ex.map(_upload_chunk, enumerate(zip(chunks, vectors_data))))

    # S3 Vectors: up to 500 vectors per request
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

def resolve_course_name(name: str) -> str:
    """Return the best-matching stored course name, or the original if no match.

    Resolution order (first hit wins):
      1. Exact key match
      2. Case-insensitive match
      3. Substring: user input contained in a course name
      4. Token overlap: all user words appear in a course name
      5. Fuzzy (difflib, cutoff 0.4)
      6. Best token-overlap score (partial match, at least 1 word)
    """
    available = list(list_summaries().keys())
    if not available:
        return name

    query = name.strip()

    # 1. Exact
    if query in available:
        return query

    # 2. Case-insensitive
    lower_map = {c.lower(): c for c in available}
    normalized = {c.replace("_", " ").lower(): c for c in available}
    q_lower = query.lower()
    if q_lower in lower_map:
        return lower_map[q_lower]

    q_norm = q_lower.replace("_", " ")

    # 3. Substring: query is contained inside a full course name
    for norm_key, original in normalized.items():
        if q_norm in norm_key:
            print(f"[RAG] Cours '{name}' résolu par sous-chaîne → '{original}'")
            return original

    # 4. Token overlap: every word in query found in a course name
    q_tokens = set(q_norm.split())
    for norm_key, original in normalized.items():
        course_tokens = set(norm_key.split())
        if q_tokens and q_tokens.issubset(course_tokens):
            print(f"[RAG] Cours '{name}' résolu par tokens → '{original}'")
            return original

    # 5. Fuzzy
    matches = difflib.get_close_matches(q_norm, normalized.keys(), n=1, cutoff=0.4)
    if matches:
        resolved = normalized[matches[0]]
        print(f"[RAG] Cours '{name}' résolu par fuzzy → '{resolved}'")
        return resolved

    # 6. Best partial token overlap (at least 1 word in common)
    best, best_score = None, 0
    for norm_key, original in normalized.items():
        course_tokens = set(norm_key.split())
        score = len(q_tokens & course_tokens)
        if score > best_score:
            best_score, best = score, original
    if best and best_score > 0:
        print(f"[RAG] Cours '{name}' résolu par overlap partiel ({best_score} mot(s)) → '{best}'")
        return best

    print(f"[RAG] Cours '{name}' introuvable. Disponibles : {available}")
    return name


def search(query: str, course_name: str, top_k: int = 5) -> list[str]:
    course_name = resolve_course_name(course_name)
    client = get_vectors_client()
    query_vector = embed(query)

    response = client.query_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        queryVector={"float32": query_vector},
        topK=top_k * 4,  # over-fetch, filter by course client-side
        returnMetadata=True,
    )

    s3 = get_s3_client()
    bucket = os.getenv("S3_BUCKET_NAME")

    # Filter by course and collect S3 keys
    s3_keys = []
    for item in response.get("vectors", []):
        meta = item.get("metadata", {})
        if meta.get("course") == course_name:
            s3_keys.append(meta.get("s3_key", ""))
        if len(s3_keys) >= top_k:
            break

    # Fetch chunk texts from S3 in parallel
    def _fetch(s3_key: str) -> str:
        try:
            obj = s3.get_object(Bucket=bucket, Key=s3_key)
            return obj["Body"].read().decode("utf-8")
        except Exception:
            return ""

    with ThreadPoolExecutor(max_workers=max(len(s3_keys), 1)) as ex:
        chunks = [c for c in ex.map(_fetch, s3_keys) if c]

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
