"""
Utility to parse uploaded CSV or XLSX files into a list of identity dicts.

Expected columns (case-insensitive, flexible naming):
  - username / user / login / samaccountname / userid
  - email / mail / emailaddress / e-mail
  - display_name / displayname / name / full_name / cn
  - department / dept

Any unrecognised columns are stored in extra_data.
"""

import csv
import io
from typing import IO, List, Dict, Any

COLUMN_ALIASES: Dict[str, List[str]] = {
    "username": ["username", "user", "login", "samaccountname", "userid", "user_id", "account"],
    "email": ["email", "mail", "emailaddress", "e-mail", "email_address"],
    "display_name": ["display_name", "displayname", "name", "full_name", "cn", "fullname"],
    "department": ["department", "dept", "division"],
}


def _normalise_header(header: str) -> str:
    return header.strip().lower().replace(" ", "_").replace("-", "_")


def _map_headers(raw_headers: List[str]) -> Dict[str, str]:
    """Return {raw_header: canonical_field} for known columns."""
    mapping: Dict[str, str] = {}
    for raw in raw_headers:
        norm = _normalise_header(raw)
        for canonical, aliases in COLUMN_ALIASES.items():
            if norm in aliases:
                mapping[raw] = canonical
                break
    return mapping


def parse_file(file_obj: IO[bytes], filename: str) -> List[Dict[str, Any]]:
    """Parse a CSV or XLSX file and return a list of identity dicts."""
    filename_lower = filename.lower()
    if filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
        return _parse_excel(file_obj)
    else:
        return _parse_csv(file_obj)


def _parse_csv(file_obj: IO[bytes]) -> List[Dict[str, Any]]:
    content = file_obj.read()
    # Try UTF-8, fall back to latin-1
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    mapping = _map_headers(list(headers))
    return _rows_to_identities(reader, mapping, list(headers))


def _parse_excel(file_obj: IO[bytes]) -> List[Dict[str, Any]]:
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl is required for XLSX support: pip install openpyxl")

    wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    raw_headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    mapping = _map_headers(raw_headers)

    identities = []
    for row in rows[1:]:
        if all(v is None for v in row):
            continue
        row_dict = {raw_headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row)}
        identities.append(_map_row(row_dict, mapping, raw_headers))

    return identities


def _rows_to_identities(reader, mapping: Dict[str, str], headers: List[str]) -> List[Dict[str, Any]]:
    identities = []
    for row in reader:
        identities.append(_map_row(dict(row), mapping, headers))
    return identities


def _map_row(row: Dict[str, Any], mapping: Dict[str, str], all_headers: List[str]) -> Dict[str, Any]:
    identity: Dict[str, Any] = {
        "username": "",
        "email": None,
        "display_name": None,
        "department": None,
        "extra_data": {},
    }
    known_raws = set(mapping.keys())
    for raw_header, value in row.items():
        if raw_header in known_raws:
            canonical = mapping[raw_header]
            identity[canonical] = value or None
        else:
            if value:
                identity["extra_data"][raw_header] = value

    return identity
