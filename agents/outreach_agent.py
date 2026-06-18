from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from agents.base import BaseAgent
from config.settings import COMPANY_NAME
from models.lead import Lead, Contact
from models.outreach import OutreachSequence


SYSTEM_PROMPT = f"""You are an Outreach Execution Specialist for {COMPANY_NAME}.

Your job is to manage multi-channel outreach campaigns and handle prospect objections professionally.

Channel priority: LinkedIn > Email > Phone > Referral

Multi-touch sequence: Day 1 (LinkedIn visit + connect + email) → Day 3 (LinkedIn message) → Day 5 (Email) → Day 7 (Call) → Day 10 (Case study) → Day 14 (Final)

Objection handling principles:
- Never be pushy or aggressive
- Lead with empathy and understanding
- Respond with value, not pressure
- Always leave the door open
- Ask one question to re-engage
"""

OBJECTION_RESPONSES = {
    "already_have_vendor": "That makes sense — most companies we work with also had existing vendors when we first connected. We often complement rather than replace, especially in areas like AI or cloud that move fast. Would it be worth a 15-minute call just to see if there's a gap we could fill?",
    "no_budget": "Understood — budgets are tight everywhere right now. Many of our engagements start small (proof of concept, pilot project) and scale once ROI is clear. Would it be premature to at least understand what a phased approach could look like?",
    "not_interested": "Fair enough — I appreciate your honesty. If anything changes on your technology roadmap, I'd love to stay in touch. Would you mind if I reached out in a few months?",
    "send_info": "Happy to send something over — to make it relevant, could I ask: what's the one technology challenge you're most focused on this year? That way I can tailor what I send rather than blasting you with a brochure.",
    "call_later": "Of course — I'll follow up. Is there a specific week that works better, or should I try in a month?",
    "use_sap": "That's great — SAP is powerful. A lot of our clients actually run SAP and bring us in for the surrounding ecosystem: custom integrations, AI layers, data analytics, or mobility. Is there any layer of your SAP implementation that's causing friction?",
    "use_microsoft": "Microsoft's stack is strong. We work alongside Microsoft tools constantly — whether it's Azure, Dynamics, or Power Platform. Often we add value in custom dev, AI integration, or data engineering that Microsoft themselves don't cover. Anything in that space on your radar?",
    "internal_team": "That's a great sign — it means technology is a priority. Most of our best partnerships are with companies that have strong internal teams. We augment them on specialized capabilities — AI agents, cloud-native development, or ERP implementations — that are hard to hire for full-time. Is there anything your team is stretched thin on?",
}


class OutreachAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT

    def build_execution_plan(self, lead: Lead, sequence: OutreachSequence) -> list[dict]:
        contact = lead.primary_contact
        if not contact:
            return []
        base_date = datetime.utcnow()
        plan = [
            {
                "day": 1,
                "date": base_date.strftime("%Y-%m-%d"),
                "actions": [
                    {"channel": "linkedin", "type": "visit", "content": sequence.day1_linkedin_visit},
                    {"channel": "linkedin", "type": "connect", "content": sequence.day1_linkedin_connect.connection_note if sequence.day1_linkedin_connect else ""},
                    {"channel": "email", "type": "send", "subject": sequence.day1_email.subject if sequence.day1_email else "", "content": sequence.day1_email.body if sequence.day1_email else ""},
                ],
            },
            {
                "day": 3,
                "date": (base_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                "actions": [
                    {"channel": "linkedin", "type": "message", "content": sequence.day3_linkedin_message},
                ],
            },
            {
                "day": 5,
                "date": (base_date + timedelta(days=4)).strftime("%Y-%m-%d"),
                "actions": [
                    {"channel": "email", "type": "send", "subject": sequence.day5_email.subject if sequence.day5_email else "", "content": sequence.day5_email.body if sequence.day5_email else ""},
                ],
            },
            {
                "day": 7,
                "date": (base_date + timedelta(days=6)).strftime("%Y-%m-%d"),
                "actions": [
                    {"channel": "phone", "type": "call", "content": sequence.day7_call.opening if sequence.day7_call else ""},
                ],
            },
            {
                "day": 10,
                "date": (base_date + timedelta(days=9)).strftime("%Y-%m-%d"),
                "actions": [
                    {"channel": "email", "type": "send", "subject": sequence.day10_case_study_email.subject if sequence.day10_case_study_email else "", "content": sequence.day10_case_study_email.body if sequence.day10_case_study_email else ""},
                ],
            },
            {
                "day": 14,
                "date": (base_date + timedelta(days=13)).strftime("%Y-%m-%d"),
                "actions": [
                    {"channel": "email", "type": "send", "subject": sequence.day14_final_email.subject if sequence.day14_final_email else "", "content": sequence.day14_final_email.body if sequence.day14_final_email else ""},
                ],
            },
        ]
        return plan

    def handle_objection(self, objection_type: str, context: dict) -> str:
        canned = OBJECTION_RESPONSES.get(objection_type)
        if canned:
            return canned
        prompt = f"""Handle this sales objection professionally and empathetically.

Objection: {objection_type}
Context: {context}
Sender: SDR at {COMPANY_NAME}

Respond in 2-4 sentences. Be genuine, value-focused, no pressure. End with a soft question.
Return just the response text."""
        return self.run(prompt)

    def determine_best_channel(self, contact: Contact) -> str:
        if contact.linkedin_url:
            return "linkedin"
        if contact.email:
            return "email"
        if contact.phone:
            return "phone"
        return "email"

    def generate_next_step(self, lead: Lead, last_interaction: dict) -> dict:
        prompt = f"""Based on this sales interaction history, recommend the next outreach step.

Company: {lead.company.name}
Contact: {lead.primary_contact.full_name if lead.primary_contact else 'Unknown'} ({lead.primary_contact.title if lead.primary_contact else ''})
Lead Status: {lead.status.value}
Last Interaction: {last_interaction}
Days in sequence: {last_interaction.get('days_since_start', 0)}

Return JSON:
{{
  "action": "specific next action",
  "channel": "linkedin/email/phone",
  "timing": "when to do it",
  "message_angle": "new angle or approach to take",
  "goal": "what outcome we're aiming for"
}}"""
        return self.run_json(prompt)
