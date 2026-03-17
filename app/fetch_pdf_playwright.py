"""Κατεβάζει το PDF εφημεριών μέσω πραγματικού browser automation."""

from __future__ import annotations

from datetime import date as dt_date
from pathlib import Path
import json
import os

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LATEST_PDF_PATH = DATA_DIR / "latest.pdf"

LOGIN_URL = "https://www.fsa-platforma.gr/fsa/Account/Login"
HANDOFF_URL = "https://fsa-efimeries.gr/pharmacist/1894"
DUTIES_URL = "https://fsa-efimeries.gr/Pharmacist/DutiesPDF"

FSA_EMAIL = os.getenv("FSA_EMAIL", "")
FSA_PASSWORD = os.getenv("FSA_PASSWORD", "")


# ----------------------------------------
# Βοηθητική συνάρτηση: ασφαλής αναμονή στοιχείου
# ----------------------------------------
def wait_fill_click(page, selector: str, value: str | None = None, click: bool = False) -> None:
    """
    Περιμένει να εμφανιστεί στοιχείο στη σελίδα.
    Αν δοθεί value, το συμπληρώνει.
    Αν click=True, κάνει click.
    """
    locator = page.locator(selector)
    locator.wait_for(state="visible", timeout=30000)

    if value is not None:
        locator.fill(value)

    if click:
        locator.click()


# ----------------------------------------
# Κύρια ροή browser automation
# ----------------------------------------
def fetch_duties_pdf(duty_date: str, output_path: Path = LATEST_PDF_PATH) -> Path:
    """
    1. Ανοίγει πραγματικό Chromium.
    2. Κάνει login.
    3. Πηγαίνει στη σελίδα DutiesPDF.
    4. Βάζει ημερομηνία.
    5. Πατάει το κουμπί προεπισκόπησης.
    6. Πατάει το κουμπί PDF και αποθηκεύει το αρχείο.
    """
    if not FSA_EMAIL or not FSA_PASSWORD:
        raise RuntimeError("Λείπουν FSA_EMAIL / FSA_PASSWORD από το .env")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        # ----------------------------------------
        # 1. Login
        # ----------------------------------------
        print("Opening login page")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        print(f"URL: {page.url}")

        # Τα selectors μπορεί να χρειαστούν μικρή προσαρμογή αν η σελίδα αλλάξει.
        wait_fill_click(page, 'input[name="Email"]', value=FSA_EMAIL)
        wait_fill_click(page, 'input[name="Password"]', value=FSA_PASSWORD)

        # Submit login form
        # Προτιμάμε form submit button. Αν δεν πιάσει, θα το αλλάξουμε μετά από inspection.
        login_button = page.locator(
            'form button[type="submit"], form input[type="submit"], '
            'button[name="login"], input[name="login"]'
        )
        login_button.first.wait_for(state="visible", timeout=30000)
        print("Submitting login")
        login_button.first.click()

        page.wait_for_load_state("networkidle", timeout=30000)
        print(f"URL after login: {page.url}")
        (LOGS_DIR / "playwright_cookies_after_login.json").write_text(
            json.dumps(context.cookies(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # ----------------------------------------
        # 2. Cross-domain handoff
        # ----------------------------------------
        print("Opening pharmacist handoff")
        page.goto(HANDOFF_URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=30000)
        print(f"URL after opening /pharmacist/1894: {page.url}")
        handoff_cookies = [
            cookie for cookie in context.cookies() if "fsa-efimeries.gr" in cookie.get("domain", "")
        ]
        (LOGS_DIR / "playwright_cookies_after_handoff.json").write_text(
            json.dumps(handoff_cookies, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # ----------------------------------------
        # 3. Μετάβαση στη σελίδα ημερομηνίας
        # ----------------------------------------
        print("Opening DutiesPDF")
        page.goto(DUTIES_URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=30000)
        print(f"URL after opening DutiesPDF: {page.url}")

        # ----------------------------------------
        # 4. Συμπλήρωση ημερομηνίας
        # ----------------------------------------
        date_input = page.locator('input[name="date"], input[type="date"], input.form-control')
        date_input.first.wait_for(state="visible", timeout=30000)
        print(f"Filling date: {duty_date}")
        date_input.first.fill(duty_date)
        print(f"URL after filling date: {page.url}")

        # ----------------------------------------
        # 5. Προεπισκόπηση
        # ----------------------------------------
        preview_button = page.locator(
            '#submit1, button:has-text("Υποβολή"), input[value*="Υποβολ"], '
            'button[type="submit"], input[type="submit"]'
        )
        preview_button.first.wait_for(state="visible", timeout=30000)
        print("Clicking preview")

        try:
            with context.expect_page(timeout=5000) as new_page_info:
                preview_button.first.click()
            preview_page = new_page_info.value
            preview_page.wait_for_load_state("domcontentloaded", timeout=30000)
            preview_page.wait_for_load_state("networkidle", timeout=30000)
            page = preview_page
        except PlaywrightTimeoutError:
            preview_button.first.click()
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=30000)

        print(f"Current URL after preview: {page.url}")
        print(page.url)
        (LOGS_DIR / "playwright_cookies_after_dutiesprint.json").write_text(
            json.dumps(context.cookies(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        try:
            page.wait_for_function(
                """
                () => {
                    const tables = document.querySelectorAll('#pdfcontent table').length;
                    const rows = document.querySelectorAll('#pdfcontent tbody tr').length;
                    return tables > 0 && rows > 0;
                }
                """,
                timeout=60000,
            )
        except PlaywrightTimeoutError as exc:
            preview_html = page.content()
            (LOGS_DIR / "playwright_after_preview.html").write_text(
                preview_html,
                encoding="utf-8",
                errors="ignore",
            )
            page.screenshot(path=str(LOGS_DIR / "playwright_after_preview.png"), full_page=True)
            pdfcontent_inner_html = page.locator("#pdfcontent").inner_html()
            (LOGS_DIR / "playwright_pdfcontent_inner.html").write_text(
                pdfcontent_inner_html,
                encoding="utf-8",
                errors="ignore",
            )
            pdfcontent_tables = page.locator("#pdfcontent table").count()
            pdfcontent_rows = page.locator("#pdfcontent tbody tr").count()
            print(f"PDF content URL: {page.url}")
            print(f"PDF content tables: {pdfcontent_tables}")
            print(f"PDF content rows: {pdfcontent_rows}")
            print(f"PDF content preview: {pdfcontent_inner_html[:500]}")
            raise RuntimeError(
                "Preview content did not populate within 60 seconds; not clicking PDF."
            ) from exc

        preview_html = page.content()
        (LOGS_DIR / "playwright_after_preview.html").write_text(
            preview_html,
            encoding="utf-8",
            errors="ignore",
        )
        page.screenshot(path=str(LOGS_DIR / "playwright_after_preview.png"), full_page=True)
        pdfcontent_inner_html = page.locator("#pdfcontent").inner_html()
        (LOGS_DIR / "playwright_pdfcontent_inner.html").write_text(
            pdfcontent_inner_html,
            encoding="utf-8",
            errors="ignore",
        )
        pdfcontent_tables = page.locator("#pdfcontent table").count()
        pdfcontent_rows = page.locator("#pdfcontent tbody tr").count()
        print(f"PDF content URL: {page.url}")
        print(f"PDF content tables: {pdfcontent_tables}")
        print(f"PDF content rows: {pdfcontent_rows}")
        print(f"PDF content preview: {pdfcontent_inner_html[:500]}")

        # ----------------------------------------
        # 6. Κατέβασμα PDF
        # ----------------------------------------
        print("Looking for PDF button")
        pdf_button = page.locator(
            '#PDF, button#PDF, input[name="PDF"], input[value*="PDF"], button:has-text("PDF")'
        )
        pdf_button.first.wait_for(state="visible", timeout=30000)

        with page.expect_download(timeout=30000) as download_info:
            pdf_button.first.click()

        download = download_info.value
        download.save_as(str(output_path))

        browser.close()
        return output_path


# ----------------------------------------
# Εκτέλεση από terminal
# ----------------------------------------
def main() -> None:
    """
    Τοπική δοκιμή.
    """
    duty_date = str(dt_date.today())  # YYYY-MM-DD
    saved_path = fetch_duties_pdf(duty_date)
    print(f"Το PDF αποθηκεύτηκε στο: {saved_path}")


if __name__ == "__main__":
    main()
