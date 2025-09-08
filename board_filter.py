from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
from date_parsing import parse_date
from constants import (
    SCODS, TIG, TIG_MONTHS_REQUIRED, TAFMSD, MDOS,
    MAIN_HIGHER_TENURE, EXCEPTION_HIGHER_TENURE, PAFSC_MAP,
    RE_CODES, hyt_start_date, hyt_end_date
)


def pafsc_check(grade, pafsc, two_afsc, three_afsc, four_afsc):
    if pafsc and pafsc[0] in ('8', '9'):
        return None

    required_level = PAFSC_MAP.get(grade)
    if not required_level:
        return False

    afscs = [pafsc, two_afsc, three_afsc, four_afsc]

    for afsc in afscs:
        if isinstance(afsc, str) and len(afsc) >= 5:
            skill_level_index = 4 if afsc[0].isalpha() or afsc[0] == '-' else 3

            try:
                if afsc[skill_level_index] >= required_level:
                    return True
            except IndexError:
                continue

    return False


def btz_elgibility_check(date_of_rank, year):
    date_of_rank = parse_date(date_of_rank)
    if not date_of_rank:
        return False
    cutoff_date = datetime.strptime(f"01-Feb-{year}", "%d-%b-%Y")
    btz_date_of_rank = date_of_rank + relativedelta(months=22)
    scod_date = datetime.strptime(f"{SCODS.get('SRA')}-{year}", "%d-%b-%Y")
    if btz_date_of_rank <= cutoff_date:
        return True
    if cutoff_date < btz_date_of_rank <= scod_date:
        return True
    return False


def check_a1c_eligbility(date_of_rank, year):
    date_of_rank = parse_date(date_of_rank)
    if not date_of_rank:
        return False
    cutoff_date = datetime.strptime(f"01-Feb-{year}", "%d-%b-%Y")
    scod_date = datetime.strptime(f"{SCODS.get('SRA')}-{year}", "%d-%b-%Y")
    standard_a1c_date_of_rank = date_of_rank + relativedelta(months=28)
    if standard_a1c_date_of_rank <= cutoff_date:
        return True
    if cutoff_date < standard_a1c_date_of_rank <= scod_date:
        return False
    return None


def three_year_tafmsd_check(scod_as_datetime, tafmsd):
    tafmsd = parse_date(tafmsd)
    if tafmsd is None:
        return False
    adjusted_tafmsd = tafmsd + relativedelta(months=36)
    return adjusted_tafmsd > scod_as_datetime


def board_filter(grade, year, date_of_rank, uif_code, uif_disposition_date, tafmsd, re_status, pafsc, two_afsc,
                 three_afsc, four_afsc):
    try:
        date_of_rank = parse_date(date_of_rank)
        uif_disposition_date = parse_date(uif_disposition_date)
        tafmsd = parse_date(tafmsd)

        # REMOVED the strict None check that was causing all members to be ineligible
        # Only check for required dates that must be present
        if date_of_rank is None or tafmsd is None:
            return False, 'Required date missing or unreadable'

        scod = f'{SCODS.get(grade)}-{year}'
        scod_as_datetime = datetime.strptime(scod, "%d-%b-%Y")
        tig_selection_month = f'{TIG.get(grade)}-{year + 1}'
        formatted_tig_selection_month = datetime.strptime(tig_selection_month, "%d-%b-%Y")
        tig_eligibility_month = formatted_tig_selection_month - relativedelta(months=TIG_MONTHS_REQUIRED.get(grade))
        tafmsd_required_date = formatted_tig_selection_month - relativedelta(years=TAFMSD.get(grade))
        hyt_date = tafmsd + relativedelta(years=MAIN_HIGHER_TENURE.get(grade))
        mdos_month = f'{MDOS.get(grade)}-{year + 1}'
        mdos = datetime.strptime(mdos_month, "%d-%b-%Y")
        btz_check = None

        if grade == 'A1C':
            eligibility_status = check_a1c_eligbility(date_of_rank, year)
            if eligibility_status is None:
                btz_check = btz_elgibility_check(date_of_rank, year)
                if not btz_check:
                    return None
            elif eligibility_status is False:
                return False, 'Failed A1C Check.'
        if grade in ('A1C', 'AMN', 'AB'):
            if three_year_tafmsd_check(scod_as_datetime, tafmsd):
                return False, 'Over 36 months TIS.'
        if date_of_rank is None or date_of_rank > tig_eligibility_month:
            return False, f'TIG: < {TIG_MONTHS_REQUIRED.get(grade)} months'
        if tafmsd > tafmsd_required_date:
            return False, f'TIS < {TAFMSD.get(grade)} years'
        if hyt_start_date < hyt_date < hyt_end_date:
            exception_hyt_years = EXCEPTION_HIGHER_TENURE.get(grade, MAIN_HIGHER_TENURE.get(grade))
            hyt_date = tafmsd + relativedelta(years=exception_hyt_years)
        if hyt_date < mdos:
            return False, 'Higher tenure.'
        try:
            uif_code = int(uif_code)
        except (TypeError, ValueError):
            uif_code = 0
        # Allow uif_disposition_date to be None since it's optional
        if uif_code > 1 and uif_disposition_date and uif_disposition_date < scod_as_datetime:
            return False, f'UIF code: {uif_code}'
        if re_status in RE_CODES.keys():
            return False, f'{re_status}: {RE_CODES.get(re_status)}'
        if grade not in ('SMS', 'MSG'):
            if pafsc_check(grade, pafsc, two_afsc, three_afsc, four_afsc) is False:
                return False, 'Insufficient PAFSC skill level.'
        if btz_check is not None and btz_check is True:
            return True, 'btz'
        return True
    except Exception as e:
        print(f"error reading file: {e}")
        return False, f'Processing error: {str(e)}'