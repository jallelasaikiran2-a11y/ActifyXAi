from pydantic import BaseModel
from typing import Optional

class ActionRequest(BaseModel):
    text: str
    action: str
    context_url: Optional[str] = None

class ActionResponse(BaseModel):
    result: str
    action_taken: str
    model_used: str

class QuickRequest(BaseModel):
    text: str
    action: Optional[str] = "explain"
    context_url: Optional[str] = None
    intent: Optional[str] = None   # detected intent from extension (fix, informational, transform, etc.)

class QuickResponse(BaseModel):
    result: str
    model_used: str
