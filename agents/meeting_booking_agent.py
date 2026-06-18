from __future__ import annotations
from typing import Optional

from agents.base import BaseAgent
from config.settings import COMPANY_NAME, COMPANY_SERVICES
from models.lead import Lead, Contact


SYSTEM_PROMPT = f"""You are a Meeting Booking Specialist for {COMPANY_NAME}.

You only book meetings when ALL qualification gates are cleared:
✅ Business need is identified and articulated
✅ Decision maker is engaged (not just an influencer)
✅ Timeline has been discussed (they have a sense of when)
✅ Interest is confirmed (they asked a question or said yes)
✅ Meeting objective is defined (not just "let's chat")

When booking, always:
- Confirm exact date, time, and timezone
- Agree on platform (Zoom/Teams/Google Meet)
- Define agenda upfront
- Identify all participants (their side + ours)
- Send a calendar invite with preparation materials

Prepare a detailed meeting brief for the account executive before every meeting.
"""


class MeetingBookingAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT

    def qualify_for_meeting(
        self,
        lead: Lead,
        conversation_history: list[dict],
    ) -> dict:
        history_text = "\n".join(
            f"[{m.get('role', 'unknown')}]: {m.get('content', '')}"
            for m in conversation_history[-10:]
        )
        prompt = f"""Assess whether this prospect is ready to book a meeting.

Company: {lead.company.name}
Contact: {lead.primary_contact.full_name if lead.primary_contact else 'Unknown'} ({lead.primary_contact.title if lead.primary_contact else ''})
Lead Score: {lead.score.total if lead.score else 'N/A'}/100
Pain Points: {'; '.join(lead.pain_points[:3])}

Conversation History:
{history_text}

Qualification Gates:
1. Business need identified?
2. Decision maker engaged?
3. Timeline discussed?
4. Interest confirmed?
5. Meeting objective clear?

Return JSON:
{{
  "ready_to_book": true/false,
  "gates_passed": {{"need": true/false, "authority": true/false, "timeline": true/false, "interest": true/false, "objective": true/false}},
  "blocking_reason": "if not ready, what's missing",
  "recommended_action": "what to do next",
  "meeting_objective": "proposed meeting objective if ready"
}}"""
        return self.run_json(prompt)

    def prepare_meeting_brief(
        self,
        lead: Lead,
        contact: Contact,
        meeting_time: str,
        platform: str = "Zoom",
    ) -> dict:
        services = ", ".join(lead.recommended_services[:4]) if lead.recommended_services else ", ".join(COMPANY_SERVICES[:4])
        prompt = f"""Prepare a comprehensive meeting brief for the account executive.

Meeting: {meeting_time} via {platform}
Prospect: {contact.full_name}, {contact.title} at {lead.company.name}
Lead Score: {lead.score.total if lead.score else 'N/A'}/100 (Grade {lead.score.grade if lead.score else 'N/A'})

Company Profile:
- Industry: {lead.company.industry}
- Country: {lead.company.country}
- Employees: {lead.company.employee_count}
- Revenue: {lead.company.revenue}
- Tech Stack: {', '.join(lead.company.tech_stack[:8])}
- ERP: {lead.company.erp_system}
- Cloud: {lead.company.cloud_provider}

Pain Points: {'; '.join(lead.pain_points)}
Opportunities: {'; '.join(lead.opportunities[:3])}
Recommended Services: {services}
Buying Signals: {'; '.join(lead.buying_signals[:3])}

Return JSON:
{{
  "executive_summary": "3-sentence account summary for the AE",
  "meeting_objective": "clear objective for this meeting",
  "agenda": ["5-point meeting agenda"],
  "key_questions_to_ask": ["5 discovery questions"],
  "pain_points_to_address": ["top 3 pain points"],
  "services_to_present": ["2-3 most relevant services with brief pitch"],
  "competitor_awareness": ["likely competitors or status quo to be aware of"],
  "deal_value_estimate": "estimated deal range",
  "preparation_checklist": ["what the AE should prepare"],
  "red_flags": ["anything to watch out for"],
  "ideal_outcome": "what a successful meeting looks like"
}}"""
        return self.run_json(prompt)

    def generate_meeting_confirmation_email(
        self,
        lead: Lead,
        contact: Contact,
        meeting_time: str,
        platform: str,
        agenda: list[str],
        ae_name: str = "[Account Executive Name]",
    ) -> str:
        agenda_text = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(agenda))
        prompt = f"""Write a professional meeting confirmation email.

To: {contact.full_name} ({contact.title}, {lead.company.name})
Meeting: {meeting_time} via {platform}
AE Name: {ae_name}
From: {COMPANY_NAME}

Agenda:
{agenda_text}

The email should:
- Confirm all meeting details
- Share the agenda
- Express genuine enthusiasm
- Include a prep ask (1-2 things they could think about beforehand)
- Be professional but warm, under 150 words

Return just the email text (subject line first, then body)."""
        return self.run(prompt)

    def generate_no_show_followup(self, lead: Lead, contact: Contact, missed_time: str) -> str:
        prompt = f"""Write a brief, gracious no-show follow-up email.

{contact.first_name} from {lead.company.name} missed a meeting scheduled for {missed_time}.

The email should be:
- Not passive-aggressive
- Give them an easy out / reschedule option
- Under 80 words
- Empathetic (they're busy)

Return just the email text."""
        return self.run(prompt)
