from datetime import datetime, timedelta, timezone
import re

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def parse_relative_time_to_iso(text: str) -> str:
    """
    Convert strings like '3 hours ago', '2 days ago', '1 week ago' into ISO8601 UTC timestamps.
    If parsing fails, return current time.
    """
    if not text:
        return now_iso()

    text = text.lower()
    num = _extract_first_int(text)
    if num is None:
        return now_iso()

    if "minute" in text:
        dt = datetime.now(timezone.utc) - timedelta(minutes=num)
    elif "hour" in text:
        dt = datetime.now(timezone.utc) - timedelta(hours=num)
    elif "day" in text:
        dt = datetime.now(timezone.utc) - timedelta(days=num)
    elif "week" in text:
        dt = datetime.now(timezone.utc) - timedelta(weeks=num)
    elif "month" in text:
        # approximate months as 30 days
        dt = datetime.now(timezone.utc) - timedelta(days=30 * num)
    elif "year" in text:
        dt = datetime.now(timezone.utc) - timedelta(days=365 * num)
    else:
        dt = datetime.now(timezone.utc)

    return dt.isoformat()

def _extract_first_int(s: str):
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None