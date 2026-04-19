import json
import os
import sys
import stat
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

COOKIE_FILE = _ROOT / ".moodle_cookies.json"

# ── Global state ───────────────────────────────────────────────────────────────
_INDEX_STATE: dict = {
    "status": "idle",   # idle | running | done | error
    "progress": {"total": 0, "done": 0},
    "errors": [],
}
_INDEX_LOCK = threading.Lock()
_SESSION_CACHE: dict = {"session": None}
_SESSION_LOCK = threading.Lock()  # prevents double Selenium launch


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_name(name: str) -> str:
    """Sanitize a course/file name for use as an S3 key segment."""
    sanitized = name.replace("..", "").replace("/", "_").replace("\\", "_")
    sanitized = sanitized.replace(" ", "_").replace("\x00", "").replace("\n", "").replace("\r", "")
    return sanitized or "unnamed"


def _clean_filename(raw: str) -> str:
    """URL-decode and sanitize a PDF filename for use as an S3 key segment."""
    decoded = urllib.parse.unquote(raw)
    # Normalize separators then take basename to strip path traversal
    decoded = decoded.replace("\\", "/").split("/")[-1]
    decoded = decoded.replace("..", "").replace(" ", "_").replace(".pdf", "")
    decoded = decoded.replace("\x00", "").replace("\n", "").replace("\r", "")
    return decoded or "unnamed"


# ── Cookie persistence (skip Selenium on restart) ──────────────────────────────

def _save_cookies(session) -> None:
    try:
        cookies = {n: v for n, v in session.cookies.items()}
        COOKIE_FILE.write_text(json.dumps(cookies))
        COOKIE_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 600 — owner only
    except Exception as e:
        print(f"[Moodle] Cookie save failed: {e}")


def _try_restore_session():
    """Restore session from disk cookies. Returns session if still valid, else None."""
    if not COOKIE_FILE.exists():
        return None
    try:
        import requests as _req
        cookies = json.loads(COOKIE_FILE.read_text())
        session = _req.Session()
        for name, value in cookies.items():
            session.cookies.set(name, value)
        resp = session.get("https://www.moodle.tum.de/my/", timeout=10, allow_redirects=True)
        if resp.ok and "moodle.tum.de/my/" in resp.url:
            print("[Moodle] Session restaurée depuis cache cookies (pas de Selenium).")
            return session
        print("[Moodle] Cookies expirés, reconnexion via Selenium...")
        COOKIE_FILE.unlink(missing_ok=True)
    except Exception as e:
        print(f"[Moodle] Cookie restore failed ({e}), falling back to Selenium.")
    return None


# ── Auth (cached for the process lifetime) ─────────────────────────────────────

def _get_session():
    if _SESSION_CACHE["session"] is not None:
        return _SESSION_CACHE["session"]
    with _SESSION_LOCK:
        if _SESSION_CACHE["session"] is not None:
            return _SESSION_CACHE["session"]

        # Fast path: restore from disk cookies (~1s)
        session = _try_restore_session()

        if session is None:
            # Slow path: full Selenium login (~20-30s)
            from moodle.moodle_auth import get_moodle_session
            print("[Moodle] Logging in via Selenium...")
            session = get_moodle_session(
                os.getenv("TUM_USERNAME"),
                os.getenv("TUM_PASSWORD"),
            )
            _save_cookies(session)
            print("[Moodle] Login successful, cookies saved.")

        _SESSION_CACHE["session"] = session
    return _SESSION_CACHE["session"]


# ── Course overview — "ls" ─────────────────────────────────────────────────────

def get_course_overview() -> list[dict]:
    """
    Return all enrolled courses with their sections and PDF list.
    Uses HTML scraping + parallel HEAD requests (AJAX is blocked on TUM Moodle).

    Returns list of:
        {course_id, course_name, course_name_safe, sections: [{name, pdf_count, pdfs}], total_pdfs}
    """
    from moodle.moodle_courses import get_enrolled_courses
    from moodle.moodle_files import get_pdf_files_parallel

    session = _get_session()

    print("[Moodle] Fetching enrolled courses...")
    courses = get_enrolled_courses(session)
    print(f"[Moodle] {len(courses)} course(s) found.")

    def _fetch_course(course: dict) -> dict:
        cid = course["id"]
        cname = course.get("fullname", f"course_{cid}")
        try:
            pdfs = get_pdf_files_parallel(session, cid, max_workers=8)
        except Exception as e:
            print(f"[Moodle] Warning: could not fetch PDFs for '{cname}': {e}")
            pdfs = []

        # Group by section
        sections_dict: dict[str, list] = {}
        for pdf in pdfs:
            sname = pdf.get("section", "") or ""
            sections_dict.setdefault(sname, []).append(pdf)

        sections = [
            {"name": sname, "pdf_count": len(spdfs), "pdfs": spdfs}
            for sname, spdfs in sections_dict.items()
        ]

        return {
            "course_id": cid,
            "course_name": cname,
            "course_name_safe": _safe_name(cname),
            "sections": sections,
            "total_pdfs": len(pdfs),
        }

    print(f"[Moodle] Scraping PDF lists for {len(courses)} courses in parallel...")
    with ThreadPoolExecutor(max_workers=4) as ex:
        overview = list(ex.map(_fetch_course, courses))

    total = sum(c["total_pdfs"] for c in overview)
    print(f"[Moodle] Overview ready: {len(overview)} courses, {total} PDFs.")
    return overview


# ── Background indexing ────────────────────────────────────────────────────────

def _index_worker(session, overview: list[dict]) -> None:
    global _INDEX_STATE

    try:
        from moodle.pdf_extractor import download_and_extract
        from aws.bedrock_client import summarize_lecture
        from aws.s3_client import (
            save_summary, get_summary,
            get_processed_files, save_processed_files,
        )
        from aws.rag_builder import store_document, create_vector_bucket

        try:
            create_vector_bucket()
        except Exception as e:
            print(f"[Index] Vector bucket init warning: {e}")

        processed_urls = set(get_processed_files())

        # Build list of new PDFs to process
        to_process = []
        for course_info in overview:
            course_safe = course_info["course_name_safe"]
            for section in course_info["sections"]:
                for pdf in section["pdfs"]:
                    url = pdf["url"]
                    if not url:
                        continue
                    filename = _clean_filename(pdf["filename"])
                    if url in processed_urls:
                        continue
                    if get_summary(course_safe, filename):
                        processed_urls.add(url)
                        continue
                    to_process.append({
                        "url": url,
                        "filename": filename,
                        "course_safe": course_safe,
                    })

        with _INDEX_LOCK:
            _INDEX_STATE["progress"] = {"total": len(to_process), "done": 0}

        print(f"[Index] {len(to_process)} new PDF(s) to index.")

        if not to_process:
            save_processed_files(list(processed_urls))
            with _INDEX_LOCK:
                _INDEX_STATE["status"] = "done"
            return

        new_urls: list[str] = []

        def _process_one(pdf_info: dict) -> None:
            url = pdf_info["url"]
            filename = pdf_info["filename"]
            course_safe = pdf_info["course_safe"]
            try:
                print(f"[Index] Downloading '{filename}'...")
                text, _ = download_and_extract(session, url)
                if not text.strip():
                    print(f"[Index] '{filename}' is empty, skipped.")
                    new_urls.append(url)
                    return

                print(f"[Index] Summarizing '{filename}'...")
                summary = summarize_lecture(text)
                save_summary(course_safe, filename, summary)

                print(f"[Index] Embedding & storing '{filename}'...")
                store_document(text, course_safe, filename)

                new_urls.append(url)
                print(f"[Index] '{filename}' done.")
            except Exception as e:
                msg = f"{filename}: {type(e).__name__}: {e}"
                print(f"[Index] ERROR: {msg}")
                with _INDEX_LOCK:
                    _INDEX_STATE["errors"].append(msg)
            finally:
                with _INDEX_LOCK:
                    _INDEX_STATE["progress"]["done"] += 1

        # 3 PDFs concurrently (Bedrock rate limits)
        with ThreadPoolExecutor(max_workers=3) as ex:
            list(ex.map(_process_one, to_process))

        save_processed_files(list(processed_urls | set(new_urls)))
        print("[Index] Background indexing complete.")

    except Exception as e:
        msg = f"Fatal indexing error: {type(e).__name__}: {e}"
        print(f"[Index] {msg}")
        with _INDEX_LOCK:
            _INDEX_STATE["errors"].append(msg)
    finally:
        # Always update status, even on unexpected crash
        with _INDEX_LOCK:
            if _INDEX_STATE["status"] == "running":
                _INDEX_STATE["status"] = "done"


def start_background_indexing(session, overview: list[dict]) -> None:
    with _INDEX_LOCK:
        if _INDEX_STATE["status"] == "running":
            return
        _INDEX_STATE["status"] = "running"
        _INDEX_STATE["errors"] = []
        _INDEX_STATE["progress"] = {"total": 0, "done": 0}

    thread = threading.Thread(
        target=_index_worker,
        args=(session, overview),
        daemon=True,
        name="moodle-indexer",
    )
    thread.start()
    print("[Index] Background indexing started.")


def get_index_status() -> dict:
    with _INDEX_LOCK:
        return {
            "status": _INDEX_STATE["status"],
            "progress": dict(_INDEX_STATE["progress"]),
            "errors": list(_INDEX_STATE["errors"]),
        }


# ── Main agent entry point (backward-compatible with orchestrator) ─────────────

def _results_from_s3() -> list[dict]:
    """Build result list purely from S3 cache — no Moodle auth needed."""
    from aws.s3_client import list_summaries, get_summary
    results = []
    for course_safe, files in list_summaries().items():
        for fname in files:
            name = fname.removesuffix(".json")
            summary = get_summary(course_safe, name)
            if summary:
                results.append({
                    "course": course_safe.replace("_", " "),
                    "pdf_filename": name,
                    "pdf_path": None,
                    "summary": summary,
                })
    return results


def run_moodle_agent() -> list[dict]:
    """
    Fast path  : if S3 cache is fresh → return in ~1s, no Moodle auth at all.
    Slow path  : authenticate, fetch overview, start background indexing, return cache.
    Compatible with orchestrator: list of {course, pdf_filename, pdf_path, summary}.
    """
    from aws.s3_client import get_summary, get_last_sync_time

    # ── Fast path: S3 cache still fresh ───────────────────────────────────────
    max_age = timedelta(hours=float(os.getenv("MOODLE_CACHE_HOURS", "6")))
    last_sync = get_last_sync_time()
    if last_sync is not None:
        age = datetime.now(timezone.utc) - last_sync
        if age < max_age:
            results = _results_from_s3()
            if results:
                print(
                    f"[Moodle] Cache S3 frais ({str(age).split('.')[0]} ago) — "
                    f"{len(results)} résumé(s) retournés sans appel Moodle."
                )
                return results

    # ── Slow path: auth + overview + background index ─────────────────────────
    session = _get_session()
    overview = get_course_overview()
    start_background_indexing(session, overview)

    # Return what's already in S3 (background worker will fill the rest)
    results = []
    for course_info in overview:
        course_safe = course_info["course_name_safe"]
        course_name = course_info["course_name"]
        for section in course_info["sections"]:
            for pdf in section["pdfs"]:
                filename = _clean_filename(pdf["filename"])
                summary = get_summary(course_safe, filename)
                if summary:
                    results.append({
                        "course": course_name,
                        "pdf_filename": filename,
                        "pdf_path": None,
                        "summary": summary,
                    })

    idx = get_index_status()
    prog = idx["progress"]
    print(
        f"[Moodle] {len(results)} résumé(s) en cache. "
        f"Indexation: {idx['status']} ({prog['done']}/{prog['total']})"
    )
    return results


# ── Fallback mock ──────────────────────────────────────────────────────────────

def mock_moodle() -> list[dict]:
    return [
        {
            "course": "Mock Course",
            "pdf_filename": "mock_lecture",
            "pdf_path": None,
            "summary": "[MOCK] Real Moodle connection unavailable.",
        }
    ]


def load_agent():
    try:
        import moodle.moodle_auth       # noqa
        import moodle.moodle_courses    # noqa
        import moodle.moodle_files      # noqa
        import moodle.pdf_extractor     # noqa
        import aws.bedrock_client       # noqa
        import aws.s3_client            # noqa
        return run_moodle_agent
    except ImportError as e:
        print(f"[load_agent] Missing dependency ({e}), falling back to mock.")
        return mock_moodle


# ── CLI demo ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time
    sys.stdout.reconfigure(encoding="utf-8")

    print("=== Moodle Course Overview (ls) ===\n")
    overview = get_course_overview()

    for course in overview:
        print(f"[{course['total_pdfs']} PDFs] {course['course_name']}")
        for section in course["sections"]:
            if section["pdf_count"] > 0:
                print(f"   └─ {section['name'] or '(no section)'}: {section['pdf_count']} PDF(s)")
                for pdf in section["pdfs"]:
                    size_kb = pdf["size"] // 1024 if pdf["size"] else 0
                    print(f"       • {pdf['filename']} ({size_kb} KB)")

    total = sum(c["total_pdfs"] for c in overview)
    print(f"\nTotal: {len(overview)} courses, {total} PDFs\n")

    print("Starting background indexing...")
    session = _get_session()
    start_background_indexing(session, overview)

    while True:
        status = get_index_status()
        prog = status["progress"]
        print(f"  Status: {status['status']} — {prog['done']}/{prog['total']} PDFs indexed", end="\r")
        if status["status"] in ("done", "error"):
            break
        time.sleep(5)

    print(f"\nDone. Errors: {get_index_status()['errors'] or 'none'}")
