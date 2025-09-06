import pandas as pd
from accounting_date_check import accounting_date_check
from board_filter import board_filter
from session_manager import update_session, get_session
from constants import (
    REQUIRED_COLUMNS, OPTIONAL_COLUMNS, PDF_COLUMNS, BOARDS,
    GRADE_MAP, PROMOTIONAL_MAP, SMALL_UNIT_THRESHOLD, MAX_NAME_LENGTH, MAX_UNIT_LENGTH
)


def roster_processor(roster_df, session_id, cycle, year):
    eligible_service_members = []
    eligible_btz_service_members = []
    ineligible_service_members = []
    small_unit_eligible_service_members = []

    pascodes = []
    small_unit_pascodes = []
    reason_for_ineligible_map = {}
    pascodeUnitMap = {}
    unit_total_map = {}

    error_log = []

    filtered_roster_df = roster_df[REQUIRED_COLUMNS + OPTIONAL_COLUMNS]
    pdf_roster = filtered_roster_df[PDF_COLUMNS]

    for index, row in filtered_roster_df.iterrows():
        for column, value in row.items():
            if pd.isna(value) and column in REQUIRED_COLUMNS:
                error_log.append(rf"error at {index}, {column}")
                break
            if isinstance(value, pd.Timestamp):
                row[column] = value.strftime('%d-%b-%Y').upper()
                continue
        valid_member = accounting_date_check(row['DATE_ARRIVED_STATION'], cycle, year)
        if not valid_member:
            continue
        if row['ASSIGNED_PAS'] not in pascodes:
            pascodes.append(row['ASSIGNED_PAS'])
            pascodeUnitMap[row['ASSIGNED_PAS']] = row['ASSIGNED_PAS_CLEARTEXT']
        if row['GRADE_PERM_PROJ'] == cycle:
            ineligible_service_members.append(index)
            reason_for_ineligible_map[index] = f'Projected for {cycle}.'
            continue
        elif row['GRADE_PERM_PROJ'] == PROMOTIONAL_MAP.get(cycle):
            continue
        if row['GRADE'] == cycle or (row['GRADE'] == 'A1C' and cycle == 'SRA'):
            member_status = board_filter(row['GRADE'], year, row['DOR'], row['UIF_CODE'],
                                         row['UIF_DISPOSITION_DATE'], row['TAFMSD'], row['REENL_ELIG_STATUS'],
                                         row['PAFSC'], row['2AFSC'], row['3AFSC'], row['4AFSC'])
            if member_status is None:
                continue
            elif member_status == True:
                eligible_service_members.append(index)
                if row['ASSIGNED_PAS'] in unit_total_map:
                    unit_total_map[row['ASSIGNED_PAS']] = unit_total_map[row['ASSIGNED_PAS']] + 1
                else:
                    unit_total_map[row['ASSIGNED_PAS']] = 1
            elif member_status[0] == True and member_status[1] == 'btz':
                eligible_btz_service_members.append(index)
            elif member_status[0] == False:
                ineligible_service_members.append(index)
                reason_for_ineligible_map[index] = member_status[1]

    pascodes = sorted(pascodes)

    update_session(session_id, pascodes=pascodes)

    eligible_df = pdf_roster.loc[eligible_service_members]
    for column in eligible_df.columns:
        if column == 'ASSIGNED_PAS_CLEARTEXT':
            eligible_df['ASSIGNED_PAS_CLEARTEXT'] = eligible_df['ASSIGNED_PAS_CLEARTEXT'].str[:MAX_UNIT_LENGTH]
        if column == 'FULL_NAME':
            eligible_df['FULL_NAME'] = eligible_df['FULL_NAME'].str[:MAX_UNIT_LENGTH]
        if pd.api.types.is_datetime64_any_dtype(eligible_df[column].dtype):
            eligible_df[column] = eligible_df[column].dt.strftime('%d-%b-%Y').str.upper()

    ineligible_df = pdf_roster.loc[ineligible_service_members].copy()
    ineligible_df['REASON'] = ineligible_df.index.map(reason_for_ineligible_map)
    for column in ineligible_df.columns:
        if column == 'ASSIGNED_PAS_CLEARTEXT':
            ineligible_df['ASSIGNED_PAS_CLEARTEXT'] = ineligible_df['ASSIGNED_PAS_CLEARTEXT'].str[:MAX_UNIT_LENGTH]
        if column == 'FULL_NAME':
            ineligible_df['FULL_NAME'] = ineligible_df['FULL_NAME'].str[:MAX_UNIT_LENGTH]
        if pd.api.types.is_datetime64_any_dtype(ineligible_df[column].dtype):
            ineligible_df[column] = ineligible_df[column].dt.strftime('%d-%b-%Y').str.upper()

    btz_df = pdf_roster.loc[eligible_btz_service_members]

    for column in btz_df.columns:
        if column == 'ASSIGNED_PAS_CLEARTEXT':
            btz_df['ASSIGNED_PAS_CLEARTEXT'] = btz_df['ASSIGNED_PAS_CLEARTEXT'].str[:MAX_UNIT_LENGTH]
        if column == 'FULL_NAME':
            btz_df['FULL_NAME'] = btz_df['FULL_NAME'].str[:MAX_UNIT_LENGTH]
        if pd.api.types.is_datetime64_any_dtype(btz_df[column].dtype):
            btz_df[column] = btz_df[column].dt.strftime('%d-%b-%Y').str.upper()

    for pascode in unit_total_map:
        if unit_total_map[pascode] < SMALL_UNIT_THRESHOLD:
            small_unit_pascodes.append(pascode)

    for index, row in eligible_df.iterrows():
        if row['ASSIGNED_PAS'] in small_unit_pascodes:
            small_unit_eligible_service_members.append(index)

    small_unit_df = eligible_df.loc[small_unit_eligible_service_members]

    if eligible_df is not None:
        update_session(session_id, eligible_df=eligible_df)

    if ineligible_df is not None:
        update_session(session_id, ineligible_df=ineligible_df)

    if btz_df is not None:
        update_session(session_id, btz_df=btz_df)

    if small_unit_df is not None:
        update_session(session_id, small_unit_df=small_unit_df)

    if pascodeUnitMap is not None:
        update_session(session_id, pascode_unit_map=pascodeUnitMap)

    if error_log.count != 0:
        update_session(session_id, error_log=error_log)

    return