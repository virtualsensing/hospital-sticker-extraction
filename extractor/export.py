"""Export extracted data to JSON and CSV."""

import csv
import json
from pathlib import Path

from .fields import FIELDS, FIELD_LABELS


def to_json(records: list[dict], pretty: bool = True) -> str:
    """Convert extracted records to a JSON string.

    Internal fields (_warnings, _status, _error, _source_file) are included
    for transparency but can be stripped with strip_internal=True.
    """
    indent = 2 if pretty else None
    return json.dumps(records, indent=indent, ensure_ascii=False)


def save_json(records: list[dict], output_path: str | Path) -> Path:
    """Save extracted records to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_json(records), encoding="utf-8")
    return path


def save_csv(records: list[dict], output_path: str | Path) -> Path:
    """Save extracted records to a CSV file.

    Uses human-readable column headers. Internal fields (_warnings etc.)
    are included as additional columns.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Build header: canonical fields + internal fields
    internal_fields = ["_source_file", "_status", "_warnings"]
    headers = list(FIELDS) + internal_fields
    display_headers = [FIELD_LABELS.get(f, f) for f in FIELDS] + [
        "Source File", "Status", "Warnings"
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(display_headers)

        for record in records:
            row = []
            for field in headers:
                val = record.get(field)
                if isinstance(val, list):
                    val = "; ".join(str(v) for v in val)
                elif val is None:
                    val = ""
                row.append(val)
            writer.writerow(row)

    return path


def print_record(record: dict, file=None) -> None:
    """Pretty-print a single record to stdout."""
    import sys
    out = file or sys.stdout

    print("=" * 60, file=out)
    source = record.get("_source_file", "unknown")
    status = record.get("_status", "unknown")
    print(f"Source: {source}  |  Status: {status}", file=out)
    print("-" * 60, file=out)

    for field in FIELDS:
        label = FIELD_LABELS[field]
        val = record.get(field) or "—"
        print(f"  {label:.<28s} {val}", file=out)

    warnings = record.get("_warnings", [])
    if warnings:
        print(f"\n  Warnings:", file=out)
        for w in warnings:
            print(f"    ! {w}", file=out)

    print(file=out)
