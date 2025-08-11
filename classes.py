from typing import Dict
from pydantic import BaseModel

class PasCodeInfo(BaseModel):
    srid: str
    senior_rater_name: str
    senior_rater_rank: str
    senior_rater_title: str

class PasCodeSubmission(BaseModel):
    session_id: str
    pascode_info: Dict[str, PasCodeInfo]