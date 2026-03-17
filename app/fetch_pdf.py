"""Κατεβάζει το PDF εφημεριών από το site και το αποθηκεύει τοπικά."""

from __future__ import annotations

from datetime import date as dt_date
from typing import Optional

import requests
from bs4 import BeautifulSoup

from app.config import (
    DUTIES_FORM_URL,
    DUTIES_PAGE_URL,
    DUTIES_PDF_URL,
    FSA_EMAIL,
    FSA_PASSWORD,
    LATEST_PDF_PATH,
    LOGIN_URL,
    LOGS_DIR,
)

# ----------------------------------------
# Βοηθητική συνάρτηση: βρίσκει το anti-forgery token από HTML form
# ----------------------------------------
def extract_verification_token(html: str) -> str:
    """
    Διαβάζει το HTML μιας σελίδας και επιστρέφει την τιμή του
    hidden input '__RequestVerificationToken'.

    Αν δεν το βρει, σηκώνει ValueError.
    """
    soup = BeautifulSoup(html, "lxml")
    token_input = soup.find("input", {"name": "__RequestVerificationToken"})
    if not token_input:
        raise ValueError("Δεν βρέθηκε '__RequestVerificationToken' στο HTML.")

    token_value = token_input.get("value", "").strip()
    if not token_value:
        raise ValueError("Το '__RequestVerificationToken' βρέθηκε αλλά είναι κενό.")

    return token_value


# ----------------------------------------
# Εξαγωγή του HTML που θα σταλεί ως pdfhtml
# ----------------------------------------
def extract_pdfcontent_html(html: str) -> str:
    """
    Παίρνει το raw HTML της σελίδας DutiesPrint και επιστρέφει ακριβώς
    το inner HTML του div#pdfcontent, χωρίς BeautifulSoup re-formatting.

    Αυτό είναι πιο κοντά στο jQuery $("#pdfcontent").html().
    """
    marker = '<div id="pdfcontent">'
    start_idx = html.find(marker)
    if start_idx == -1:
        raise ValueError("Δεν βρέθηκε το div με id='pdfcontent'.")

    # Ξεκινάμε αμέσως μετά το opening tag
    content_start = start_idx + len(marker)

    # Θέλουμε να βρούμε το matching closing </div> του pdfcontent
    i = content_start
    depth = 1

    while i < len(html):
        next_open = html.find("<div", i)
        next_close = html.find("</div>", i)

        if next_close == -1:
            raise ValueError("Δεν βρέθηκε closing </div> για το div#pdfcontent.")

        if next_open != -1 and next_open < next_close:
            depth += 1
            i = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                content_end = next_close
                inner_html = html[content_start:content_end].strip()
                if not inner_html:
                    raise ValueError("Το div#pdfcontent βρέθηκε αλλά είναι κενό.")
                return inner_html
            i = next_close + 6

    raise ValueError("Αποτυχία εξαγωγής inner HTML από το div#pdfcontent.")

# ----------------------------------------
# Login στο fsa-platforma.gr
# ----------------------------------------
def login(session: requests.Session) -> None:
    """
    1. Κάνει GET στη σελίδα login για να πάρει cookies + token.
    2. Κάνει POST με email/password/token.
    3. Ελέγχει αν το login πέτυχε.

    Το session κρατάει αυτόματα τα cookies.
    """
    # Βήμα 1: GET login page
    response_get = session.get(LOGIN_URL, timeout=30)
    response_get.raise_for_status()

    # Παίρνουμε το anti-forgery token από το HTML της φόρμας login
    verification_token = extract_verification_token(response_get.text)

    # Βήμα 2: POST login form
    payload = {
        "__RequestVerificationToken": verification_token,
        "Email": FSA_EMAIL,
        "Password": FSA_PASSWORD,
        "AcceptLow": "false",
    }

    response_post = session.post(
        LOGIN_URL,
        data=payload,
        timeout=30,
        allow_redirects=True,
    )
    response_post.raise_for_status()

    # Απλός λειτουργικός έλεγχος:
    # Αν μετά το POST παραμένουμε στη σελίδα login, συνήθως κάτι πήγε στραβά.
    final_url = response_post.url.lower()
    if "account/login" in final_url:
        raise RuntimeError("Το login μάλλον απέτυχε. Έλεγξε credentials ή token flow.")


# ----------------------------------------
# Προετοιμασία της ημέρας στο fsa-efimeries.gr
# ----------------------------------------
def prepare_duties_date(session: requests.Session, duty_date: str) -> str:
    """
    1. Κάνει GET στη σελίδα DutiesPDF για να πάρει το anti-forgery token.
    2. Κάνει POST στο DutiesPrint με την ημερομηνία που θέλουμε.
    3. Επιστρέφει το HTML του DutiesPrint για περαιτέρω ανάλυση.
    """
    response_get = session.get(DUTIES_PAGE_URL, timeout=30)
    response_get.raise_for_status()

    verification_token = extract_verification_token(response_get.text)

    payload = {
        "date": duty_date,
        "print.css": "",
        "__RequestVerificationToken": verification_token,
    }

    response_post = session.post(
        DUTIES_FORM_URL,
        data=payload,
        timeout=30,
        allow_redirects=True,
    )
    response_post.raise_for_status()

    return response_post.text

# ----------------------------------------
# Κατέβασμα PDF
# ----------------------------------------
def download_pdf(session: requests.Session, duties_html: str, output_path: str) -> None:
    """
    Στέλνει στο PDF endpoint ακριβώς τα πεδία που στέλνει και ο browser:
    - pdfhtml = $("#pdfcontent").html()
    - __RequestVerificationToken = hidden input από το form

    Αν αποτύχει, αποθηκεύει το response body για debugging.
    """
    verification_token = extract_verification_token(duties_html)
    pdfhtml_value = extract_pdfcontent_html(duties_html)

    (LOGS_DIR / "pdfhtml_payload.html").write_text(
    pdfhtml_value,
    encoding="utf-8",
    errors="ignore",
    )

    payload = {
        "pdfhtml": pdfhtml_value,
        "__RequestVerificationToken": verification_token,
    }

    headers = {
        "Referer": DUTIES_FORM_URL,
    }

    response_pdf = session.post(
        DUTIES_PDF_URL,
        data=payload,
        headers=headers,
        timeout=60,
        allow_redirects=True,
    )

    if response_pdf.status_code >= 400:
        debug_path = LOGS_DIR / "print_error_response.html"
        debug_path.write_text(response_pdf.text, encoding="utf-8", errors="ignore")
        raise RuntimeError(
            f"Αποτυχία στο PDF endpoint: HTTP {response_pdf.status_code}. "
            f"Το response σώθηκε στο {debug_path}"
        )

    content_type = response_pdf.headers.get("Content-Type", "")
    if "application/pdf" not in content_type.lower():
        debug_path = LOGS_DIR / "print_non_pdf_response.html"
        debug_path.write_text(response_pdf.text, encoding="utf-8", errors="ignore")
        raise RuntimeError(
            f"Το endpoint δεν επέστρεψε PDF. Content-Type: {content_type}. "
            f"Το response σώθηκε στο {debug_path}"
        )

    with open(output_path, "wb") as pdf_file:
        pdf_file.write(response_pdf.content)


# ----------------------------------------
# Κεντρική ροή
# ----------------------------------------
def fetch_duties_pdf(duty_date: str, output_path: Optional[str] = None) -> str:
    """
    Εκτελεί όλη τη ροή:
    login -> επιλογή ημερομηνίας -> λήψη PDF

    Επιστρέφει το path του αποθηκευμένου PDF.
    """
    if not FSA_EMAIL or not FSA_PASSWORD:
        raise RuntimeError("Λείπουν FSA_EMAIL / FSA_PASSWORD από το .env")

    target_path = str(output_path or LATEST_PDF_PATH)

    with requests.Session() as session:
        # User-Agent ώστε να μοιάζει με κανονικό browser request
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux armv7l) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/145.0.0.0 Safari/537.36"
                )
            }
        )

        # 1. Login
        login(session)

        # 2. Δήλωση της ημερομηνίας που θέλουμε
        duties_html = prepare_duties_date(session, duty_date)

        # Σώζουμε την HTML του DutiesPrint για debugging
        (LOGS_DIR / "duties_print_response.html").write_text(
            duties_html,
            encoding="utf-8",
            errors="ignore",
        )

        # 3. Κατέβασμα του PDF
        download_pdf(session, duties_html, target_path)

    return target_path


# ----------------------------------------
# Εκτέλεση από terminal
# ----------------------------------------
def main() -> None:
    """
    Τοπική εκτέλεση για δοκιμή.
    """
    # Βάλε εδώ προσωρινά μια ημερομηνία για δοκιμή
    duty_date = str(dt_date.today())  # μορφή YYYY-MM-DD
    saved_path = fetch_duties_pdf(duty_date)
    print(f"Το PDF αποθηκεύτηκε στο: {saved_path}")


if __name__ == "__main__":
    main()