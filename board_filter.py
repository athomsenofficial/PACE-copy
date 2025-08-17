from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd


# Static closeout date = annual report due date (PECD)
SCODs = {
    'AB': '31-MAR',    # E1 to E2
    'AMN': '31-MAR',   # E2 to E3
    'A1C': '31-MAR',   # E3 to E4
    'SRA': '31-MAR',   # E4 to E5 (BTZ/regular)
    'SSG': '31-JAN',   # E5 to E6
    'TSG': '30-NOV',   # E6 to E7
    'MSG': '30-SEP',   # E7 to E8
    'SMS': '31-JUL'    # E8 to E9
}

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
tig_months_required = {
    'AB': 6,     # 21/6 months per chart
    'AMN': 6,    # 22/6 months per chart
    'A1C': 10,   # 23/6 months per chart (Note: Regular is 28 months, BTZ is different)
    'SRA': 6,    # 24/6 months per chart
    'SSG': 23,   # 23/23 months per chart
    'TSG': 23,   # 24/23 months per chart (varies by cycle, using most common)
    'MSG': 20,   # 20/20 months per chart
    'SMS': 21    # 21/21 months per chart
}

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

# Mandatory date of separation (MDOS column - must be on or after)
# This is the base month for MDOS calculation
mdos = {
    'AB': '01-SEP',    # Per chart MDOS column
    'AMN': '01-SEP',   # Per chart MDOS column
    'A1C': '01-SEP',   # Per chart MDOS column
    'SRA': '01-SEP',   # Per chart MDOS column
    'SSG': '01-AUG',   # Per chart MDOS column
    'TSG': '01-AUG',   # Per chart MDOS column
    'MSG': '01-APR',   # Per chart MDOS column
    'SMS': '01-JAN'    # Per chart MDOS column
}

# Main higher tenure (standard HYT limits, in years)
main_higher_tenure = {
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
exception_higher_tenure = {
    'AB': 8,
    'AMN': 8,
    'A1C': 10,
    'SRA': 12,
    'SSG': 22,
    'TSG': 24,
    'MSG': 26,
    'SMS': 28
}

# CAFSC skill level mapping 5th digit of the AFSC: ex -3F0X1)
cafsc_map = {
    'AB': '3',
    'AMN': '3',
    'A1C': '3',
    'SRA': '5',
    'SSG': '5',
    'TSG': '7',
    'MSG': '7',
    'SMS': '9'
}

#reenlistment codes
re_codes = {
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

exception_hyt_start_date = datetime(2023, 12, 8)
exception_hyt_end_date = datetime(2026, 9,30)

def _parse_date(value):
    """Return ``datetime`` for a variety of Excel or string representations."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, (int, float)):
        # Excel serial dates start at 1899-12-30
        return pd.to_datetime(value, unit="D", origin="1899-12-30").to_pydatetime()
    if isinstance(value, str):
        return datetime.strptime(value, "%d-%b-%Y")
    return None


def cafsc_check(grade, cafsc, two_afsc, three_afsc, four_afsc):
    if cafsc is not None and len(cafsc) >= 6:
        if cafsc[1] == '8' or cafsc[1] == '9':
            return None
        if cafsc[4] >= cafsc_map.get(grade):
            return True
        elif isinstance(two_afsc, str) and two_afsc is not None:
            if len(two_afsc) == 6:
                if two_afsc[4] >= cafsc_map.get(grade):
                    return True
            elif len(two_afsc) == 5:
                if two_afsc[3] >= cafsc_map.get(grade):
                    return True
        elif isinstance(three_afsc, str) and three_afsc is not None:
            if len(three_afsc) == 6:
                if three_afsc[4] >= cafsc_map.get(grade):
                    return True
            elif len(three_afsc) == 5:
                if three_afsc[3] >= cafsc_map.get(grade):
                    return True
        elif isinstance(four_afsc, str) and four_afsc is not None:
            if len(four_afsc) == 6:
                if four_afsc[4] >= cafsc_map.get(grade):
                    return True
            elif len(four_afsc) == 5:
                if four_afsc[3] >= cafsc_map.get(grade):
                    return True
    return False



def btz_elgibility_check(date_of_rank, year):
    date_of_rank = _parse_date(date_of_rank)
    cutoff_date = datetime.strptime(f"01-Feb-{year}", "%d-%b-%Y")
    btz_date_of_rank = date_of_rank + relativedelta(months=22)
    scod_date = datetime.strptime(f"{SCODs.get('SRA')}-{year}", "%d-%b-%Y")
    if btz_date_of_rank <= cutoff_date:
        return True
    if cutoff_date < btz_date_of_rank <= scod_date:
        return True
    return False

def check_a1c_eligbility(date_of_rank, year):
    date_of_rank = _parse_date(date_of_rank)
    cutoff_date = datetime.strptime(f"01-Feb-{year}", "%d-%b-%Y")
    scod_date = datetime.strptime(f"{SCODs.get('SRA')}-{year}", "%d-%b-%Y")
    standard_a1c_date_of_rank = date_of_rank + relativedelta(months=28)
    if standard_a1c_date_of_rank <= cutoff_date:
        return True
    if cutoff_date < standard_a1c_date_of_rank <= scod_date:
        return False
    return None

def three_year_tafmsd_check(scod_as_datetime, tafmsd):
    tafmsd = _parse_date(tafmsd)
    if tafmsd is None:
        return False
    adjusted_tafmsd = tafmsd + relativedelta(months=36)
    return adjusted_tafmsd > scod_as_datetime


def board_filter(grade, year, date_of_rank, uif_code, uif_disposition_date, tafmsd, re_status, cafsc, two_afsc, three_afsc, four_afsc):
    try:
        date_of_rank = _parse_date(date_of_rank)
        uif_disposition_date = _parse_date(uif_disposition_date)
        tafmsd = _parse_date(tafmsd)

        scod = f'{SCODs.get(grade)}-{year}'
        scod_as_datetime = datetime.strptime(scod, "%d-%b-%Y")
        tig_selection_month = f'{TIG.get(grade)}-{year}'
        formatted_tig_selection_month = datetime.strptime(tig_selection_month, "%d-%b-%Y")
        tig_eligibility_month = formatted_tig_selection_month - relativedelta(months=tig_months_required.get(grade))
        tafmsd_required_date = formatted_tig_selection_month - relativedelta(years=TAFMSD.get(grade))
        hyt_date = tafmsd + relativedelta(years=main_higher_tenure.get(grade))
        mdos = formatted_tig_selection_month + relativedelta(months=1)
        btz_check = None

        if grade == 'A1C':
            eligibility_status = check_a1c_eligbility(date_of_rank, year)
            if eligibility_status == None:
                btz_check = btz_elgibility_check(date_of_rank, year)
                if not btz_check:
                    return None
            elif eligibility_status == False:
                return False, 'Failed A1C Check.'
        if grade in ('A1C', 'AMN', 'AB'):
            if three_year_tafmsd_check(scod_as_datetime, tafmsd):
                return False, 'Over 36 months TIS.'
        if date_of_rank is None or date_of_rank > tig_eligibility_month:
            return False, f'TIG: < {tig_months_required.get(grade)} months'
        if tafmsd > tafmsd_required_date:
            return False, f'TIS < {TAFMSD.get(grade)} years'
        if exception_hyt_start_date < hyt_date < exception_hyt_end_date:
            hyt_date += relativedelta(years=2)
        if hyt_date < mdos:
            return False, 'Higher tenure.'
        try:
            uif_code = int(uif_code)
        except (TypeError, ValueError):
            uif_code = 0
        if uif_code > 1 and uif_disposition_date and uif_disposition_date < scod_as_datetime:
            return False, f'UIF code: {uif_code}'
        if re_status in re_codes.keys():
            return False, f'{re_status}: {re_codes.get(re_status)}'
        if grade not in ('SMS', 'MSG'):
            if cafsc_check(grade, cafsc, two_afsc, three_afsc, four_afsc) is False:
                return False, 'Insufficient CAFSC skill level.'
        if btz_check is not None and btz_check == True:
            return True, 'btz'
        return True
    except Exception as e:
        print(f"error reading file: {e}")
