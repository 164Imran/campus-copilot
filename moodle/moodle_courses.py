import re
import requests
from concurrent.futures import ThreadPoolExecutor

MOODLE_BASE = "https://www.moodle.tum.de"

_sesskey_cache: dict[int, str] = {}


def _get_sesskey(session: requests.Session) -> str:
    key = id(session)
    if key not in _sesskey_cache:
        resp = session.get(f"{MOODLE_BASE}/my/")
        resp.raise_for_status()
        match = re.search(r'"sesskey":"([^"]+)"', resp.text)
        if not match:
            raise ValueError("Could not extract sesskey from Moodle dashboard")
        _sesskey_cache[key] = match.group(1)
    return _sesskey_cache[key]


def get_sesskey(session: requests.Session) -> str:
    return _get_sesskey(session)


def _ajax(session: requests.Session, methodname: str, args: dict) -> dict:
    sesskey = _get_sesskey(session)
    payload = [{"index": 0, "methodname": methodname, "args": args}]
    resp = session.post(
        f"{MOODLE_BASE}/lib/ajax/service.php",
        params={"sesskey": sesskey},
        json=payload,
    )
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, list) and result and "data" in result[0]:
        return result[0]["data"]
    raise ValueError(f"Unexpected AJAX response: {result}")


def get_enrolled_courses(session: requests.Session) -> list[dict]:
    data = _ajax(session, "core_course_get_enrolled_courses_by_timeline_classification", {
        "offset": 0,
        "limit": 0,
        "classification": "all",
        "sort": "fullname",
        "customfieldname": "",
        "customfieldvalue": "",
    })
    return data.get("courses", [])


def get_course_contents(session: requests.Session, course_id: int) -> list[dict]:
    data = _ajax(session, "core_course_get_contents", {"courseid": course_id})
    return data if isinstance(data, list) else []


def get_course_contents_bulk(
    session: requests.Session,
    course_ids: list[int],
    sesskey: str,
    max_workers: int = 5,
) -> dict[int, list[dict]]:
    """Fetch contents for multiple courses in parallel using a pre-fetched sesskey."""
    def _fetch(course_id: int) -> tuple[int, list[dict]]:
        payload = [{"index": 0, "methodname": "core_course_get_contents", "args": {"courseid": course_id}}]
        try:
            resp = session.post(
                f"{MOODLE_BASE}/lib/ajax/service.php",
                params={"sesskey": sesskey},
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()
            result = resp.json()
            if isinstance(result, list) and result and "data" in result[0]:
                data = result[0]["data"]
                return course_id, (data if isinstance(data, list) else [])
        except Exception as e:
            print(f"[Moodle] Warning: could not fetch contents for course {course_id}: {e}")
        return course_id, []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        pairs = list(ex.map(_fetch, course_ids))
    return dict(pairs)
