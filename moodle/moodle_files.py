import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from bs4 import BeautifulSoup

MOODLE_BASE = "https://www.moodle.tum.de"


def get_pdfs_from_contents(sections: list[dict]) -> list[dict]:
    """Extract PDFs from core_course_get_contents AJAX response. Zero extra HTTP requests."""
    pdfs = []
    for section in sections:
        section_name = section.get("name", "").strip()
        for module in section.get("modules", []):
            if module.get("modname") not in ("resource", "folder"):
                continue
            for content in module.get("contents", []):
                mime = content.get("mimetype", "")
                fname = content.get("filename", "")
                if "pdf" in mime.lower() or fname.lower().endswith(".pdf"):
                    pdfs.append({
                        "filename": fname,
                        "url": content.get("fileurl", ""),
                        "section": section_name,
                        "size": content.get("filesize", 0),
                    })
    return pdfs


def get_pdf_files_parallel(session: requests.Session, course_id: int, max_workers: int = 8) -> list[dict]:
    """Like get_pdf_files but HEAD requests run in parallel. Much faster for courses with many links."""
    resp = session.get(f"{MOODLE_BASE}/course/view.php?id={course_id}", timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Deduplicate links while preserving anchor tag for section lookup
    seen: dict[str, object] = {}
    for a in soup.select("a[href*='mod/resource/view.php']"):
        href = a["href"]
        if href not in seen:
            seen[href] = a

    def _check(href_anchor: tuple) -> dict | None:
        href, anchor = href_anchor
        try:
            r = session.head(href, allow_redirects=True, timeout=10)
            ct = r.headers.get("content-type", "")
            url = r.url
            if "pdf" in ct or url.lower().endswith(".pdf"):
                filename = url.split("/")[-1].split("?")[0] or href.split("id=")[-1] + ".pdf"
                return {"filename": filename, "url": url, "section": _get_section_name(soup, anchor), "size": 0}
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=min(max_workers, len(seen) or 1)) as ex:
        results = list(ex.map(_check, seen.items()))

    return [r for r in results if r is not None]


def get_pdf_files(session: requests.Session, course_id: int) -> list[dict]:
    resp = session.get(f"{MOODLE_BASE}/course/view.php?id={course_id}")
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    resource_links = soup.select("a[href*='mod/resource/view.php']")
    seen = set()
    pdfs = []

    for a in resource_links:
        href = a["href"]
        if href in seen:
            continue
        seen.add(href)

        # Use HEAD to check content-type without downloading the whole file
        try:
            r = session.head(href, allow_redirects=True, timeout=15)
        except Exception:
            continue

        content_type = r.headers.get("content-type", "")
        final_url = r.url

        if "pdf" in content_type or final_url.lower().endswith(".pdf"):
            filename = final_url.split("/")[-1].split("?")[0]
            if not filename:
                filename = href.split("id=")[-1] + ".pdf"
            section = _get_section_name(soup, a)
            pdfs.append({
                "filename": filename,
                "url":      final_url,
                "section":  section,
            })

    return pdfs


def _get_section_name(soup: BeautifulSoup, link_tag) -> str:
    section = link_tag.find_parent(class_=lambda c: c and "section" in c)
    if section:
        name_tag = section.select_one(".sectionname, h3")
        if name_tag:
            return name_tag.get_text(strip=True)
    return ""


def download_file(session: requests.Session, url: str, dest_dir: str) -> Path:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    response = session.get(url, stream=True)
    response.raise_for_status()
    filename = url.split("/")[-1].split("?")[0]
    file_path = dest / filename
    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return file_path
