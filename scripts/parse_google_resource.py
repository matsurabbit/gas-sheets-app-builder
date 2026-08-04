#!/usr/bin/env python3
"""Normalize Google Sheets and Drive folder URLs or IDs into JSON."""

from __future__ import annotations

import argparse
import json
import re
from urllib.parse import parse_qs, urlparse


ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,}$")
SHEET_PATTERN = re.compile(r"/spreadsheets/d/([A-Za-z0-9_-]+)")
FOLDER_PATTERN = re.compile(r"/folders/([A-Za-z0-9_-]+)")


def parse_resource(value: str) -> dict[str, str | None]:
    raw = value.strip()
    if ID_PATTERN.fullmatch(raw):
        return {"type": "unknown", "id": raw, "gid": None, "input": raw}

    parsed = urlparse(raw)
    sheet_match = SHEET_PATTERN.search(parsed.path)
    folder_match = FOLDER_PATTERN.search(parsed.path)

    resource_type = "unknown"
    resource_id = None
    if sheet_match:
        resource_type = "spreadsheet"
        resource_id = sheet_match.group(1)
    elif folder_match:
        resource_type = "folder"
        resource_id = folder_match.group(1)

    query = parse_qs(parsed.query)
    fragment = parse_qs(parsed.fragment)
    gid_values = query.get("gid") or fragment.get("gid") or []
    gid = gid_values[0] if gid_values else None

    if resource_id is None:
        raise ValueError(f"Google SheetsまたはDriveフォルダのURL/IDとして解釈できません: {raw}")

    return {"type": resource_type, "id": resource_id, "gid": gid, "input": raw}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("values", nargs="+", help="Google resource URLs or IDs")
    args = parser.parse_args()

    try:
        result = [parse_resource(value) for value in args.values]
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
