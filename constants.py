import os
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============================================================================
# FASTAPI SETTINGS
# ============================================================================

CORS_ORIGINS = [
    "http://localhost:5173",
    "https://hammerhead-app-bqr7z.ondigitalocean.app",
    "https://api.pace-af-tool.com",
    "https://pace-af-tool.com",
    "https://www.api.pace-af-tool.com",
    "https://www.pace-af-tool.com",
]

ALLOWED_FILE_TYPES = [
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
]

# ============================================================================
# SESSION SETTINGS
# ============================================================================

SESSION_TTL_SECONDS = 1800

# ============================================================================
# COLUMN DEFINITIONS
# ============================================================================

REQUIRED_COLUMNS = [
    'FULL_NAME', 'GRADE', 'ASSIGNED_PAS_CLEARTEXT', 'DAFSC', 'DOR',
    'DATE_ARRIVED_STATION', 'TAFMSD', 'REENL_ELIG_STATUS', 'ASSIGNED_PAS', 'PAFSC'
]

OPTIONAL_COLUMNS = [
    'GRADE_PERM_PROJ', 'UIF_CODE', 'UIF_DISPOSITION_DATE', '2AFSC', '3AFSC', '4AFSC'
]

PDF_COLUMNS = [
    'FULL_NAME', 'GRADE', 'DATE_ARRIVED_STATION', 'DAFSC',
    'ASSIGNED_PAS_CLEARTEXT', 'DOR', 'TAFMSD', 'ASSIGNED_PAS'
]

# ============================================================================
# GRADE AND PROMOTION MAPPINGS
# ============================================================================

GRADE_MAP = {
    "SRA": "E4",
    "SSG": "E5",
    "TSG": "E6",
    "MSG": "E7",
    "SMS": "E8"
}

PROMOTION_MAP = {
    "SRA": "E5",
    "SSG": "E6",
    "TSG": "E7",
    "MSG": "E8",
    "SMS": "E9"
}

PROMOTIONAL_MAP = {
    'SRA': 'SSG',
    'SSG': 'TSG',
    'TSG': 'MSG',
    'MSG': 'SMS',
    'SMS': 'CMS'
}

BOARDS = ['E5', 'E6', 'E7', 'E8', 'E9']

# ============================================================================
# CLOSEOUT DATES (SCODs)
# ============================================================================

SCODS = {
    'SRA': '31-MAR',
    'SSG': '31-JAN',
    'TSG': '30-NOV',
    'MSG': '30-SEP',
    'SMS': '31-JUL'
}

# ============================================================================
# TIME IN GRADE (TIG) REQUIREMENTS
# ============================================================================

# Base month for TIG calculation (DOR requirement date)
TIG = {
    'AB': '01-FEB',    # Chart shows 1 FEB for E1-E2
    'AMN': '01-FEB',   # Chart shows 1 FEB for E2-E3
    'A1C': '01-FEB',   # Chart shows 1 FEB for E3-E4
    'SRA': '01-FEB',   # Chart shows 1 FEB for E4-E5
    'SSG': '01-AUG',   # Chart shows 1 AUG for E5-E6
    'TSG': '01-JUL',   # Chart shows 1 JUL for E6-E7
    'MSG': '01-JUL',   # Chart shows 1 JUL for E7-E8
    'SMS': '01-MAR'    # Chart shows 1 MAR for E8-E9
}

# Time in grade months required
TIG_MONTHS_REQUIRED = {
    'AB': 6,     # 21/6 months per chart
    'AMN': 6,    # 22/6 months per chart
    'A1C': 10,   # 23/6 months per chart (Note: Regular is 28 months, BTZ is different)
    'SRA': 6,    # 24/6 months per chart
    'SSG': 23,   # 23/23 months per chart
    'TSG': 24,   # 24/23 months per chart (varies by cycle, using most common)
    'MSG': 20,   # 20/20 months per chart
    'SMS': 21    # 21/21 months per chart
}

# ============================================================================
# TIME IN SERVICE (TAFMSD) REQUIREMENTS
# ============================================================================

# Total active federal military service date = time in military (years)
# Based on TAFMSD/TIS REQUIRED column
TAFMSD = {
    'AB': 0.25,   # 3 months (1 AUG - 3 months = 1 MAY)
    'AMN': 0.5,   # 6 months (1 AUG - 6 months = 1 FEB)
    'A1C': 1.25,  # 15 months (1 AUG - 15 months)
    'SRA': 3,     # 3 years per chart
    'SSG': 5,     # 5 years per chart (1 JUL XX/5 YRS)
    'TSG': 8,     # 8 years per chart (1 JUL XX/8 YRS)
    'MSG': 11,    # 11 years per chart (1 MAR XX/11 YRS)
    'SMS': 14     # 14 years per chart (1 DEC XX/14 YRS)
}

# ============================================================================
# MANDATORY DATE OF SEPARATION (MDOS)
# ============================================================================

# Mandatory date of separation (MDOS column - must be on or after)
# This is the base month for MDOS calculation
MDOS = {
    'AB': '01-SEP',    # Per chart MDOS column
    'AMN': '01-SEP',   # Per chart MDOS column
    'A1C': '01-SEP',   # Per chart MDOS column
    'SRA': '01-SEP',   # Per chart MDOS column
    'SSG': '01-AUG',   # Per chart MDOS column
    'TSG': '01-AUG',   # Per chart MDOS column
    'MSG': '01-APR',   # Per chart MDOS column
    'SMS': '01-JAN'    # Per chart MDOS column
}

# ============================================================================
# HIGHER TENURE (HYT) LIMITS
# ============================================================================

# Main higher tenure (standard HYT limits, in years)
MAIN_HIGHER_TENURE = {
    'AB': 6,
    'AMN': 6,
    'A1C': 8,
    'SRA': 10,
    'SSG': 20,
    'TSG': 22,
    'MSG': 24,
    'SMS': 26
}

# Exception higher tenure (extended HYT limits, in years)
# use cases are people between the HYT_EXTENSION_DATES
EXCEPTION_HIGHER_TENURE = {
    'AB': 8,
    'AMN': 8,
    'A1C': 10,
    'SRA': 12,
    'SSG': 22,
    'TSG': 24,
    'MSG': 26,
    'SMS': 28
}

# ============================================================================
# AFSC SKILL LEVEL MAPPING
# ============================================================================

# PAFSC skill level mapping 5th digit of the AFSC: ex -3F0X1)
PAFSC_MAP = {
    'AB': '3',
    'AMN': '3',
    'A1C': '3',
    'SRA': '5',
    'SSG': '7',
    'TSG': '7',
    'MSG': '7',
    'SMS': '9'
}

# ============================================================================
# REENLISTMENT CODES
# ============================================================================

RE_CODES = {
    "2A": "AFPC Denied Reenlistment",
    "2B": "Discharged, General.",
    "2C": "Involuntary separation.",
    "2F": "Undergoing Rehab",
    "2G": "Substance Abuse, Drugs",
    "2H": "Substance Abuse, Alcohol",
    "2J": "Under investigation",
    "2K": "Involuntary Separation.",
    "2M": "Sentenced under UCMJ",
    "2P": "AWOL; deserter.",
    "2W": "Retired and recalled to AD",
    "2X": "Not selected for Reenlistment.",
    "4H": "Article 15.",
    "4I": "Control Roster.",
    "4L": "Separated, Commissioning program.",
    "4M": "Breach of enlistment.",
    "4N": "Convicted, Civil Court."
}

# ============================================================================
# HYT EXEMPTION DATE RANGES
# ============================================================================

EXCEPTION_HYT_START_DATE = datetime(2023, 12, 8)
EXCEPTION_HYT_END_DATE = datetime(2026, 9, 30)


# ============================================================================
# FONT MANAGEMENT
# ============================================================================

PDF_FONT_PATH = os.path.join(os.path.dirname(__file__), 'fonts', 'calibri.ttf')
PDF_BOLD_FONT_PATH = os.path.join(os.path.dirname(__file__), 'fonts', 'calibrib.ttf')

PDF_REGULAR_FONT_NAME = 'Calibri'
PDF_BOLD_FONT_NAME = 'Calibri-Bold'
FALLBACK_FONT_NAME = 'Helvetica'
FALLBACK_BOLD_FONT_NAME = 'Helvetica-Bold'

PDF_FONTS = (FALLBACK_FONT_NAME, FALLBACK_BOLD_FONT_NAME)

try:
    pdfmetrics.registerFont(TTFont(PDF_REGULAR_FONT_NAME, PDF_FONT_PATH))
    pdfmetrics.registerFont(TTFont(PDF_BOLD_FONT_NAME, PDF_BOLD_FONT_PATH))
    PDF_FONTS = (PDF_REGULAR_FONT_NAME, PDF_BOLD_FONT_NAME)
    print("Successfully registered custom fonts for PDF generation.")
except Exception as e:
    print(f"Warning: Could not load custom fonts ({e}). Using fallback fonts.")


# ============================================================================
# PDF GENERATION SETTINGS
# ============================================================================

# Table column percentages for eligible tables
ELIGIBLE_TABLE_WIDTHS = [0.26, 0.08, 0.1, 0.1, 0.26, 0.05, 0.05, 0.05, 0.05]

# Table column percentages for ineligible tables
INELIGIBLE_TABLE_WIDTHS = [0.25, 0.08, 0.1, 0.1, 0.25, 0.2]

# Table column percentages for initial MEL tables
INITIAL_MEL_TABLE_WIDTHS = [0.22, 0.07, 0.1, 0.08, 0.23, 0.1, 0.1, 0.1]

# Table column percentages for initial MEL ineligible tables
INITIAL_MEL_INELIGIBLE_TABLE_WIDTHS = [0.22, 0.07, 0.1, 0.08, 0.3, 0.23]

# Font paths (relative to project root)
FONT_BASE_DIR = 'fonts'
PDF_FONT_PATH = 'calibri.ttf'
PDF_BOLD_FONT_PATH = 'calibrib.ttf'

# Image paths (relative to project root)
IMAGE_BASE_DIR = 'images'
DEFAULT_LOGO_PATH = 'fiftyonefss.jpeg'
AFPC_LOGO_PATH = 'afpc.png'

# PDF Table Headers
ELIGIBLE_HEADER_ROW = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'NRN', 'P', 'MP', 'PN']
INELIGIBLE_HEADER_ROW = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'REASON NOT ELIGIBLE']
INITIAL_MEL_HEADER_ROW = ['FULL NAME', 'GRADE', 'DAS', 'DAFSC', 'UNIT', 'DOR', 'TAFMSD', 'PASCODE']
INITIAL_MEL_INELIGIBLE_HEADER_ROW = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'REASON']

# ============================================================================
# UTILITY CONSTANTS
# ============================================================================

# Small unit threshold
SMALL_UNIT_THRESHOLD = 10

# Maximum name/unit length for display
MAX_NAME_LENGTH = 30
MAX_UNIT_LENGTH = 25

# Date format strings
DATE_FORMAT_INPUT = "%d-%b-%Y"
DATE_FORMAT_DISPLAY = "%d %B %Y"