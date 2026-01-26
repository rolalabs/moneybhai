
from datetime import datetime, timezone

def convert_iso_to_datetime(iso_str: str) -> datetime | None:
    '''
    convert datetime is str isoformat to datetime object
    Add timezone info if needed
    '''
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None