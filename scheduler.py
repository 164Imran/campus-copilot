import os
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")


def log(msg: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def check_for_new_files() -> bool:
    from moodle.moodle_auth import get_moodle_session
    from moodle.moodle_courses import get_enrolled_courses
    from moodle.moodle_files import get_pdf_files
    from aws.s3_client import get_processed_files
    import urllib.parse

    log("Connecting to Moodle...")
    session = get_moodle_session(
        os.getenv("TUM_USERNAME"),
        os.getenv("TUM_PASSWORD"),
    )
    log("Login successful.")

    courses = get_enrolled_courses(session)
    log(f"Found {len(courses)} courses.")

    processed_urls = set(get_processed_files())
    new_found = []

    for course in courses:
        pdfs = get_pdf_files(session, course["id"])
        new = [p for p in pdfs if p["url"] not in processed_urls]
        if new:
            names = [urllib.parse.unquote(p["filename"]) for p in new]
            log(f"  [{course['fullname']}] {len(new)} new PDF(s): {', '.join(names)}")
            new_found.extend(new)

    if new_found:
        log(f"Total new files detected: {len(new_found)}")
        return True

    log("No new files detected.")
    return False


def run_cycle() -> None:
    log("=" * 50)
    log("Starting new check cycle...")
    try:
        has_new = check_for_new_files()
        if has_new:
            log("New PDFs found — running Moodle agent...")
            from agents.moodle_agent import run_moodle_agent
            results = run_moodle_agent()
            log(f"Agent done. {len(results)} summary(ies) generated.")
        else:
            hours = int(os.getenv("SCHEDULER_HOURS", "6"))
            log(f"No new files. Sleeping {hours}h.")
    except Exception as e:
        log(f"ERROR during cycle: {e}")
    log("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Co-Pilot Scheduler")
    parser.add_argument("--once", action="store_true", help="Run one check then exit")
    args = parser.parse_args()

    hours = int(os.getenv("SCHEDULER_HOURS", "6"))
    sleep_seconds = hours * 3600

    log("Campus Co-Pilot Scheduler started.")
    log(f"Check interval: every {hours} hour(s). Press Ctrl+C to stop.")

    if args.once:
        run_cycle()
        log("--once flag set. Exiting.")
        return

    try:
        while True:
            run_cycle()
            log(f"Next check in {hours} hour(s).")
            time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        log("Scheduler stopped by user.")


if __name__ == "__main__":
    main()
