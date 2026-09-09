from pydantic import BaseModel
from datetime import datetime

class TrendBase(BaseModel):
    title: str
    query: str
    source: str
    score: float
    category: str

class TrendOut(TrendBase):
    id: str
    analyzed_at: datetime

    class Config:
        from_attributes = True
