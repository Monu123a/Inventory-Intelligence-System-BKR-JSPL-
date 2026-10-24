from datetime import date, datetime
from typing import Optional, Union

def parse_date_param(val: Optional[Union[date, datetime, str]]) -> Optional[date]:
    """
    Safely parses a date parameter from query params, request bodies, or internal callers.
    Gracefully handles None, empty strings, whitespace, 'null'/'undefined', date objects,
    datetime objects, and common string formats (YYYY-MM-DD, DD/MM/YYYY, ISO datetime).
    Prevents FastAPI 422 Unprocessable Entity errors when frontend submits empty string filters.
    """
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned or cleaned.lower() in ("none", "null", "undefined", '""', "''"):
            return None
        # ISO format YYYY-MM-DD (e.g. 2026-10-24 or 2026-10-24T00:00:00)
        try:
            return datetime.strptime(cleaned[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
        # DD/MM/YYYY or DD-MM-YYYY or YYYY/MM/DD
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(cleaned[:10], fmt).date()
            except ValueError:
                pass
    return None
