"""Structured output for the counterparty risk memo."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    PROCEED = "PROCEED"
    ESCALATE = "ESCALATE"
    DECLINE = "DECLINE"


class Severity(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    CONCERN = "CONCERN"
    BLOCKER = "BLOCKER"


class Evidence(BaseModel):
    """One piece of evidence supporting the verdict, citing a Specter field."""
    severity: Severity
    field: str = Field(description="Specter field that drove this, e.g. 'highlights', 'operating_status'")
    finding: str = Field(description="One sentence describing what was found")
    raw_value: Optional[str] = Field(default=None, description="The actual value from Specter for audit")


class CounterpartyMemo(BaseModel):
    """Final structured output handed to the human analyst."""
    entity_name: str
    domain: Optional[str] = None
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(description="2-3 sentence executive summary")
    evidence: List[Evidence]
    requires_human_review: bool = Field(
        description="True if the agent needs a human to look at this."
    )
    review_reason: Optional[str] = Field(
        default=None,
        description="If requires_human_review, why."
    )
"""Structured output for the counterparty risk memo."""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Verdict(str, Enum):
    PROCEED = "PROCEED"
    ESCALATE = "ESCALATE"
    DECLINE = "DECLINE"


class Severity(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    CONCERN = "CONCERN"
    BLOCKER = "BLOCKER"


class Evidence(BaseModel):
    """One piece of evidence supporting the verdict, citing a Specter field."""
    severity: Severity
    field: str = Field(description="Specter field that drove this, e.g. 'highlights', 'operating_status'")
    finding: str = Field(description="One sentence describing what was found")
    raw_value: Optional[str] = Field(default=None, description="The actual value from Specter for audit")


class CounterpartyMemo(BaseModel):
    """Final structured output handed to the human analyst."""
    entity_name: str
    domain: Optional[str] = None
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(description="2-3 sentence executive summary")
    evidence: List[Evidence]
    requires_human_review: bool = Field(
        description="True if the agent needs a human to look at this."
    )
    review_reason: Optional[str] = Field(
        default=None,
        description="If requires_human_review, why."
    )