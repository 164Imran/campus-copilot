import requests
import fitz  # PyMuPDF
from pathlib import Path


def download_and_extract(session: requests.Session, url: str, dest_dir: str = "/tmp/moodle_pdfs") -> str:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0]
    pdf_path = dest / filename

    resp = session.get(url, stream=True)
    resp.raise_for_status()
    with open(pdf_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    return extract_text(pdf_path)


def extract_text(pdf_path: str | Path) -> str:
    doc = fitz.open(str(pdf_path))
    return "\n".join(page.get_text() for page in doc)


def extract_text_by_page(pdf_path: str | Path) -> list[str]:
    doc = fitz.open(str(pdf_path))
    return [page.get_text() for page in doc]
