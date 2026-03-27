#!/usr/bin/env python3

"""Generate kiosk viewer JSON from the latest duties PDF."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.build_viewer_data import _parse_pdf_text

PDF_PATH = BASE_DIR / "data/latest.pdf"
OUTPUT_PATH = BASE_DIR / "data/viewer_data.json"


def generate_data(pdf_path: Path = PDF_PATH, output_path: Path = OUTPUT_PATH) -> Path:
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
    output_path = generate_data()
    print(f"Generated viewer data: {output_path}")


if __name__ == "__main__":
    main()
