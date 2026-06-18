from __future__ import annotations
from typing import Optional

from agents.base import BaseAgent
from config.settings import COMPANY_NAME
from integrations import apollo
from models.lead import Company, FundingInfo, HiringSignal


SYSTEM_PROMPT = f"""You are an Account Research Specialist for {COMPANY_NAME}.

Your job is to conduct deep research on target companies to identify:
- Business overview and strategic direction
- Technology stack, ERP, CRM, and cloud infrastructure
- Recent news, funding, leadership changes, product launches
- Hiring patterns that signal technology investment
- Pain points and gaps that {COMPANY_NAME} can solve
- Buying signals and urgency indicators

Always be specific and actionable. Avoid generic statements.
Return structured JSON when asked for data.
"""


class AccountResearchAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT

    def research_company(self, company_name: str, domain: Optional[str] = None) -> Company:
        enriched = {}
        if domain:
            enriched = apollo.enrich_organization(domain)
        org_data = enriched.get("organization", {})

        if org_data:
            return self._parse_apollo_org(org_data, company_name)

        prompt = f"""Research the company "{company_name}"{f' (domain: {domain})' if domain else ''}.

Return JSON:
{{
  "name": "{company_name}",
  "domain": "company domain",
  "industry": "primary industry",
  "country": "headquarters country",
  "city": "headquarters city",
  "employee_count": estimated number,
  "revenue": "estimated annual revenue e.g. $50M-$100M",
  "description": "2-3 sentence company description",
  "tech_stack": ["list of known technologies"],
  "erp_system": "ERP system if known or null",
  "crm_system": "CRM if known or null",
  "cloud_provider": "AWS/Azure/GCP/On-premise/Unknown",
  "recent_news": ["list of recent news items or developments"],
  "funding_info": {{
    "total_raised": "amount or null",
    "last_round": "Series A/B/C etc or null",
    "last_round_date": "date or null",
    "investors": []
  }},
  "hiring_signals": [
    {{"role": "job title being hired", "count": 1, "relevance": "what it signals"}}
  ]
}}"""
        data = self.run_json(prompt)
        return self._dict_to_company(data, company_name)

    def identify_buying_signals(self, company: Company) -> list[str]:
        context = f"""Company: {company.name}
Industry: {company.industry}
Employees: {company.employee_count}
Revenue: {company.revenue}
Tech Stack: {', '.join(company.tech_stack)}
ERP: {company.erp_system}
Recent News: {'; '.join(company.recent_news[:3])}
Hiring: {', '.join(h.role for h in company.hiring_signals[:5])}
Funding: {company.funding_info.last_round if company.funding_info else 'Unknown'}"""

        prompt = f"""Based on this company profile, identify specific buying signals that indicate they may need IT consulting, AI, ERP modernization, or cloud services.

{context}

Return JSON array of specific buying signals (strings), each explaining what was observed and what it signals."""
        data = self.run_json(prompt)
        if isinstance(data, list):
            return data
        return []

    def identify_tech_gaps(self, company: Company) -> list[str]:
        prompt = f"""Analyze {company.name}'s technology stack and identify gaps or modernization opportunities.

Known stack: {', '.join(company.tech_stack) or 'Unknown'}
ERP: {company.erp_system or 'Unknown'}
CRM: {company.crm_system or 'Unknown'}
Cloud: {company.cloud_provider or 'Unknown'}
Industry: {company.industry}
Employee Count: {company.employee_count}

Return JSON array of technology gap/opportunity strings relevant to IT consulting and digital transformation."""
        data = self.run_json(prompt)
        if isinstance(data, list):
            return data
        return []

    def estimate_deal_value(self, company: Company) -> str:
        prompt = f"""Estimate the potential deal value for an IT consulting engagement with {company.name}.

Details:
- Industry: {company.industry}
- Employees: {company.employee_count}
- Revenue: {company.revenue}
- Tech Stack: {', '.join(company.tech_stack[:5])}

Return JSON: {{"estimate": "$X - $Y", "reasoning": "brief explanation", "recommended_services": ["list"]}}"""
        data = self.run_json(prompt)
        return data.get("estimate", "Unknown") if isinstance(data, dict) else "Unknown"

    def _parse_apollo_org(self, org: dict, fallback_name: str) -> Company:
        funding = None
        if org.get("latest_funding_round_date") or org.get("funding_events"):
            events = org.get("funding_events", [])
            funding = FundingInfo(
                total_raised=str(org.get("total_funding", "")),
                last_round=events[0].get("type", "") if events else None,
                last_round_date=org.get("latest_funding_round_date", ""),
                investors=[i.get("name", "") for i in org.get("investors", [])[:5]],
            )
        return Company(
            name=org.get("name", fallback_name),
            domain=org.get("primary_domain", ""),
            industry=org.get("industry", ""),
            country=org.get("country", ""),
            city=org.get("city", ""),
            employee_count=org.get("num_employees") or 0,
            revenue=str(org.get("annual_revenue", "")),
            description=org.get("short_description", ""),
            tech_stack=org.get("technology_names", [])[:20],
            linkedin_url=org.get("linkedin_url", ""),
            funding_info=funding,
            apollo_id=org.get("id", ""),
        )

    def _dict_to_company(self, data: dict, fallback_name: str) -> Company:
        funding_data = data.get("funding_info", {}) or {}
        funding = FundingInfo(**funding_data) if funding_data else None
        hiring_data = data.get("hiring_signals", []) or []
        hiring = [HiringSignal(**h) if isinstance(h, dict) else HiringSignal(role=str(h)) for h in hiring_data]
        return Company(
            name=data.get("name", fallback_name),
            domain=data.get("domain"),
            industry=data.get("industry"),
            country=data.get("country"),
            city=data.get("city"),
            employee_count=data.get("employee_count"),
            revenue=str(data.get("revenue", "")),
            description=data.get("description", ""),
            tech_stack=data.get("tech_stack", []),
            erp_system=data.get("erp_system"),
            crm_system=data.get("crm_system"),
            cloud_provider=data.get("cloud_provider"),
            recent_news=data.get("recent_news", []),
            funding_info=funding,
            hiring_signals=hiring,
        )
