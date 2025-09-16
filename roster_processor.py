# In roster_processor.py

import pandas as pd
from accounting_date_check import accounting_date_check
from board_filter import board_filter
from session_manager import update_session, get_session
from constants import (
    REQUIRED_COLUMNS, OPTIONAL_COLUMNS, PDF_COLUMNS,
    GRADE_MAP, PROMOTIONAL_MAP, small_unit_threshold, max_unit_length,
    OFFICER_RANKS, ENLISTED_RANKS
)

from datetime import datetime
from date_parsing import parse_date

def format_date_for_display(date_value):
    """Format date for display in PDFs as DD-MMM-YYYY"""
    if pd.isna(date_value) or date_value is None:
        return None

    if isinstance(date_value, str):
        parsed_date = parse_date(date_value)
        if parsed_date:
            return parsed_date.strftime("%d-%b-%Y").upper()
        return date_value

    if isinstance(date_value, (datetime, pd.Timestamp)):
        return date_value.strftime("%d-%b-%Y").upper()

    return str(date_value)

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

    all_roster_columns = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

    missing_columns = [col for col in all_roster_columns if col not in roster_df.columns]
    if missing_columns:
        error_log.append(f"Missing required columns: {', '.join(missing_columns)}")
        update_session(session_id, error_log=error_log)
        return

    filtered_roster_df = roster_df[all_roster_columns].copy()

    # Parse all date columns in the DataFrame ONCE, before processing
    date_columns = ['DOR', 'UIF_DISPOSITION_DATE', 'TAFMSD', 'DATE_ARRIVED_STATION']
    for col in date_columns:
        if col in filtered_roster_df.columns:
            filtered_roster_df[col] = filtered_roster_df[col].apply(
                lambda x: parse_date(x, error_log, None)
            )

    # Processing loop - now working with properly parsed datetime objects
    for index, row in filtered_roster_df.iterrows():

        # Check for officer ranks
        if row['GRADE'] in OFFICER_RANKS:
            error_log.append(f"Officer {row['FULL_NAME']} ({row['GRADE']}) excluded from enlisted promotion processing")
            continue

        if row['GRADE'] not in ENLISTED_RANKS:
            error_log.append(f"Unknown or unsupported rank: {row['GRADE']} for {row['FULL_NAME']}")
            continue

        # Check projected grades
        if row['GRADE_PERM_PROJ'] == cycle:
            ineligible_service_members.append(index)
            reason_for_ineligible_map[index] = f'Projected for {cycle}.'
            continue
        elif row['GRADE_PERM_PROJ'] == PROMOTIONAL_MAP.get(cycle):
            continue

        # Early filtering - only process personnel eligible for this promotion cycle
        if not (row['GRADE'] == cycle or (row['GRADE'] == 'A1C' and cycle == 'SRA')):
            continue

        # Check for missing required data
        missing_required = False
        for column in REQUIRED_COLUMNS:
            if column in row and pd.isna(row[column]):
                error_log.append(f"Missing required data at row {index}, column {column}")
                missing_required = True
                break

        if missing_required:
            ineligible_service_members.append(index)
            reason_for_ineligible_map[index] = 'Missing required data'
            continue

        valid_member = accounting_date_check(row['DATE_ARRIVED_STATION'], cycle, year)
        if not valid_member:
            continue

        # Track PASCODEs
        if row['ASSIGNED_PAS'] not in pascodes:
            pascodes.append(row['ASSIGNED_PAS'])
            pascodeUnitMap[row['ASSIGNED_PAS']] = row['ASSIGNED_PAS_CLEARTEXT']


        # Board filter check
        member_status = board_filter(row['GRADE'], year, row['DOR'], row['UIF_CODE'],
                                     row['UIF_DISPOSITION_DATE'], row['TAFMSD'], row['REENL_ELIG_STATUS'],
                                     row['PAFSC'], row['2AFSC'], row['3AFSC'], row['4AFSC'])

        if member_status is None:
            continue
        elif member_status is True:
            eligible_service_members.append(index)
            if row['ASSIGNED_PAS'] in unit_total_map:
                unit_total_map[row['ASSIGNED_PAS']] += 1
            else:
                unit_total_map[row['ASSIGNED_PAS']] = 1
        elif member_status[0] is True and member_status[1] == 'btz':
            eligible_btz_service_members.append(index)
        elif member_status[0] is False:
            ineligible_service_members.append(index)
            reason_for_ineligible_map[index] = member_status[1]

    pascodes = sorted(pascodes)
    update_session(session_id, pascodes=pascodes)

    # Create PDF DataFrames with parsed datetime objects
    pdf_roster = filtered_roster_df[PDF_COLUMNS].copy()

    eligible_df = pdf_roster.loc[eligible_service_members].copy() if eligible_service_members else pd.DataFrame()
    ineligible_df = pdf_roster.loc[ineligible_service_members].copy() if ineligible_service_members else pd.DataFrame()
    btz_df = pdf_roster.loc[eligible_btz_service_members].copy() if eligible_btz_service_members else pd.DataFrame()

    if not ineligible_df.empty:
        ineligible_df['REASON'] = ineligible_df.index.map(reason_for_ineligible_map)

    # NOW format dates for display - only when preparing final output
    def format_df_for_session(df):
        if df.empty:
            return df
        df_copy = df.copy()

        # Format date columns for display ONLY
        date_columns = ['DOR', 'TAFMSD', 'DATE_ARRIVED_STATION']
        for col in date_columns:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].apply(format_date_for_display)

        # Format text columns
        if 'ASSIGNED_PAS_CLEARTEXT' in df_copy.columns:
            df_copy['ASSIGNED_PAS_CLEARTEXT'] = df_copy['ASSIGNED_PAS_CLEARTEXT'].str[:max_unit_length]
        if 'FULL_NAME' in df_copy.columns:
            df_copy['FULL_NAME'] = df_copy['FULL_NAME'].str[:max_unit_length]
        return df_copy

    # Apply formatting only for final output
    eligible_df = format_df_for_session(eligible_df)
    ineligible_df = format_df_for_session(ineligible_df)
    btz_df = format_df_for_session(btz_df)

    for pascode in unit_total_map:
        if cycle == 'MSG' or cycle == 'SMS':
            small_unit_pascodes.append(pascode)
        elif unit_total_map[pascode] <= small_unit_threshold:
            small_unit_pascodes.append(pascode)

    if not eligible_df.empty:
        small_unit_eligible_service_members = eligible_df[eligible_df['ASSIGNED_PAS'].isin(small_unit_pascodes)].index
        small_unit_df = eligible_df.loc[small_unit_eligible_service_members].copy()
    else:
        small_unit_df = pd.DataFrame()

    # Update session with results
    update_session(session_id, eligible_df=eligible_df)
    update_session(session_id, ineligible_df=ineligible_df)
    update_session(session_id, btz_df=btz_df)
    update_session(session_id, small_unit_df=small_unit_df)

    if pascodeUnitMap:
        update_session(session_id, pascode_unit_map=pascodeUnitMap)

    if error_log:
        update_session(session_id, error_log=error_log)

    return
