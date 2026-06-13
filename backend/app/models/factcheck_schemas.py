from pydantic import BaseModel
from typing import List

class FactCheckRequest(BaseModel):
    statement: str

class FactCheckSource(BaseModel):
    title: str
    url: str
    snippet: str

class FactCheckResponse(BaseModel):
    verdict: str  # "PRAWDA", "FAŁSZ", "SPORNE"
    explanation: str
    confidence: float
    sources: List[FactCheckSource]