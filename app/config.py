"""Βασικές ρυθμίσεις για το project."""

from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
LATEST_PDF_PATH = DATA_DIR / "latest.pdf"

LOGIN_BASE_URL = "https://www.fsa-platforma.gr"
PDF_BASE_URL = "https://fsa-efimeries.gr"

LOGIN_URL = f"{LOGIN_BASE_URL}/fsa/Account/Login"
DUTIES_PAGE_URL = f"{PDF_BASE_URL}/Pharmacist/DutiesPDF"
DUTIES_FORM_URL = f"{PDF_BASE_URL}/Pharmacist/DutiesPrint"
DUTIES_PDF_URL = f"{PDF_BASE_URL}/Pharmacist/DutiesPrint/Print"

FSA_EMAIL = os.getenv("FSA_EMAIL", "")
FSA_PASSWORD = os.getenv("FSA_PASSWORD", "")