"""Refreshes the local duties PDF using the Playwright downloader only."""

from __future__ import annotations

from datetime import date as dt_date
from pathlib import Path
import sys

from app.config import DATA_DIR, LATEST_PDF_PATH
from app.fetch_pdf_playwright import fetch_duties_pdf as fetch_with_playwright


def _validate_pdf(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"file does not exist: {path}")

    file_size = path.stat().st_size
    if file_size <= 10 * 1024:
        raise RuntimeError(f"file is too small ({file_size} bytes): {path}")

    with path.open("rb") as pdf_file:
        header = pdf_file.read(4)

    if header != b"%PDF":
        raise RuntimeError(f"file does not start with %PDF header: {path}")


def refresh_pdf(duty_date: str | None = None) -> Path:
    duty_date = duty_date or str(dt_date.today())
    tmp_path = DATA_DIR / "latest.pdf.download"

    print(f"Starting PDF download for {duty_date} with Playwright")

    try:
        if tmp_path.exists():
            tmp_path.unlink()

        fetch_with_playwright(duty_date, tmp_path)
        print(f"Download completed: {tmp_path}")

        _validate_pdf(tmp_path)
        print("Validation passed: file exists, is larger than 10 KB, and starts with %PDF")

        tmp_path.replace(LATEST_PDF_PATH)
        print(f"Replaced latest PDF: {LATEST_PDF_PATH}")
        return LATEST_PDF_PATH
    except Exception as exc:
        print(f"Refresh failed: {exc}", file=sys.stderr)
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def main() -> None:
    try:
        saved_path = refresh_pdf()
        print(f"Saved PDF to: {saved_path}")
    except Exception:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
