"""
Turns the free-text deadline phrase preserved by Module 2 (``meta_info.deadline``)
into a real date. Module 2 deliberately does not resolve phrases such as
"next Friday", so this module resolves them relative to an anchor date
(the day the memory was recorded).

Returns ``None`` when a phrase cannot be resolved with confidence; the tracker
then flags the commitment for review instead of guessing.
"""
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Optional

from dateutil import parser as dateutil_parser

_WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_LEADING_FILLER = re.compile(r"^(?:by|on|before|till|until|due|latest|no later than)\s+")
_ORDINAL = re.compile(r"(?<=\d)(?:st|nd|rd|th)\b")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:$|[t\s])")
_NUMERIC = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}$")
_MONTH_NAME = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b")
_YEAR = re.compile(r"\b\d{4}\b")
_SMALL_NUMBER = re.compile(r"\b\d{1,2}\b")
_IN_N = re.compile(r"^in (\d{1,3}) (day|days|week|weeks)$")
_WEEKDAY_PHRASE = re.compile(r"^(next|this|coming)?\s*([a-z]+)$")


def _clean(text: str) -> str:
    s = str(text).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = _LEADING_FILLER.sub("", s)
    s = _ORDINAL.sub("", s)
    s = re.sub(r"\bof\b", " ", s)          # "15th of November"
    s = re.sub(r"\bthe\b", " ", s)         # "end of the month"
    s = re.sub(r"[.,]+$", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()


def _end_of_month(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def _parse_relative(s: str, anchor: date) -> Optional[date]:
    if s in ("today", "tonight", "eod", "end day"):
        return anchor
    if s == "tomorrow":
        return anchor + timedelta(days=1)
    if s == "day after tomorrow":
        return anchor + timedelta(days=2)

    match = _IN_N.match(s)
    if match:
        amount = int(match.group(1))
        return anchor + timedelta(days=amount * (7 if match.group(2).startswith("week") else 1))

    if s == "end month":  # "end of the month" after cleaning
        return _end_of_month(anchor.year, anchor.month)
    if s == "end week":
        # Friday of the anchor's week (the next Friday if the anchor is already past it).
        return anchor + timedelta(days=(4 - anchor.weekday()) % 7)

    match = _WEEKDAY_PHRASE.match(s)
    if match and match.group(2) in _WEEKDAYS:
        target = _WEEKDAYS[match.group(2)]
        ahead = (target - anchor.weekday()) % 7
        if match.group(1) == "next" and ahead == 0:
            ahead = 7  # "next Monday" said on a Monday means a week later
        return anchor + timedelta(days=ahead)
    return None


def _parse_absolute(s: str, anchor: date) -> Optional[date]:
    iso = _ISO.match(s)
    if iso:
        try:
            return date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        except ValueError:
            return None

    numeric = bool(_NUMERIC.match(s))
    if not numeric and not _MONTH_NAME.search(s):
        return None

    has_year = bool(_YEAR.search(s)) or numeric
    month_only = (not numeric) and not _SMALL_NUMBER.search(_YEAR.sub(" ", s))

    default = datetime(anchor.year, 1, 1)
    try:
        parsed = dateutil_parser.parse(s, default=default, dayfirst=True, fuzzy=False).date()
    except (ValueError, OverflowError):
        return None

    if month_only:
        parsed = _end_of_month(parsed.year, parsed.month)

    # "15 November" with no year: use the next occurrence on/after the anchor date.
    if not has_year and parsed < anchor:
        try:
            parsed = parsed.replace(year=parsed.year + 1)
        except ValueError:  # 29 Feb
            return None
    return parsed


def parse_deadline(text: object, anchor: date) -> Optional[date]:
    """Resolve a deadline phrase to a date, or ``None`` if it is missing or unclear."""
    if text is None or not str(text).strip():
        return None
    cleaned = _clean(text)
    if not cleaned:
        return None
    return _parse_relative(cleaned, anchor) or _parse_absolute(cleaned, anchor)
