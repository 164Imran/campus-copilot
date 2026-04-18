import requests
from pathlib import Path
from bs4 import BeautifulSoup

MOODLE_BASE = "https://www.moodle.tum.de"


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

        # Follow the link — Moodle redirects to the actual file
        r = session.get(href, allow_redirects=True)
        content_type = r.headers.get("content-type", "")
        final_url = r.url

        if "pdf" in content_type or final_url.lower().endswith(".pdf"):
            filename = final_url.split("/")[-1].split("?")[0]
            section = _get_section_name(soup, a)
            pdfs.append({
                "filename": filename,
                "url": final_url,
                "section": section,
                "filesize": int(r.headers.get("content-length", 0)),
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
