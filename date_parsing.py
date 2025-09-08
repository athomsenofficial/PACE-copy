import pandas as pd
from datetime import datetime


def parse_date(value, error_log=None, full_name=None):
    if pd.isna(value) or value is None or value == '':
        return None

    original_value = value
    original_type = type(value)

    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.to_datetime(value).to_pydatetime()

    # Handle Excel serial dates (numbers)
    if isinstance(value, (int, float)):
        try:
            # Excel serial dates start from 1900-01-01
            if 1 <= value <= 2958465:
                return pd.to_datetime(value, unit="D", origin="1899-12-30").to_pydatetime()
        except Exception:
            pass

    # Use pandas to_datetime with inference as the primary method
    if isinstance(value, str):
        try:
            result = pd.to_datetime(value.strip())
            if pd.notna(result):
                return result.to_pydatetime()
        except Exception:
            pass

    if error_log and full_name:
        error_log.append(f"Date parsing failed for {full_name}: '{original_value}' (type: {original_type})")

    return None