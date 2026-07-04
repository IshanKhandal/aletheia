from pydantic import BaseModel
from typing import Optional, List

# What the user sends when submitting a case
class CaseInput(BaseModel):
    case_text: str
    user_diagnosis: str
    severity_flag: Optional[str] = None  # "serious" or None
    mode: str = "doctor"  # "doctor" or "student"
    manual_specialists: Optional[List[str]] = None  # if user picks manually

# What each agent returns after responding
class AgentResponse(BaseModel):
    agent_name: str
    api_used: str
    response: str
    confidence: float
    round_number: int

# What the Triage Agent returns
class TriageResult(BaseModel):
    severity: str  # "CRITICAL", "URGENT", "ROUTINE"
    reason: str

# What the Selector Agent returns
class SelectorResult(BaseModel):
    selected_specialists: List[str]

# What the Comparison Agent returns
class ComparisonResult(BaseModel):
    user_diagnosis: str
    panel_verdict: str
    agreement: bool
    divergence_points: List[str]
    missed_by_user: List[str]
    feedback: str

# The full debate result
class DebateResult(BaseModel):
    case_id: str
    triage: TriageResult
    selected_specialists: List[str]
    debate_log: List[AgentResponse]
    final_verdict: str
    comparison: ComparisonResult