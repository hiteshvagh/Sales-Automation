from __future__ import annotations
from typing import Optional

from agents import (
    MarketIntelligenceAgent,
    AccountResearchAgent,
    DecisionMakerAgent,
    QualificationAgent,
    PersonalizationAgent,
    OutreachAgent,
    MeetingBookingAgent,
    CRMAgent,
    AnalyticsAgent,
)
from models.lead import Lead, QualificationStatus
from models.outreach import OutreachSequence


class SalesOrchestrator:
    def __init__(self, api_key: Optional[str] = None):
        self.market = MarketIntelligenceAgent(api_key)
        self.research = AccountResearchAgent(api_key)
        self.dm = DecisionMakerAgent(api_key)
        self.qualify = QualificationAgent(api_key)
        self.personalize = PersonalizationAgent(api_key)
        self.outreach = OutreachAgent(api_key)
        self.meeting = MeetingBookingAgent(api_key)
        self.crm = CRMAgent(api_key)
        self.analytics = AnalyticsAgent(api_key)

    def process_company(
        self,
        company_name: str,
        domain: Optional[str] = None,
        verbose: bool = False,
    ) -> Lead:
        if verbose:
            print(f"[1/5] Researching {company_name}...")
        company = self.research.research_company(company_name, domain)
        buying_signals = self.research.identify_buying_signals(company)

        if verbose:
            print(f"[2/5] Finding decision makers at {company_name}...")
        contacts = self.dm.find_decision_makers(company)
        contacts = self.dm.prioritize_contacts(contacts)

        if verbose:
            print(f"[3/5] Qualifying lead...")
        lead = self.qualify.qualify_lead(company, contacts, buying_signals)

        if verbose:
            print(f"[4/5] Saving to CRM...")
        lead_id = self.crm.save_lead(lead)
        lead.id = lead_id

        if verbose:
            score = lead.score
            print(f"[5/5] Done. Score: {score.total if score else 'N/A'}/100 | Status: {lead.status.value}")

        return lead

    def generate_outreach_for_lead(self, lead: Lead, verbose: bool = False) -> OutreachSequence:
        contact = lead.primary_contact
        if not contact:
            raise ValueError(f"No contacts found for lead {lead.id}")

        if verbose:
            print(f"Generating personalized outreach for {contact.full_name} at {lead.company.name}...")

        sequence = self.personalize.generate_outreach(lead, contact)
        plan = self.outreach.build_execution_plan(lead, sequence)

        self.crm.update_status(lead.id, QualificationStatus.OUTREACH_SENT, "Outreach sequence generated")
        self.crm.log_interaction(
            lead.id, "multi-channel",
            f"Outreach sequence generated: {len(plan)} touchpoints over 14 days",
            "sequence_ready",
        )

        if verbose:
            print(f"Generated {len(plan)}-step sequence via {sequence.primary_channel}")

        return sequence

    def search_and_qualify(
        self,
        industry: str,
        country: str = "USA",
        count: int = 10,
        verbose: bool = False,
    ) -> list[Lead]:
        if verbose:
            print(f"Searching for {count} {industry} companies in {country}...")

        targets = self.market.identify_target_accounts(industry, country, count=count)
        leads = []

        for i, target in enumerate(targets[:count]):
            if verbose:
                print(f"\n[{i+1}/{len(targets)}] Processing: {target.get('name', 'Unknown')}")
            try:
                lead = self.process_company(
                    company_name=target.get("name", ""),
                    domain=target.get("domain"),
                    verbose=verbose,
                )
                leads.append(lead)
            except Exception as e:
                if verbose:
                    print(f"  Error processing {target.get('name')}: {e}")
                continue

        return leads

    def run_daily_workflow(self, verbose: bool = False) -> dict:
        if verbose:
            print("Running daily sales workflow...")

        queue = self.crm.get_follow_up_queue()
        if verbose:
            print(f"  {len(queue)} leads in follow-up queue")

        processed = 0
        for lead in queue:
            try:
                next_step = self.crm.suggest_next_action(lead)
                self.crm.log_interaction(
                    lead.id, "crm",
                    f"Daily workflow: {next_step.get('action', 'Follow-up')}",
                    "scheduled",
                )
                processed += 1
            except Exception:
                continue

        kpis = self.analytics.calculate_kpis()
        report = self.analytics.generate_report()

        return {
            "leads_in_queue": len(queue),
            "leads_processed": processed,
            "kpis": kpis,
            "report": report,
        }

    def book_meeting(
        self,
        lead_id: str,
        contact_name: str,
        scheduled_at: str,
        timezone: str = "EST",
        platform: str = "Zoom",
        agenda: list[str] = None,
        verbose: bool = False,
    ) -> dict:
        lead = self.crm.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        contact = lead.primary_contact
        if not contact:
            raise ValueError("No primary contact found")

        brief = self.meeting.prepare_meeting_brief(lead, contact, scheduled_at, platform)
        agenda_str = "\n".join(agenda or brief.get("agenda", []))

        meeting_id = self.crm.save_meeting(
            lead_id=lead_id,
            contact_name=contact_name,
            scheduled_at=scheduled_at,
            timezone=timezone,
            platform=platform,
            agenda=agenda_str,
        )

        confirmation_email = self.meeting.generate_meeting_confirmation_email(
            lead, contact, scheduled_at, platform,
            agenda or brief.get("agenda", []),
        )

        if verbose:
            print(f"Meeting booked: {meeting_id}")

        return {
            "meeting_id": meeting_id,
            "brief": brief,
            "confirmation_email": confirmation_email,
        }
