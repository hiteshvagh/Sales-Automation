from __future__ import annotations
from typing import Optional

from agents.base import BaseAgent
from config.settings import (
    COMPANY_NAME, TARGET_INDUSTRIES, TARGET_COUNTRIES,
    DECISION_MAKER_TITLES, BUYING_SIGNALS,
)
from integrations import apollo


SYSTEM_PROMPT = f"""You are a Market Intelligence Specialist for {COMPANY_NAME}, a global IT Consulting and Digital Transformation company.

Your job is to identify the most promising target markets, industries, and accounts for outbound B2B sales.

You understand:
- Which industries are most likely to need IT modernization, AI, ERP, Cloud, or automation
- What buying signals indicate a company is ready to invest in technology
- How to prioritize accounts by potential deal value and fit
- Market trends that create urgency for digital transformation

Always respond with structured JSON when asked for data.
"""


class MarketIntelligenceAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT

    def identify_target_accounts(
        self,
        industry: str,
        country: str = "USA",
        employee_range: str = "100,1000",
        count: int = 10,
    ) -> list[dict]:
        apollo_result = apollo.search_organizations(
            industries=[industry],
            countries=[country],
            employee_ranges=[employee_range],
            per_page=count,
        )
        orgs = apollo_result.get("organizations", [])
        if not orgs:
            prompt = f"""Generate a list of {count} realistic target companies in the {industry} industry in {country} that would benefit from IT consulting, AI, ERP, or cloud transformation services.

Return JSON array where each item has: name, domain, industry, country, employee_count, description, why_target"""
            data = self.run_json(prompt)
            if isinstance(data, list):
                return data
            return []

        results = []
        for org in orgs[:count]:
            results.append({
                "name": org.get("name", ""),
                "domain": org.get("primary_domain", ""),
                "industry": org.get("industry", industry),
                "country": org.get("country", country),
                "employee_count": org.get("num_employees", 0),
                "description": org.get("short_description", ""),
                "apollo_id": org.get("id", ""),
            })
        return results

    def analyze_market_trends(self, industry: str) -> dict:
        prompt = f"""Analyze the current market trends for the {industry} industry from a B2B IT consulting perspective.

Return JSON with:
{{
  "industry": "{industry}",
  "top_pain_points": ["list of 5 common pain points"],
  "technology_trends": ["list of 5 tech trends driving investment"],
  "buying_triggers": ["list of 5 events that trigger IT spending"],
  "common_tech_stack": ["list of common technologies used"],
  "erp_systems": ["commonly used ERP systems"],
  "avg_deal_size_range": "e.g. $50K-$500K",
  "sales_cycle_months": "estimated sales cycle",
  "key_decision_makers": ["list of titles"],
  "recommended_services": ["which Aspire services fit best"]
}}"""
        return self.run_json(prompt)

    def score_industry_opportunity(self, industry: str) -> dict:
        prompt = f"""Rate the {industry} industry as a sales target for an IT consulting company offering AI, ERP, Cloud, and Digital Transformation services.

Return JSON:
{{
  "industry": "{industry}",
  "opportunity_score": 0-100,
  "reasoning": "2-3 sentence explanation",
  "urgency": "high/medium/low",
  "competition_level": "high/medium/low",
  "recommended_approach": "brief strategy",
  "best_services_to_lead_with": ["list of 3 services"]
}}"""
        return self.run_json(prompt)

    def get_buying_signals_for_industry(self, industry: str) -> list[str]:
        prompt = f"""List the top 10 most reliable buying signals indicating that a {industry} company is ready to invest in IT consulting, digital transformation, or AI/ERP/cloud services.

Return JSON array of strings, each describing a specific buying signal."""
        data = self.run_json(prompt)
        if isinstance(data, list):
            return data
        return BUYING_SIGNALS
