import os
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.units import inch
from reportlab.lib import colors

# ============================================================================
# FASTAPI SETTINGS
# ============================================================================

cors_origins = [
    "http://localhost:5173",
    "https://hammerhead-app-bqr7z.ondigitalocean.app",
    "https://api.pace-af-tool.com",
    "https://pace-af-tool.com",
    "https://www.api.pace-af-tool.com",
    "https://www.pace-af-tool.com",
]

allowed_types = [
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
]

# ============================================================================
# SESSION SETTINGS
# ============================================================================

session_ttl = 1800

# ============================================================================
# PATH SETTINGS
# ============================================================================

# Image paths (relative to project root)
images_dir = 'images'
default_logo = 'fiftyonefss.jpeg'
afpc_logo = 'afpc.png'

font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'calibri.ttf')
font_bold_path = os.path.join(os.path.dirname(__file__), 'fonts', 'calibrib.ttf')

# ============================================================================
# UTILITY CONSTANTS
# ============================================================================

# Small unit threshold
small_unit_threshold = 10

# Maximum name/unit length for display
max_name_length = 30
max_unit_length = 25

# Date format strings
date_input_format = "%d-%b-%Y"
date_display_format = "%d %B %Y"

# ============================================================================
# ERROR HANDLING CONSTANTS
# ============================================================================

# Session validation
SESSION_REQUIRED_KEYS = ['eligible_df', 'cycle', 'year', 'pascode_map']

# Data validation
DATA_VALIDATION_ERRORS = {
    'MISSING_COLUMNS': 'Missing required columns',
    'EMPTY_DATAFRAME': 'Uploaded file contains no data',
    'DUPLICATE_ENTRIES': 'Duplicate personnel entries detected',
    'INVALID_DATE_FORMAT': 'Invalid date format detected',
    'INVALID_GRADE': 'Invalid military grade detected',
    'MISSING_REQUIRED_DATA': 'Missing required data'
}

# File processing
MAX_FILE_SIZE_MB = 50
ALLOWED_FILE_EXTENSIONS = ['.csv', '.xlsx']

# Redis/Session constants
SESSION_ID_LENGTH = 36  # UUID4 length
SESSION_CLEANUP_INTERVAL = 3600  # 1 hour in seconds

# ============================================================================
# LOGGING CONSTANTS
# ============================================================================

LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================================
# API RESPONSE CONSTANTS
# ============================================================================

HTTP_STATUS_CODES = {
    'SUCCESS': 200,
    'CREATED': 201,
    'BAD_REQUEST': 400,
    'UNAUTHORIZED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'METHOD_NOT_ALLOWED': 405,
    'CONFLICT': 409,
    'UNPROCESSABLE_ENTITY': 422,
    'INTERNAL_SERVER_ERROR': 500,
    'SERVICE_UNAVAILABLE': 503
}

API_RESPONSES = {
    'UPLOAD_SUCCESS': 'Upload successful.',
    'PDF_GENERATION_FAILED': 'PDF generation failed',
    'SESSION_NOT_FOUND': 'Session not found',
    'INVALID_FILE_TYPE': 'Invalid file type. Only CSV or Excel files are allowed.',
    'PROCESSING_ERROR': 'Error processing data'
}

# ============================================================================
# PERFORMANCE CONSTANTS
# ============================================================================

# PDF generation limits
MAX_RECORDS_PER_PDF = 10000
MAX_PASCODES_PER_SESSION = 100
PDF_GENERATION_TIMEOUT = 300  # 5 minutes

# Memory management
MAX_DATAFRAME_MEMORY_MB = 100
CHUNK_SIZE_FOR_LARGE_FILES = 1000

# ============================================================================
# VALIDATION RULES
# ============================================================================

# Grade validation
VALID_GRADE_TRANSITIONS = {
    'AB': ['AMN'],
    'AMN': ['A1C'],
    'A1C': ['SRA'],
    'SRA': ['SSG'],
    'SSG': ['TSG'],
    'TSG': ['MSG'],
    'MSG': ['SMS'],
    'SMS': ['CMS']
}

# Date validation ranges
MIN_SERVICE_YEAR = 1950
MAX_SERVICE_YEAR = 2050
MIN_PROMOTION_CYCLE_YEAR = 2020
MAX_PROMOTION_CYCLE_YEAR = 2030

# AFSC validation
AFSC_LENGTH_REQUIREMENTS = {
    'MIN_LENGTH': 5,
    'MAX_LENGTH': 9
}

# Name validation
NAME_VALIDATION = {
    'MIN_LENGTH': 2,
    'MAX_LENGTH': 50,
    'ALLOWED_CHARACTERS': r'^[A-Za-z\s\-\'\.]+$'
}

# ============================================================================
# FEATURE FLAGS
# ============================================================================

FEATURES = {
    'ENABLE_BTZ_PROCESSING': True,
    'ENABLE_SMALL_UNIT_PROCESSING': True,
    'ENABLE_INTERACTIVE_CHECKBOXES': True,
    'ENABLE_COMPREHENSIVE_LOGGING': True,
    'ENABLE_DATA_VALIDATION': True,
    'ENABLE_SESSION_CLEANUP': True
}
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
    "AB": "E1",
    "AMN": "E2",
    "A1C": "E3",
    "SRA": "E4",
    "SSG": "E5",
    "TSG": "E6",
    "MSG": "E7",
    "SMS": "E8",
    "CMS": "E9",
    "2LT": "O1",
    "1LT": "O2",
    "CPT": "O3",
    "MAJ": "O4",
    "LTC": "O5",
    "COL": "O6",
    "BG": "O7",
    "MG": "O8",
    "LTG": "O9",
    "GEN": "O10"
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

# Officer ranks to be filtered out of enlisted promotion processing
OFFICER_RANKS = ['2LT', '1LT', 'CPT', 'MAJ', 'LTC', 'COL', 'BG', 'MG', 'LTG', 'GEN']

# Only enlisted ranks that can be processed for promotion
ENLISTED_RANKS = ['AB', 'AMN', 'A1C', 'SRA', 'SSG', 'TSG', 'MSG', 'SMS', 'CMS']

# ============================================================================
# CLOSEOUT DATES (SCODs)
# ============================================================================

SCODS = {
    'AB': '31-MAR',
    'AMN': '31-MAR',
    'A1C': '31-MAR',
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
    'AB': 0.25,  # 3 months
    'AMN': 0.5,  # 6 months
    'A1C': 1.25,  # 15 months
    'SRA': 3,  # 3 years
    'SSG': 5,  # 5 years
    'TSG': 8,  # 8 years
    'MSG': 11,  # 11 years
    'SMS': 14  # 14 years
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

hyt_start_date = datetime(2023, 12, 8)
hyt_end_date = datetime(2026, 9, 30)

# ============================================================================
# FONT MANAGEMENT
# ============================================================================

font_regular = 'Calibri'
font_bold = 'Calibri-Bold'
font_fallback = 'Helvetica'
font_fallback_bold = 'Helvetica-Bold'

pdf_fonts = (font_fallback, font_fallback_bold)

try:
    pdfmetrics.registerFont(TTFont(font_regular, font_path))
    pdfmetrics.registerFont(TTFont(font_bold, font_bold_path))
    pdf_fonts = (font_regular, font_bold)
    print("Successfully registered custom fonts for PDF generation.")
except Exception as e:
    print(f"Warning: Could not load custom fonts ({e}). Using fallback fonts.")

# Get font names from the pre-registered fonts
BODY_FONT, BOLD_FONT = pdf_fonts

# ============================================================================
# PDF GENERATION SHARED CONSTANTS
# ============================================================================

PDF_PAGE_WIDTH, PDF_PAGE_HEIGHT = landscape(letter)

# Margins and spacing
PDF_MARGIN = 0.5 * inch
PDF_CONTENT_FRAME_X = PDF_MARGIN
PDF_CONTENT_FRAME_Y = 1.05 * inch
PDF_CONTENT_FRAME_WIDTH = PDF_PAGE_WIDTH - (2 * PDF_MARGIN)
PDF_CONTENT_FRAME_HEIGHT = PDF_PAGE_HEIGHT - 2.735 * inch

# Header positioning
PDF_HEADER_CUI_Y = PDF_PAGE_HEIGHT - 0.3 * inch
PDF_HEADER_MAIN_Y = PDF_PAGE_HEIGHT - 0.8 * inch
PDF_HEADER_TITLE_Y_OFFSET = 0.1 * inch
PDF_HEADER_LINE_HEIGHT = 0.2 * inch
PDF_HEADER_SIGNATURE_X = 7.5 * inch
PDF_HEADER_PROMOTION_X = 5 * inch
PDF_HEADER_UNIT_DATA_X = 2 * inch

# Logo positioning
PDF_LOGO_SIZE = 1 * inch
PDF_LOGO_X = PDF_MARGIN
PDF_LOGO_Y_OFFSET = 0.8 * inch

# Footer positioning
PDF_FOOTER_BORDER_Y = 1.2 * inch
PDF_FOOTER_TEXT_Y = 0.75 * inch
PDF_FOOTER_BOTTOM_Y = 0.3 * inch

# Font sizes
PDF_FONT_SIZE_CUI = 10
PDF_FONT_SIZE_HEADER = 12
PDF_FONT_SIZE_SUBHEADER = 10
PDF_FONT_SIZE_FOOTER = 8
PDF_FONT_SIZE_FOOTER_BOTTOM = 12

# Colors
PDF_HEADER_COLOR = colors.Color(23 / 255, 54 / 255, 93 / 255)  # #17365d
PDF_CHECKBOX_BORDER_COLOR = (0, 0, 0)
PDF_CHECKBOX_FILL_COLOR = (1, 1, 1)

# Text constants
PDF_CUI_HEADER = 'CUI// CONTROLLED UNCLASSIFIED INFORMATION'
PDF_FOOTER_DISCLAIMER = (
    "The information herein is FOR OFFICIAL USE ONLY (CUI) information which must be protected under "
    "the Freedom of Information Act (5 U.S.C. 552) and/or the Privacy Act of 1974 (5 U.S.C. 552a). "
    "Unauthorized disclosure or misuse of this PERSONAL INFORMATION may result in disciplinary action, "
    "criminal and/or civil penalties."
)
PDF_FOOTER_CUI = "CUI"

# ============================================================================
# PDF TABLE CONFIGURATIONS
# ============================================================================

INITIAL_MEL_TABLE_WIDTHS = [0.22, 0.07, 0.1, 0.08, 0.23, 0.1, 0.1, 0.1]
INITIAL_MEL_INELIGIBLE_TABLE_WIDTHS = [0.22, 0.07, 0.1, 0.08, 0.3, 0.23]
ELIGIBLE_TABLE_WIDTHS = [0.26, 0.08, 0.1, 0.1, 0.26, 0.05, 0.05, 0.05, 0.05]
INELIGIBLE_TABLE_WIDTHS = [0.25, 0.08, 0.1, 0.1, 0.25, 0.2]

# PDF Table Headers
ELIGIBLE_HEADER_ROW = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'NRN', 'P', 'MP', 'PN']
INELIGIBLE_HEADER_ROW = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'REASON NOT ELIGIBLE']
INITIAL_MEL_HEADER_ROW = ['FULL NAME', 'GRADE', 'DAS', 'DAFSC', 'UNIT', 'DOR', 'TAFMSD', 'PASCODE']
INITIAL_MEL_INELIGIBLE_HEADER_ROW = ['FULL NAME', 'GRADE', 'PASCODE', 'DAFSC', 'UNIT', 'REASON']

# Table styling constants
PDF_TABLE_ROW_HEIGHT = 30
PDF_TABLE_HEADER_PADDING = 4
PDF_TABLE_BORDER_WIDTH = 0.5

# Checkbox constants for Final MEL
PDF_CHECKBOX_SIZE = 11
PDF_CHECKBOX_START_X_PERCENT = 0.79  # Percentage of page width
PDF_CHECKBOX_START_Y_PERCENT = 0.276  # Percentage of page height
PDF_CHECKBOX_ROW_HEIGHT_PERCENT = 0.0295  # Percentage of page height
PDF_CHECKBOX_COL_WIDTH_PERCENT = 0.045  # Percentage of page width
PDF_CHECKBOX_MAX_ROWS_PER_PAGE = 20
