from pydantic import BaseModel, Field
from typing import List, Optional

class SummarizeRequest(BaseModel):
    subject: str = ""
    body: str

class ActionItem(BaseModel):
    text: str
    due: Optional[str] = None

class SummarizeResponse(BaseModel):
    summary: str
    action_items: List[ActionItem] = []
    sentiment: Optional[str] = None

class DraftRequest(BaseModel):
    subject: Optional[str] = None
    body: str
    tone: str = Field(default="polite")

class DraftResponse(BaseModel):
    reply_text: str
