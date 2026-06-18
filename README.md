# Sales-Automation

AI-powered Sales Automation platform for Aspire Softserv — a modular, multi-agent SDR system that automates B2B lead generation, account research, decision-maker discovery, lead qualification, personalized outreach, meeting booking, CRM management, and sales analytics using Claude AI and Apollo.io.

---

## Architecture

Nine specialized AI agents, each powered by Claude (`claude-sonnet-4-6`), coordinate through a central orchestrator:

| Agent | Responsibility |
|---|---|
| `MarketIntelligenceAgent` | Target industry/ICP analysis, buying signal identification |
| `AccountResearchAgent` | Company deep-dive via Apollo.io enrichment |
| `DecisionMakerAgent` | Executive discovery, prioritization, contact enrichment |
| `QualificationAgent` | MEDDICC + BANT + SPICED scoring (0–100) |
| `PersonalizationAgent` | <120-word emails, LinkedIn messages, cold call scripts |
| `OutreachAgent` | 14-day multi-touch sequences, objection handling |
| `MeetingBookingAgent` | Qualification gates, meeting briefs, confirmations |
| `CRMAgent` | SQLite pipeline tracking, follow-up queue |
| `AnalyticsAgent` | KPIs, executive reports, optimization recommendations |

```
main.py (CLI)
    └── orchestrator.py
            ├── agents/market_intelligence_agent.py
            ├── agents/account_research_agent.py
            ├── agents/decision_maker_agent.py
            ├── agents/qualification_agent.py
            ├── agents/personalization_agent.py
            ├── agents/outreach_agent.py
            ├── agents/meeting_booking_agent.py
            ├── agents/crm_agent.py
            └── agents/analytics_agent.py
                    ├── integrations/apollo.py   (Apollo.io REST API)
                    ├── db/crm.py                (SQLite CRM)
                    └── models/                  (Pydantic data models)
```

---

## Target ICP

**Industries:** Healthcare, Manufacturing, Retail, Logistics, Finance, Insurance, E-commerce, Pharma, Energy, Construction, and more

**Countries:** USA, Canada, UK, Germany, France, Netherlands, Australia, Singapore, UAE, Saudi Arabia

**Company Size:** 100–5,000 employees | Revenue $10M+

**Decision Makers:** CEO, CTO, CIO, VP Engineering, Head of IT, Digital Transformation Director, Operations Director

---

## Services Sold

AI & Automation · Generative AI · AI Agents · LLM Integration · SaaS & Enterprise Software · Odoo/ERPNext/Custom ERP · AWS/Azure/GCP · DevOps · Data Engineering · BI & Analytics · Legacy Modernization · Process Automation · UI/UX · QA Automation

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/hiteshvagh/Sales-Automation.git
cd Sales-Automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY (required) and APOLLO_API_KEY (optional)
```

### 3. Run

```bash
# Research a specific company
python main.py research "Acme Corp" --domain acmecorp.com

# Search and qualify leads by industry
python main.py search Healthcare --country USA --count 5

# Generate personalized outreach sequence
python main.py outreach <lead-id>

# View pipeline
python main.py pipeline

# Run MEDDICC qualification
python main.py qualify <lead-id>

# Analytics report
python main.py report

# Daily workflow (follow-up queue + report)
python main.py workflow
```

---

## Lead Scoring (0–100)

| Dimension | Max Points |
|---|---|
| Company Fit | 20 |
| Buying Intent | 20 |
| Technology Need | 15 |
| Growth | 10 |
| Funding | 10 |
| Urgency | 10 |
| Decision Maker Access | 10 |
| Response Probability | 5 |

**Grade A (80+):** SQL-ready · **Grade B (65–79):** Prioritize · **Grade C (50–64):** Nurture · **Below 50:** Deprioritize

---

## Outreach Sequence

```
Day 1  → LinkedIn visit + connection note + Email #1
Day 3  → LinkedIn follow-up message
Day 5  → Email #2 (new angle)
Day 7  → Cold call
Day 10 → Case study email
Day 14 → Final breakup email
```

Email rules: <120 words · Personalized opener → Observation → Pain point → Value prop → Proof → Single CTA

---

## Qualification Framework

**MEDDICC:** Metrics · Economic Buyer · Decision Criteria · Decision Process · Identify Pain · Champion · Competition

**BANT:** Budget · Authority · Need · Timeline

**SPICED:** Situation · Pain · Impact · Critical Event · Decision

---

## Stack

- **AI:** Anthropic Claude (`claude-sonnet-4-6`)
- **Lead Data:** Apollo.io REST API
- **CLI:** Typer + Rich
- **Data Models:** Pydantic v2
- **Database:** SQLite (stdlib)
- **HTTP:** httpx

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `APOLLO_API_KEY` | No | Apollo.io API key (falls back to AI-generated data) |
| `SMTP_HOST` | No | SMTP host for email sending |
| `SMTP_USER` | No | SMTP username |
| `SMTP_PASS` | No | SMTP password |
