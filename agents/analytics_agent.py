from __future__ import annotations
from typing import Optional

from agents.base import BaseAgent
from config.settings import COMPANY_NAME
from db import crm as db


SYSTEM_PROMPT = f"""You are a Sales Analytics Specialist for {COMPANY_NAME}.

You track, analyze, and optimize SDR performance. Key metrics you monitor:

- Reply Rate: replies / emails sent (target: >15%)
- Positive Reply Rate: positive replies / total replies (target: >40%)
- Meeting Rate: meetings booked / leads contacted (target: >5%)
- Meeting Attendance Rate: attended / booked (target: >80%)
- SQL Rate: SQLs / leads qualified (target: >20%)
- Pipeline Value: sum of estimated deal values in active pipeline
- Revenue Generated: closed won deals

You identify patterns, bottlenecks, and optimization opportunities.
You provide specific, actionable recommendations — not generic advice.
"""


class AnalyticsAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.system_prompt = SYSTEM_PROMPT

    def calculate_kpis(self) -> dict:
        summary = db.get_pipeline_summary()
        total = summary["total_leads"]
        meetings = summary["total_meetings"]
        interactions = summary["total_interactions"]
        replies = summary["reply_count"]
        status = summary["status_breakdown"]

        emails_sent = interactions
        reply_rate = round((replies / emails_sent * 100), 1) if emails_sent > 0 else 0
        meeting_rate = round((meetings / total * 100), 1) if total > 0 else 0
        sql_count = status.get("sql", 0)
        sql_rate = round((sql_count / total * 100), 1) if total > 0 else 0
        qualified = status.get("qualified", 0)
        conversion = round((meetings / qualified * 100), 1) if qualified > 0 else 0

        return {
            "total_leads": total,
            "total_meetings_booked": meetings,
            "total_interactions": interactions,
            "total_replies": replies,
            "reply_rate_pct": reply_rate,
            "meeting_rate_pct": meeting_rate,
            "sql_count": sql_count,
            "sql_rate_pct": sql_rate,
            "qualified_to_meeting_rate_pct": conversion,
            "status_breakdown": status,
            "benchmarks": {
                "reply_rate_target": "15%",
                "meeting_rate_target": "5%",
                "sql_rate_target": "20%",
            },
        }

    def generate_report(self) -> str:
        kpis = self.calculate_kpis()
        summary = db.get_pipeline_summary()
        prompt = f"""Generate a concise SDR performance report for {COMPANY_NAME}.

Current KPIs:
- Total Leads: {kpis['total_leads']}
- Meetings Booked: {kpis['total_meetings_booked']}
- Reply Rate: {kpis['reply_rate_pct']}% (target: {kpis['benchmarks']['reply_rate_target']})
- Meeting Rate: {kpis['meeting_rate_pct']}% (target: {kpis['benchmarks']['meeting_rate_target']})
- SQL Rate: {kpis['sql_rate_pct']}% (target: {kpis['benchmarks']['sql_rate_target']})
- SQLs: {kpis['sql_count']}
- Pipeline Status: {summary['status_breakdown']}

Write a brief executive report (300-400 words) covering:
1. Performance summary (green/yellow/red status per metric)
2. Top 3 wins or positives
3. Top 3 areas needing improvement
4. Specific recommendations for next 30 days
5. Priority actions this week

Use a professional tone. Be specific and data-driven."""
        return self.run(prompt)

    def recommend_optimizations(self) -> list[str]:
        kpis = self.calculate_kpis()
        prompt = f"""Based on these SDR metrics, provide 5-7 specific, actionable optimizations.

Metrics:
- Reply Rate: {kpis['reply_rate_pct']}% (target 15%+)
- Meeting Rate: {kpis['meeting_rate_pct']}% (target 5%+)
- SQL Rate: {kpis['sql_rate_pct']}% (target 20%+)
- Total Leads: {kpis['total_leads']}
- Status breakdown: {kpis['status_breakdown']}

Return JSON array of optimization recommendations (strings).
Each recommendation should be specific and implementable this week."""
        data = self.run_json(prompt)
        if isinstance(data, list):
            return data
        return [
            "Increase personalization depth — reference specific company news in first line",
            "Optimize subject lines — test question-based vs statement-based",
            "Increase follow-up cadence — most replies come after touch 3-5",
            "Focus outreach on companies with recent funding or hiring signals",
            "Multi-thread accounts — reach out to 2-3 contacts per company",
        ]

    def analyze_outreach_performance(self) -> dict:
        kpis = self.calculate_kpis()
        prompt = f"""Analyze the outreach performance and identify patterns.

Data:
{kpis}

Return JSON:
{{
  "top_performing_channels": ["ranked channels by effectiveness"],
  "best_day_to_reach_out": "recommendation",
  "optimal_sequence_length": "recommendation",
  "subject_line_tips": ["3 tips based on data"],
  "messaging_improvements": ["3 specific messaging improvements"],
  "icp_refinements": ["suggested ICP adjustments"],
  "quick_wins": ["3 things to do in the next 48 hours"]
}}"""
        return self.run_json(prompt)
