from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class QualificationStatus(str, Enum):
    NEW = "new"
    RESEARCHING = "researching"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    OUTREACH_SENT = "outreach_sent"
    MEETING_BOOKED = "meeting_booked"
    SQL = "sql"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class FundingInfo(BaseModel):
    total_raised: Optional[str] = None
    last_round: Optional[str] = None
    last_round_date: Optional[str] = None
    investors: list[str] = Field(default_factory=list)


class HiringSignal(BaseModel):
    role: str
    count: int = 1
    relevance: str = ""


class Company(BaseModel):
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    employee_count: Optional[int] = None
    revenue: Optional[str] = None
    description: Optional[str] = None
    tech_stack: list[str] = Field(default_factory=list)
    erp_system: Optional[str] = None
    crm_system: Optional[str] = None
    cloud_provider: Optional[str] = None
    recent_news: list[str] = Field(default_factory=list)
    funding_info: Optional[FundingInfo] = None
    hiring_signals: list[HiringSignal] = Field(default_factory=list)
    linkedin_url: Optional[str] = None
    apollo_id: Optional[str] = None


class Contact(BaseModel):
    first_name: str
    last_name: str
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    company: Optional[str] = None
    seniority: Optional[str] = None
    is_decision_maker: bool = False
    authority_score: int = Field(default=0, ge=0, le=10)
    apollo_id: Optional[str] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class LeadScore(BaseModel):
    company_fit: int = Field(default=0, ge=0, le=20)
    buying_intent: int = Field(default=0, ge=0, le=20)
    technology_need: int = Field(default=0, ge=0, le=15)
    growth: int = Field(default=0, ge=0, le=10)
    funding: int = Field(default=0, ge=0, le=10)
    urgency: int = Field(default=0, ge=0, le=10)
    decision_maker_access: int = Field(default=0, ge=0, le=10)
    response_probability: int = Field(default=0, ge=0, le=5)

    @property
    def total(self) -> int:
        return (
            self.company_fit + self.buying_intent + self.technology_need
            + self.growth + self.funding + self.urgency
            + self.decision_maker_access + self.response_probability
        )

    @property
    def grade(self) -> str:
        t = self.total
        if t >= 80:
            return "A"
        if t >= 65:
            return "B"
        if t >= 50:
            return "C"
        if t >= 35:
            return "D"
        return "F"


class Lead(BaseModel):
    id: Optional[str] = None
    company: Company
    contacts: list[Contact] = Field(default_factory=list)
    score: Optional[LeadScore] = None
    status: QualificationStatus = QualificationStatus.NEW
    pain_points: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    recommended_services: list[str] = Field(default_factory=list)
    estimated_deal_value: Optional[str] = None
    notes: str = ""
    next_action: Optional[str] = None
    next_action_date: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def primary_contact(self) -> Optional[Contact]:
        dms = [c for c in self.contacts if c.is_decision_maker]
        if dms:
            return max(dms, key=lambda c: c.authority_score)
        return self.contacts[0] if self.contacts else None
