from io import BytesIO
import os
import json
import uuid
import redis
import pandas as pd
from dotenv import load_dotenv
import base64
from constants import session_ttl
from datetime import datetime

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL, decode_responses=True)


def create_session(processed_df: pd.DataFrame, pdf_df: pd.DataFrame):
    session_id = str(uuid.uuid4())

    def convert_datetime_columns(df):
        """Convert all datetime columns to strings before creating records"""
        df_copy = df.copy()
        for col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d').fillna('')
            else:
                # Check for datetime objects in object columns
                if df_copy[col].dtype == 'object':
                    df_copy[col] = df_copy[col].apply(
                        lambda x: x.isoformat() if isinstance(x, (datetime, pd.Timestamp)) else x
                    )
        return df_copy

    # Convert datetime columns first
    processed_clean = convert_datetime_columns(processed_df)
    pdf_clean = convert_datetime_columns(pdf_df)

    def simple_sanitize(records):
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        return records

    session_data = {
        "dataframe": simple_sanitize(processed_clean.to_dict(orient="records")),
        "pdf_dataframe": simple_sanitize(pdf_clean.to_dict(orient="records")),
    }

    r.set(session_id, json.dumps(session_data), ex=session_ttl)
    return session_id

def get_session(session_id):
    raw = r.get(session_id)
    if not raw:
        return None
    return json.loads(raw)


def update_session(session_id, **kwargs):
    session = r.get(session_id)
    if not session:
        return None

    session = json.loads(session)

    def comprehensive_sanitize(obj):
        """Recursively sanitize any datetime objects in nested structures"""
        if isinstance(obj, dict):
            return {k: comprehensive_sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [comprehensive_sanitize(item) for item in obj]
        elif pd.isna(obj):
            return None
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        elif hasattr(obj, 'isoformat'):  # Catch any other datetime-like objects
            try:
                return obj.isoformat()
            except:
                return str(obj)
        else:
            return obj

    for key, value in kwargs.items():
        if isinstance(value, pd.DataFrame):
            # Convert DataFrame to records and sanitize
            records = value.to_dict(orient="records")
            session[key] = comprehensive_sanitize(records)
        else:
            session[key] = comprehensive_sanitize(value)

    r.set(session_id, json.dumps(session), ex=session_ttl)
    return session


def delete_session(session_id):
    r.delete(session_id)


def store_pdf_in_redis(session_id: str, pdf_buffer: BytesIO):
    encoded = base64.b64encode(pdf_buffer.getvalue()).decode("utf-8")
    r.set(f"{session_id}_pdf", encoded, ex=session_ttl)


def get_pdf_from_redis(session_id: str) -> BytesIO | None:
    encoded = r.get(f"{session_id}_pdf")
    if not encoded:
        return None
    pdf_bytes = base64.b64decode(encoded)
    return BytesIO(pdf_bytes)