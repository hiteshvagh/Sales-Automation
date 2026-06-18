from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class EmailDraft(BaseModel):
    subject: str
    body: str
    personalization_hook: str = ""
    cta: str = ""
    sequence_step: int = 1

    @property
    def word_count(self) -> int:
        return len(self.body.split())

    @field_validator("body")
    @classmethod
    def check_length(cls, v: str) -> str:
        wc = len(v.split())
        if wc > 150:
            raise ValueError(f"Email body is {wc} words — must be under 150 (target <120)")
        return v


class LinkedInMessage(BaseModel):
    connection_note: str
    follow_up_message: str = ""

    @field_validator("connection_note")
    @classmethod
    def check_note_length(cls, v: str) -> str:
        if len(v) > 300:
            raise ValueError("LinkedIn connection note must be under 300 characters")
        return v


class CallScript(BaseModel):
    opening: str
    qualifying_questions: list[str] = Field(default_factory=list)
    value_proposition: str = ""
    objection_handlers: dict[str, str] = Field(default_factory=dict)
    close: str = ""
    voicemail_script: str = ""


class OutreachSequence(BaseModel):
    lead_id: Optional[str] = None
    contact_name: str = ""
    company_name: str = ""
    day1_linkedin_visit: str = ""
    day1_linkedin_connect: Optional[LinkedInMessage] = None
    day1_email: Optional[EmailDraft] = None
    day3_linkedin_message: str = ""
    day5_email: Optional[EmailDraft] = None
    day7_call: Optional[CallScript] = None
    day10_case_study_email: Optional[EmailDraft] = None
    day14_final_email: Optional[EmailDraft] = None
    primary_channel: str = "linkedin"
