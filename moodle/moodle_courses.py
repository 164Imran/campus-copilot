import re
import requests

MOODLE_BASE = "https://www.moodle.tum.de"


def _get_sesskey(session: requests.Session) -> str:
    resp = session.get(f"{MOODLE_BASE}/my/")
    resp.raise_for_status()
    match = re.search(r'"sesskey":"([^"]+)"', resp.text)
    if not match:
        raise ValueError("Could not extract sesskey from Moodle dashboard")
    return match.group(1)


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
