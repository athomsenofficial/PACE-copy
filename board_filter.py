from datetime import datetime
from dateutil.relativedelta import relativedelta

#Static closeout date = annual report due date
SCODs = {
    'AB': f'31-MAR',
    'AMN': f'31-MAR',
    'A1C': f'31-MAR',
    'SRA': f'31-MAR',
    'SSG': f'31-JAN',
    'TSG': f'30-NOV',
    'MSG': f'30-SEP',
    'SMS': f'31-JUL'
}

#Time in grade = how long you've been in a rank
TIG = {
    'AB': f'01-AUG',
    'AMN': f'01-AUG',
    'A1C': f'01-AUG',
    'SRA': f'01-AUG',
    'SSG': f'01-JUL',
    'TSG': f'01-MAY',
    'MSG': f'01-MAR',
    'SMS': f'01-DEC'
}

tig_months_required = {
    'AB': 6,
    'AMN': 6,
    'A1C': 6,
    'SRA': 6,
    'SSG': 23,
    'TSG': 24,
    'MSG': 20,
    'SMS': 21
}

#Total active federal military service date = time in military (years)
TAFMSD = {
    'AB': 3,
    'AMN': 3,
    'A1C': 3,
    'SRA': 3,
    'SSG': 5,
    'TSG': 8,
    'MSG': 11,
    'SMS': 14
}

#manditory date of separation = the day you have to exit the military
mdos = {
    'AB': f'01-SEP',
    'AMN': f'01-SEP',
    'A1C': f'01-SEP',
    'SRA': f'01-SEP',
    'SSG': f'01-AUG',
    'TSG': f'01-AUG',
    'MSG': f'01-APR',
    'SMS': f'01-JAN'
}

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
    "4J": "AF Weight Management Program.",
    "4K": "Medically disqualified",
    "4L": "Separated, Commissioning program.",
    "4M": "Breach of enlistment.",
    "4N": "Convicted, Civil Court."
}

exception_hyt_start_date = datetime(2023, 12, 8)
exception_hyt_end_date = datetime(2026, 9,30)

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
    cutoff_date = datetime.strptime(f'01-Feb-{year}', '%d-%b-%Y' )
    if isinstance(date_of_rank, str):
        btz_date_of_rank = datetime.strptime(date_of_rank, '%d-%b-%Y') + relativedelta(months=22)
    else:
        btz_date_of_rank = date_of_rank + relativedelta(months=22)
    scod_date = datetime.strptime(f'{SCODs.get('SRA')}-{year}', '%d-%b-%Y')
    if btz_date_of_rank <= cutoff_date:
        return True
    if cutoff_date < btz_date_of_rank <= scod_date:
        return True
    return False

def check_a1c_eligbility(date_of_rank, year):
    cutoff_date = datetime.strptime(f'01-Feb-{year}', '%d-%b-%Y')
    scod_date = datetime.strptime(f'{SCODs.get('SRA')}-{year}', '%d-%b-%Y')
    if isinstance(date_of_rank, str):
        standard_a1c_date_of_rank = datetime.strptime(date_of_rank, '%d-%b-%Y') + relativedelta(months=28)
    else:
        standard_a1c_date_of_rank = date_of_rank + relativedelta(months=28)
    if standard_a1c_date_of_rank <= cutoff_date:
        return True
    if cutoff_date < standard_a1c_date_of_rank <= scod_date:
        return False
    return None

def three_year_tafmsd_check(scod_as_datetime, tafmsd):
    if isinstance(tafmsd, str):
        tafmsd = datetime.strptime(tafmsd, "%d-%b-%Y")
    adjusted_tafmsd = tafmsd + relativedelta(months=36)
    if adjusted_tafmsd > scod_as_datetime:
        return False


def board_filter(grade, year, date_of_rank, uif_code, uif_disposition_date, tafmsd, re_status, cafsc, two_afsc, three_afsc, four_afsc):
    try:
        if isinstance(date_of_rank, str):
            date_of_rank = datetime.strptime(date_of_rank, "%d-%b-%Y")
        if isinstance(uif_disposition_date, str):
            uif_disposition_date = datetime.strptime(uif_disposition_date, "%d-%b-%Y")
        if isinstance(tafmsd, str):
            tafmsd = datetime.strptime(tafmsd, "%d-%b-%Y")

        scod = f'{SCODs.get(grade)}-{year}'
        scod_as_datetime = datetime.strptime(scod, "%d-%b-%Y")
        tig_selection_month = f'{TIG.get(grade)}-{year}'
        formatted_tig_selection_month = datetime.strptime(tig_selection_month, "%d-%b-%Y")
        tig_eligibility_month = formatted_tig_selection_month - relativedelta(months=tig_months_required.get(grade))
        tafmsd_required_date = formatted_tig_selection_month - relativedelta(years=TAFMSD.get(grade)-1)
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
        if grade == 'A1C' or grade == 'AMN' or grade == 'AB':
            if three_year_tafmsd_check(scod_as_datetime, tafmsd):
                return False, 'Over 36 months TIS.'
        if date_of_rank <= tig_eligibility_month:
            return False, f'TIG: < {tig_months_required.get(grade)} months'
        if tafmsd > tafmsd_required_date:
            return False, f'TIS < {TAFMSD.get(grade)} years'
        if exception_hyt_start_date < hyt_date < exception_hyt_end_date:
            hyt_date += relativedelta(years=2)
        if hyt_date < mdos:
            return False, 'Higher tenure.'
        if uif_code > 1 and uif_disposition_date < scod_as_datetime:
            return False, f'UIF code: {uif_code}'
        if re_status in re_codes.keys():
            return False, f'{re_status}: {re_codes.get(re_status)}'
        if grade != 'SMS' or 'MSG':
            if cafsc_check(grade, cafsc, two_afsc, three_afsc, four_afsc) is False:
                return False, 'Insufficient CAFSC skill level.'
        if btz_check is not None and btz_check == True:
            return True, 'btz'
        return True
    except Exception as e:
        print(f"error reading file: {e}")
