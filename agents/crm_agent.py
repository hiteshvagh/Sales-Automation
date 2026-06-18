from __future__ import annotations
from typing import Optional

from agents.base import BaseAgent
from config.settings import COMPANY_NAME
from db import crm as db
from models.lead import Lead, QualificationStatus
from models.outreach import OutreachSequence


SYSTEM_PROMPT = f"""You are a CRM Management Specialist for {COMPANY_NAME}.

Your job is to keep the sales pipeline accurate, up-to-date, and actionable.

You maintain:
- Lead records with full context
- Interaction logs (every touch point)
- Pipeline stage accuracy
- Follow-up scheduling
- Deal value tracking

Always ensure data quality. Every lead should have:
- A clear status
- A next action
- A next action date
- Documented pain points
"""


class CRMAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT
        db.initialize()

    def save_lead(self, lead: Lead) -> str:
        return db.save_lead(lead)

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        return db.get_lead(lead_id)

    def update_status(
        self,
        lead_id: str,
        status: QualificationStatus,
        notes: str = "",
    ) -> None:
        db.update_lead_status(lead_id, status, notes)

    def log_interaction(
        self,
        lead_id: str,
        channel: str,
        content: str,
        outcome: str = "",
        direction: str = "outbound",
    ) -> None:
        db.log_interaction(lead_id, channel, content, outcome, direction)

    def save_meeting(
        self,
        lead_id: str,
        contact_name: str,
        scheduled_at: str,
        timezone: str = "UTC",
        platform: str = "Zoom",
        agenda: str = "",
    ) -> str:
        meeting_id = db.save_meeting(lead_id, contact_name, scheduled_at, timezone, platform, agenda)
        db.update_lead_status(lead_id, QualificationStatus.MEETING_BOOKED, f"Meeting booked: {scheduled_at}")
        return meeting_id

    def get_follow_up_queue(self) -> list[Lead]:
        return db.get_follow_up_queue()

    def get_all_leads(self, status: Optional[str] = None) -> list[Lead]:
        return db.get_all_leads(status)

    def get_pipeline_summary(self) -> dict:
        return db.get_pipeline_summary()

    def analyze_pipeline_health(self) -> dict:
        summary = self.get_pipeline_summary()
        prompt = f"""Analyze the health of this B2B sales pipeline and provide recommendations.

Pipeline Data:
- Total Leads: {summary['total_leads']}
- Total Meetings: {summary['total_meetings']}
- Total Interactions: {summary['total_interactions']}
- Reply Count: {summary['reply_count']}
- Status Breakdown: {summary['status_breakdown']}

Return JSON:
{{
  "health_score": 0-100,
  "conversion_rates": {{
    "lead_to_meeting": "X%",
    "lead_to_sql": "X%"
  }},
  "bottlenecks": ["list of pipeline bottlenecks"],
  "recommendations": ["list of actionable recommendations"],
  "priority_actions": ["top 3 things to do this week"]
}}"""
        return self.run_json(prompt)

    def suggest_next_action(self, lead: Lead) -> dict:
        prompt = f"""Suggest the best next action for this lead.

Company: {lead.company.name}
Status: {lead.status.value}
Score: {lead.score.total if lead.score else 'N/A'}/100
Pain Points: {'; '.join(lead.pain_points[:2])}
Last Note: {lead.notes[-200:] if lead.notes else 'None'}
Current Next Action: {lead.next_action or 'Not set'}

Return JSON:
{{
  "action": "specific action to take",
  "channel": "linkedin/email/phone",
  "timing": "today/tomorrow/this week/next week",
  "message_angle": "what angle to use",
  "expected_outcome": "what we're trying to achieve"
}}"""
        return self.run_json(prompt)
