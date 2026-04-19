import os
import sys
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root is on sys.path when this file is run directly
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")


# ── Mock fallback ──────────────────────────────────────────────────────────────

def mock_moodle() -> list[dict]:
    return [
        {
            "course": "Analysis 1",
            "filename": "Lecture_1_mock",
            "summary": "[MOCK] This is a placeholder summary. Real Moodle connection unavailable.",
        }
    ]


# ── Real agent ─────────────────────────────────────────────────────────────────

def run_moodle_agent() -> list[dict]:
    from moodle.moodle_auth import get_moodle_session
    from moodle.moodle_courses import get_enrolled_courses
    from moodle.moodle_files import get_pdf_files
    from moodle.pdf_extractor import download_and_extract
    from aws.bedrock_client import summarize_lecture
    from aws.rag_builder import store_document
    from aws.s3_client import (
        save_summary, get_summary,
        save_processed_files, get_processed_files,
    )

    results = []

    # Step 1 — Login
    print("[Agent] Logging into Moodle...")
    session = get_moodle_session(
        os.getenv("TUM_USERNAME"),
        os.getenv("TUM_PASSWORD"),
    )
    print("[Agent] Login successful.")

    # Step 2 — Get all courses
    print("[Agent] Fetching enrolled courses...")
    courses = get_enrolled_courses(session)
    print(f"[Agent] Found {len(courses)} courses.")

    # Step 3 — Load already-processed URLs to skip them
    processed_urls = set(get_processed_files())
    newly_processed = list(processed_urls)

    for course in courses:
        course_name = course.get("fullname", f"course_{course['id']}")
        course_name_safe = course_name.replace("/", "_").replace(" ", "_")
        print(f"\n[Agent] Course : {course_name}")

        # Step 3 — Find new PDFs
        pdfs = get_pdf_files(session, course["id"])
        new_pdfs = [f for f in pdfs if f["url"] not in processed_urls]
        print(f"[Agent]   {len(pdfs)} PDF(s) found, {len(new_pdfs)} new.")

        for pdf in new_pdfs:
            url      = pdf["url"]
            filename = urllib.parse.unquote(pdf["filename"]).replace(" ", "_").replace(".pdf", "")

            # Check if summary already cached in S3
            cached = get_summary(course_name_safe, filename)
            if cached:
                print(f"[Agent]   Skipping '{filename}' — summary already in S3.")
                results.append({
                    "course":   course_name,
                    "filename": filename,
                    "summary":  cached,
                })
                newly_processed.append(url)
                continue

            # Step 4 — Download and extract text
            print(f"[Agent]   Downloading '{filename}'...")
            try:
                text = download_and_extract(session, url)
                print(f"[Agent]   Extracted {len(text)} characters.")
            except Exception as e:
                print(f"[Agent]   ERROR extracting '{filename}': {e}")
                continue

            # Step 5 — Generate summary
            print(f"[Agent]   Generating summary with Bedrock...")
            try:
                summary = summarize_lecture(text)
                print(f"[Agent]   Summary generated ({len(summary)} chars).")
            except Exception as e:
                print(f"[Agent]   ERROR generating summary for '{filename}': {e}")
                continue

            # Step 6 — Save to S3
            s3_key = save_summary(course_name_safe, filename, summary)
            print(f"[Agent]   Saved to S3 : {s3_key}")

            # Step 7 — Index for RAG (fail-soft: don't abort the pipeline)
            try:
                n = store_document(text, course_name_safe, filename)
                print(f"[Agent]   Indexed for RAG ({n} chunks).")
            except Exception as e:
                print(f"[Agent]   WARNING RAG indexing failed for '{filename}': {type(e).__name__}: {e}")

            results.append({
                "course":   course_name,
                "filename": filename,
                "summary":  summary,
            })
            newly_processed.append(url)

    # Persist updated processed files list
    save_processed_files(newly_processed)
    print(f"\n[Agent] Done. {len(results)} summary(ies) generated.")
    return results


# ── Loader with mock fallback ──────────────────────────────────────────────────

def load_agent():
    """Return run_moodle_agent if all dependencies are available, else mock."""
    try:
        import moodle.moodle_auth      # noqa
        import moodle.moodle_courses   # noqa
        import moodle.moodle_files     # noqa
        import moodle.pdf_extractor    # noqa
        import aws.bedrock_client      # noqa
        import aws.s3_client           # noqa
        return run_moodle_agent
    except ImportError as e:
        print(f"[load_agent] Dependency missing ({e}), falling back to mock.")
        return mock_moodle


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    agent = load_agent()
    results = agent()
    print(f"\nResults ({len(results)}) :")
    for r in results:
        print(f"  [{r['course']}] {r['filename']} — {len(r['summary'])} chars")
