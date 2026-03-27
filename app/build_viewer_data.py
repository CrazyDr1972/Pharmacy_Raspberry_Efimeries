"""Builds structured viewer data from the downloaded pharmacy duties PDF."""

from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess

from app.config import DATA_DIR, LATEST_PDF_PATH

OUTPUT_JSON_PATH = DATA_DIR / "viewer_data.json"

AREA_END = 17
ADDRESS_END = 58
SECTION_RE = re.compile(r"\d.*ΠΡΩΙ")
PHONE_RE = re.compile(r"(?P<phone>\d{10})(?:\s+(?P<distance>.+))?$")
DATE_RE = re.compile(r"([Α-ΩA-ZΆ-Ώα-ωά-ώ]+,\s+\d{1,2}\s+[Α-ΩA-ZΆ-Ώα-ωά-ώ]+\s+\d{4})")
COLUMN_SPLIT_RE = re.compile(r"\s{2,}")


def _append_field(target: dict[str, str], key: str, value: str) -> None:
    value = value.strip()
    if not value:
        return
    if target[key]:
        target[key] = f"{target[key]} {value}"
    else:
        target[key] = value


def _split_entry_columns(prefix: str) -> tuple[str, str, str]:
    padded = prefix.ljust(AREA_END)
    area = padded[:AREA_END].strip()
    remainder = prefix[AREA_END:].strip()
    parts = [part.strip() for part in COLUMN_SPLIT_RE.split(remainder) if part.strip()]
    if len(parts) >= 2:
        return area, parts[0], " ".join(parts[1:])

    padded = prefix.ljust(ADDRESS_END)
    return (
        area,
        padded[AREA_END:ADDRESS_END].strip(),
        prefix[ADDRESS_END:].strip(),
    )


def _parse_pdf_text(text: str) -> dict[str, object]:
    lines = [line.rstrip() for line in text.replace("\f", "\n").splitlines()]

    date_line = ""
    current_section = ""
    entries: list[dict[str, str]] = []
    current_entry: dict[str, str] | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            continue

        if not date_line:
            date_match = DATE_RE.search(stripped)
            if date_match:
                date_line = date_match.group(1)

        if stripped.startswith("ΦΑΡΜΑΚΕΥΤΙΚΟΣ ΣΥΛΛΟΓΟΣ") or stripped.startswith("Eφημερεύοντα"):
            continue
        if stripped.startswith("Περιοχή") or stripped.startswith("Διεύθυνση"):
            continue
        if stripped.startswith("Φαρμακείο") or stripped.startswith("Τηλέφωνο"):
            continue
        if stripped.startswith("σελίδα "):
            continue

        if SECTION_RE.search(stripped):
            current_section = stripped
            current_entry = None
            continue

        phone_match = PHONE_RE.search(line)
        if phone_match:
            prefix = line[:phone_match.start()]
            area, address, pharmacy = _split_entry_columns(prefix)
            current_entry = {
                "section": current_section,
                "area": area,
                "address": address,
                "pharmacy": pharmacy,
                "phone": phone_match.group("phone").strip(),
                "distance": (phone_match.group("distance") or "").strip(),
            }
            entries.append(current_entry)
            continue

        if current_entry is None:
            continue

        continuation_parts = [part.strip() for part in COLUMN_SPLIT_RE.split(line.rstrip()) if part.strip()]
        if line[:ADDRESS_END].strip() == "" and continuation_parts:
            _append_field(current_entry, "pharmacy", continuation_parts[-1])
            continue

        padded = line.ljust(ADDRESS_END)
        _append_field(current_entry, "area", padded[:AREA_END])
        _append_field(current_entry, "address", padded[AREA_END:ADDRESS_END])
        _append_field(current_entry, "pharmacy", line[ADDRESS_END:])

    return {
        "date": date_line,
        "entries": entries,
    }


def build_viewer_data(pdf_path: Path = LATEST_PDF_PATH, output_path: Path = OUTPUT_JSON_PATH) -> Path:
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = _parse_pdf_text(result.stdout)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    output_path = build_viewer_data()
    print(f"Built viewer data: {output_path}")


if __name__ == "__main__":
    main()
