from __future__ import annotations
from typing import Optional

from agents.base import BaseAgent
from config.settings import COMPANY_NAME, DECISION_MAKER_TITLES
from integrations import apollo
from models.lead import Company, Contact


SYSTEM_PROMPT = f"""You are a Decision Maker Research Specialist for {COMPANY_NAME}.

Your job is to identify, research, and prioritize key decision makers at target companies who have:
- Authority to approve IT and software investments
- Budget control over technology initiatives
- Strategic responsibility for digital transformation, operations, or engineering

Priority titles: {', '.join(DECISION_MAKER_TITLES[:8])}

Always identify the most approachable and highest-authority decision maker.
Return structured JSON when asked for data.
"""


class DecisionMakerAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT

    def find_decision_makers(self, company: Company) -> list[Contact]:
        apollo_result = apollo.search_people(
            titles=DECISION_MAKER_TITLES,
            countries=[company.country] if company.country else None,
            per_page=10,
        )
        people = apollo_result.get("people", [])
        company_people = [p for p in people if _matches_company(p, company)]

        if company_people:
            return [self._apollo_to_contact(p, company.name) for p in company_people[:5]]

        prompt = f"""Find the likely key decision makers at {company.name} ({company.industry} company, {company.country}, ~{company.employee_count} employees).

Return JSON array of decision makers:
[{{
  "first_name": "First",
  "last_name": "Last",
  "title": "exact title",
  "email": "likely email pattern or null",
  "linkedin_url": "linkedin URL or null",
  "seniority": "c_suite/vp/director/manager",
  "authority_score": 1-10,
  "is_decision_maker": true,
  "why_target": "reason this person is key decision maker"
}}]

Focus on: {', '.join(DECISION_MAKER_TITLES[:6])}"""
        data = self.run_json(prompt)
        if isinstance(data, list):
            return [self._dict_to_contact(d, company.name) for d in data]
        return []

    def prioritize_contacts(self, contacts: list[Contact]) -> list[Contact]:
        if not contacts:
            return []
        return sorted(contacts, key=lambda c: (c.is_decision_maker, c.authority_score), reverse=True)

    def enrich_contact(self, contact: Contact) -> Contact:
        result = apollo.enrich_person(
            email=contact.email,
            linkedin_url=contact.linkedin_url,
            first_name=contact.first_name,
            last_name=contact.last_name,
            domain=None,
        )
        person = result.get("person", {})
        if person:
            if person.get("email"):
                contact.email = person["email"]
            if person.get("linkedin_url"):
                contact.linkedin_url = person["linkedin_url"]
            if person.get("phone_numbers"):
                contact.phone = person["phone_numbers"][0].get("raw_number", "")
        return contact

    def assess_stakeholder_influence(self, contacts: list[Contact], company: Company) -> dict:
        contacts_summary = "\n".join(
            f"- {c.full_name}, {c.title} (authority: {c.authority_score}/10)" for c in contacts
        )
        prompt = f"""Assess the stakeholder influence map for {company.name}.

Identified contacts:
{contacts_summary}

Return JSON:
{{
  "champion": "name of best internal champion to approach first",
  "economic_buyer": "name of likely budget holder",
  "technical_evaluator": "name of technical decision maker",
  "recommended_sequence": ["ordered list of names to approach"],
  "multi_thread_strategy": "brief strategy for multi-threading the account"
}}"""
        return self.run_json(prompt)

    def _apollo_to_contact(self, person: dict, company_name: str) -> Contact:
        title = person.get("title", "")
        return Contact(
            first_name=person.get("first_name", ""),
            last_name=person.get("last_name", ""),
            title=title,
            email=person.get("email", ""),
            linkedin_url=person.get("linkedin_url", ""),
            company=company_name,
            seniority=person.get("seniority", ""),
            is_decision_maker=_is_decision_maker(title),
            authority_score=apollo.authority_score_from_title(title),
            apollo_id=person.get("id", ""),
        )

    def _dict_to_contact(self, data: dict, company_name: str) -> Contact:
        title = data.get("title", "")
        return Contact(
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            title=title,
            email=data.get("email"),
            linkedin_url=data.get("linkedin_url"),
            company=company_name,
            seniority=data.get("seniority", ""),
            is_decision_maker=data.get("is_decision_maker", _is_decision_maker(title)),
            authority_score=data.get("authority_score", apollo.authority_score_from_title(title)),
        )


def _is_decision_maker(title: str) -> bool:
    dm_keywords = ["ceo", "cto", "cio", "founder", "president", "director",
                   "vp", "vice president", "head of", "chief"]
    title_lower = title.lower()
    return any(kw in title_lower for kw in dm_keywords)


def _matches_company(person: dict, company: Company) -> bool:
    org = person.get("organization", {}) or {}
    name = org.get("name", "").lower()
    return company.name.lower() in name or (company.domain and company.domain.lower() in name)
