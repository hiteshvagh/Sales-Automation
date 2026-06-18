from __future__ import annotations
from typing import Optional

from agents.base import BaseAgent
from config.settings import COMPANY_NAME, COMPANY_SERVICES
from models.lead import Lead, Contact
from models.outreach import (
    EmailDraft, LinkedInMessage, CallScript, OutreachSequence,
)


SYSTEM_PROMPT = f"""You are a Personalization Specialist for {COMPANY_NAME}, crafting hyper-personalized B2B outreach.

EMAIL RULES (strict):
- Under 120 words (hard limit: 150)
- Structure: Personalized opener → Business observation → Pain point → Value prop → Proof → Single CTA
- Never: "We are the best", generic templates, long paragraphs, buzzwords
- Always: Specific, relevant, human, direct

LINKEDIN MESSAGE RULES:
- Connection note: max 300 characters, personal, no pitch yet
- Follow-up: warm, value-first, conversational

CALL SCRIPT RULES:
- Opening: 15 seconds max, earn the right to continue
- Ask permission before pitching
- Discovery-first approach

PERSONALIZATION SOURCES (use whatever is available):
- Recent funding rounds
- New job postings (signal investment areas)
- Press releases / news
- Technology adoption or migration
- Office expansion or new markets
- Product launches
- Leadership changes
- Awards or recognitions
"""


class PersonalizationAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT

    def generate_outreach(self, lead: Lead, contact: Contact) -> OutreachSequence:
        day1_email = self.generate_email(lead, contact, step=1)
        day1_linkedin = self.generate_linkedin_message(lead, contact)
        day5_email = self.generate_email(lead, contact, step=2)
        day7_call = self.generate_call_script(lead, contact)
        day10_email = self.generate_email(lead, contact, step=3)
        day14_email = self.generate_email(lead, contact, step=4)

        return OutreachSequence(
            lead_id=lead.id,
            contact_name=contact.full_name,
            company_name=lead.company.name,
            day1_linkedin_visit=f"Visit {contact.full_name}'s LinkedIn profile before connecting",
            day1_linkedin_connect=day1_linkedin,
            day1_email=day1_email,
            day3_linkedin_message=day1_linkedin.follow_up_message,
            day5_email=day5_email,
            day7_call=day7_call,
            day10_case_study_email=day10_email,
            day14_final_email=day14_email,
            primary_channel="linkedin" if contact.linkedin_url else "email",
        )

    def generate_email(self, lead: Lead, contact: Contact, step: int = 1) -> EmailDraft:
        step_instructions = {
            1: "First touch. Lead with the most compelling personalization hook. Soft CTA — ask for a 15-minute call.",
            2: "Follow-up to email 1. Reference the previous email. Share a different angle or insight. Same soft CTA.",
            3: "Case study email. Reference a relevant success story or result for a similar company. CTA: share the case study.",
            4: "Final breakup email. Short, low pressure. Leave the door open. No hard sell.",
        }

        personalization_ctx = self._build_personalization_context(lead)
        services = ", ".join(lead.recommended_services[:3]) if lead.recommended_services else COMPANY_SERVICES[0]

        prompt = f"""Write a personalized cold email for step {step} of an outreach sequence.

Sender: SDR at {COMPANY_NAME} (IT Consulting, AI, ERP, Cloud, Digital Transformation)
Recipient: {contact.full_name}, {contact.title} at {lead.company.name}

Personalization Context:
{personalization_ctx}

Pain Points: {'; '.join(lead.pain_points[:2])}
Relevant Services: {services}
Step Instructions: {step_instructions.get(step, step_instructions[1])}

CRITICAL: Email body must be under 120 words. No fluff.

Return JSON:
{{
  "subject": "compelling subject line (no clickbait)",
  "body": "email body under 120 words",
  "personalization_hook": "the specific hook used",
  "cta": "the single call to action"
}}"""
        data = self.run_json(prompt)
        if isinstance(data, dict) and data.get("body"):
            body = data["body"]
            word_count = len(body.split())
            if word_count > 150:
                body = " ".join(body.split()[:140])
            try:
                return EmailDraft(
                    subject=data.get("subject", f"Quick question, {contact.first_name}"),
                    body=body,
                    personalization_hook=data.get("personalization_hook", ""),
                    cta=data.get("cta", ""),
                    sequence_step=step,
                )
            except Exception:
                pass
        return EmailDraft(
            subject=f"Quick question, {contact.first_name}",
            body=f"Hi {contact.first_name},\n\nI noticed {lead.company.name} is growing rapidly. We help {lead.company.industry} companies modernize their technology stack.\n\nWould a 15-minute call make sense?\n\nBest,\n[Your Name]",
            personalization_hook="company growth",
            cta="15-minute call",
            sequence_step=step,
        )

    def generate_linkedin_message(self, lead: Lead, contact: Contact) -> LinkedInMessage:
        personalization_ctx = self._build_personalization_context(lead)
        prompt = f"""Write a LinkedIn outreach for {contact.full_name} ({contact.title} at {lead.company.name}).

Personalization Context:
{personalization_ctx}

Connection Note (max 300 chars, NO pitch, just genuine human connection):
Follow-up Message (after they accept, value-first, conversational, <80 words):

Return JSON:
{{
  "connection_note": "300 char max connection note",
  "follow_up_message": "follow-up message after connection"
}}"""
        data = self.run_json(prompt)
        if isinstance(data, dict) and data.get("connection_note"):
            note = data["connection_note"][:300]
            return LinkedInMessage(
                connection_note=note,
                follow_up_message=data.get("follow_up_message", ""),
            )
        return LinkedInMessage(
            connection_note=f"Hi {contact.first_name}, I came across {lead.company.name} and was impressed by your work. Would love to connect.",
            follow_up_message=f"Thanks for connecting, {contact.first_name}! I work with {lead.company.industry} companies on digital transformation. Happy to share ideas if helpful.",
        )

    def generate_call_script(self, lead: Lead, contact: Contact) -> CallScript:
        personalization_ctx = self._build_personalization_context(lead)
        prompt = f"""Write a cold call script for {contact.full_name} ({contact.title} at {lead.company.name}).

Personalization Context:
{personalization_ctx}

Pain Points: {'; '.join(lead.pain_points[:2])}
Services: {', '.join(lead.recommended_services[:2])}

Return JSON:
{{
  "opening": "15-second opening that earns the right to continue",
  "qualifying_questions": ["3-4 discovery questions"],
  "value_proposition": "30-second value prop if they engage",
  "objection_handlers": {{
    "not_interested": "response",
    "no_budget": "response",
    "already_have_vendor": "response",
    "send_email": "response",
    "call_back_later": "response"
  }},
  "close": "meeting ask close",
  "voicemail_script": "20-second voicemail if no answer"
}}"""
        data = self.run_json(prompt)
        if isinstance(data, dict) and data.get("opening"):
            return CallScript(
                opening=data["opening"],
                qualifying_questions=data.get("qualifying_questions", []),
                value_proposition=data.get("value_proposition", ""),
                objection_handlers=data.get("objection_handlers", {}),
                close=data.get("close", ""),
                voicemail_script=data.get("voicemail_script", ""),
            )
        return CallScript(
            opening=f"Hi {contact.first_name}, this is [Name] from {COMPANY_NAME}. I know this is out of the blue — do you have 30 seconds?",
            qualifying_questions=[
                "What does your current technology modernization roadmap look like?",
                "Are you running any legacy systems you're looking to replace?",
                "How are you currently handling [pain point]?",
            ],
            value_proposition=f"We help {lead.company.industry} companies like yours modernize technology and automate operations.",
            close="Would it make sense to spend 15 minutes to see if there's a fit?",
            voicemail_script=f"Hi {contact.first_name}, this is [Name] from {COMPANY_NAME}. I had a quick idea for {lead.company.name} around [pain point]. I'll follow up by email — [Name], {COMPANY_NAME}.",
        )

    def handle_objection(self, objection: str, context: dict) -> str:
        company = context.get("company", "your company")
        contact = context.get("contact", "")
        prompt = f"""Write a brief, non-pushy response to this sales objection.

Objection: "{objection}"
Company: {company}
Context: {context.get('notes', '')}
Sender: SDR at {COMPANY_NAME}

Response should be:
- Empathetic and understanding
- 2-3 sentences max
- Value-focused, not pressure-based
- End with a soft open-ended question or offer

Return just the response text, no JSON."""
        return self.run(prompt)

    def _build_personalization_context(self, lead: Lead) -> str:
        lines = []
        c = lead.company
        if c.funding_info and c.funding_info.last_round:
            lines.append(f"Recently raised {c.funding_info.last_round} funding")
        if c.recent_news:
            lines.append(f"Recent news: {c.recent_news[0]}")
        if c.hiring_signals:
            roles = ", ".join(h.role for h in c.hiring_signals[:3])
            lines.append(f"Actively hiring: {roles}")
        if lead.buying_signals:
            lines.append(f"Buying signals: {lead.buying_signals[0]}")
        if c.tech_stack:
            lines.append(f"Tech stack includes: {', '.join(c.tech_stack[:5])}")
        if c.erp_system:
            lines.append(f"Running {c.erp_system} ERP")
        if c.employee_count:
            lines.append(f"{c.employee_count} employees, {c.industry} industry, {c.country}")
        return "\n".join(lines) if lines else f"{c.name} is a {c.industry} company in {c.country}"
