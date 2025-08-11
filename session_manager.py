from io import BytesIO
import os
import json
import uuid
import redis
import pandas as pd
from dotenv import load_dotenv
import base64

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL, decode_responses=True)
# user_sessions = {}

SESSION_TTL_SECONDS = 1800

def create_session(processed_df: pd.DataFrame, pdf_df: pd.DataFrame):
    session_id = str(uuid.uuid4())

    def sanitize_records(records):
        for record in records:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
                elif isinstance(value, pd.Timestamp):
                    record[key] = value.isoformat()
        return records

    session_data = {
        "dataframe": sanitize_records(processed_df.to_dict(orient="records")),
        "pdf_dataframe": sanitize_records(pdf_df.to_dict(orient="records")),
    }

    r.set(session_id, json.dumps(session_data), ex=SESSION_TTL_SECONDS)
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

    for key, value in kwargs.items():
        if isinstance(value, pd.DataFrame):
            session[key] = value.to_dict(orient="records")
        else:
            session[key] = value

    r.set(session_id, json.dumps(session), ex=SESSION_TTL_SECONDS)
    return session

def delete_session(session_id):
    r.delete(session_id)

def store_pdf_in_redis(session_id: str, pdf_buffer: BytesIO):
    encoded = base64.b64encode(pdf_buffer.getvalue()).decode("utf-8")
    r.set(f"{session_id}_pdf", encoded, ex=SESSION_TTL_SECONDS)

def get_pdf_from_redis(session_id: str) -> BytesIO | None:
    encoded = r.get(f"{session_id}_pdf")
    if not encoded:
        return None
    pdf_bytes = base64.b64decode(encoded)
    return BytesIO(pdf_bytes)