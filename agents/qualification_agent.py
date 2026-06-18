from __future__ import annotations
from typing import Optional

from agents.base import BaseAgent
from config.settings import COMPANY_NAME, COMPANY_SERVICES
from models.lead import Company, Contact, Lead, LeadScore, QualificationStatus


SYSTEM_PROMPT = f"""You are a Lead Qualification Specialist for {COMPANY_NAME}.

You evaluate prospects using MEDDICC + BANT + SPICED frameworks:
- MEDDICC: Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion, Competition
- BANT: Budget, Authority, Need, Timeline
- SPICED: Situation, Pain, Impact, Critical Event, Decision

Available services: {', '.join(COMPANY_SERVICES)}

Score leads 0-100 across:
- Company Fit (20 pts): industry, size, revenue, location
- Buying Intent (20 pts): signals, engagement, timing
- Technology Need (15 pts): stack gaps, modernization need
- Growth (10 pts): expansion, hiring, market momentum
- Funding (10 pts): recent funding, ability to invest
- Urgency (10 pts): critical events, deadlines, pain severity
- Decision Maker Access (10 pts): have we found the right person
- Response Probability (5 pts): likelihood of getting a reply

Leads scoring 70+ are SQL-ready. 50-69 need nurturing. Below 50 deprioritize.
"""


class QualificationAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT

    def qualify_lead(
        self,
        company: Company,
        contacts: list[Contact],
        buying_signals: list[str],
    ) -> Lead:
        score = self.score_lead(company, contacts, buying_signals)
        analysis = self._analyze_lead(company, contacts, buying_signals, score)

        status = QualificationStatus.QUALIFIED if score.total >= 50 else QualificationStatus.DISQUALIFIED

        return Lead(
            company=company,
            contacts=contacts,
            score=score,
            status=status,
            pain_points=analysis.get("pain_points", []),
            opportunities=analysis.get("opportunities", []),
            buying_signals=buying_signals,
            recommended_services=analysis.get("recommended_services", []),
            estimated_deal_value=analysis.get("estimated_deal_value", ""),
            notes=analysis.get("qualification_summary", ""),
            next_action=analysis.get("next_action", "Send personalized outreach"),
        )

    def score_lead(
        self,
        company: Company,
        contacts: list[Contact],
        buying_signals: list[str],
    ) -> LeadScore:
        has_dm = any(c.is_decision_maker for c in contacts)
        dm_score = min(10, sum(1 for c in contacts if c.is_decision_maker) * 4) if has_dm else 2

        prompt = f"""Score this B2B lead for {COMPANY_NAME} (IT Consulting, AI, ERP, Cloud, Digital Transformation).

Company: {company.name}
Industry: {company.industry}
Country: {company.country}
Employees: {company.employee_count}
Revenue: {company.revenue}
Tech Stack: {', '.join(company.tech_stack[:10])}
ERP: {company.erp_system}
CRM: {company.crm_system}
Cloud: {company.cloud_provider}
Recent News: {'; '.join(company.recent_news[:3])}
Funding: {company.funding_info.last_round if company.funding_info else 'Unknown'}
Hiring Signals: {', '.join(h.role for h in company.hiring_signals[:5])}
Buying Signals: {'; '.join(buying_signals[:5])}
Decision Makers Found: {len([c for c in contacts if c.is_decision_maker])}

Return JSON with exact integer scores (no floats):
{{
  "company_fit": 0-20,
  "buying_intent": 0-20,
  "technology_need": 0-15,
  "growth": 0-10,
  "funding": 0-10,
  "urgency": 0-10,
  "decision_maker_access": 0-10,
  "response_probability": 0-5,
  "reasoning": {{
    "company_fit": "brief reason",
    "buying_intent": "brief reason",
    "technology_need": "brief reason"
  }}
}}"""
        data = self.run_json(prompt)
        if isinstance(data, dict):
            try:
                return LeadScore(
                    company_fit=min(20, int(data.get("company_fit", 10))),
                    buying_intent=min(20, int(data.get("buying_intent", 10))),
                    technology_need=min(15, int(data.get("technology_need", 8))),
                    growth=min(10, int(data.get("growth", 5))),
                    funding=min(10, int(data.get("funding", 5))),
                    urgency=min(10, int(data.get("urgency", 5))),
                    decision_maker_access=min(10, dm_score),
                    response_probability=min(5, int(data.get("response_probability", 3))),
                )
            except (ValueError, TypeError):
                pass
        return LeadScore(
            company_fit=10, buying_intent=10, technology_need=8,
            growth=5, funding=5, urgency=5,
            decision_maker_access=dm_score, response_probability=3,
        )

    def _analyze_lead(
        self,
        company: Company,
        contacts: list[Contact],
        buying_signals: list[str],
        score: LeadScore,
    ) -> dict:
        contact_summary = ", ".join(f"{c.full_name} ({c.title})" for c in contacts[:3])
        prompt = f"""Analyze this qualified lead for {COMPANY_NAME} sales team.

Company: {company.name} | {company.industry} | {company.country} | {company.employee_count} employees
Lead Score: {score.total}/100 (Grade {score.grade})
Contacts: {contact_summary}
Buying Signals: {'; '.join(buying_signals[:5])}
Tech Stack: {', '.join(company.tech_stack[:8])}
ERP: {company.erp_system} | Cloud: {company.cloud_provider}

Return JSON:
{{
  "pain_points": ["list of 4 specific business pain points"],
  "opportunities": ["list of 4 specific {COMPANY_NAME} service opportunities"],
  "recommended_services": ["list of 3-4 most relevant Aspire services"],
  "estimated_deal_value": "$X-$Y range",
  "sales_cycle": "estimated months",
  "qualification_summary": "2-3 sentence MEDDICC summary",
  "next_action": "specific next action for the SDR",
  "disqualification_risks": ["any risks or concerns"]
}}"""
        return self.run_json(prompt)

    def apply_meddicc(self, lead: Lead) -> dict:
        prompt = f"""Apply the MEDDICC qualification framework to this lead.

Company: {lead.company.name}
Contacts: {', '.join(c.full_name + ' (' + (c.title or '') + ')' for c in lead.contacts[:3])}
Pain Points: {'; '.join(lead.pain_points[:3])}
Score: {lead.score.total if lead.score else 'N/A'}/100

Return JSON:
{{
  "metrics": "quantified business impact and ROI potential",
  "economic_buyer": "who controls the budget",
  "decision_criteria": "how they will evaluate solutions",
  "decision_process": "steps in their buying process",
  "identify_pain": "core business pain driving urgency",
  "champion": "who internally will advocate for us",
  "competition": "likely competing vendors or status quo",
  "overall_assessment": "go/no-go recommendation with reasoning"
}}"""
        return self.run_json(prompt)
