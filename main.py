#!/usr/bin/env python3
"""Aspire Softserv AI SDR — Sales Automation CLI"""
from __future__ import annotations
import json
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from orchestrator import SalesOrchestrator
from agents import (
    MarketIntelligenceAgent, AccountResearchAgent,
    QualificationAgent, AnalyticsAgent, CRMAgent,
)
from db import crm as db
from models.lead import QualificationStatus

app = typer.Typer(
    name="aspire-sdr",
    help="Aspire Softserv AI SDR — Intelligent Sales Automation",
    rich_markup_mode="rich",
)
console = Console()
orchestrator = SalesOrchestrator()


def _score_color(score: int) -> str:
    if score >= 80:
        return "bright_green"
    if score >= 65:
        return "green"
    if score >= 50:
        return "yellow"
    if score >= 35:
        return "red"
    return "bright_red"


def _status_color(status: str) -> str:
    colors = {
        "qualified": "green",
        "sql": "bright_green",
        "meeting_booked": "cyan",
        "outreach_sent": "blue",
        "new": "white",
        "researching": "yellow",
        "disqualified": "red",
        "closed_won": "bright_green",
        "closed_lost": "bright_red",
    }
    return colors.get(status, "white")


@app.command()
def search(
    industry: str = typer.Argument(..., help="Target industry (e.g. Healthcare, Manufacturing)"),
    country: str = typer.Option("USA", "--country", "-c", help="Target country"),
    count: int = typer.Option(5, "--count", "-n", help="Number of companies to find and qualify"),
):
    """Search Apollo.io and qualify leads by industry and country."""
    console.print(Panel(
        f"[bold]Searching for [cyan]{industry}[/cyan] companies in [cyan]{country}[/cyan][/bold]\n"
        f"Target count: {count}",
        title="[bold blue]AI SDR — Lead Search[/bold blue]",
        border_style="blue",
    ))

    with console.status(f"[bold green]Researching {count} companies...[/bold green]"):
        leads = orchestrator.search_and_qualify(industry, country, count=count, verbose=False)

    if not leads:
        console.print("[red]No leads found.[/red]")
        raise typer.Exit(1)

    table = Table(
        title=f"Qualified Leads — {industry} / {country}",
        box=box.ROUNDED, show_header=True, header_style="bold blue",
    )
    table.add_column("Company", style="bold", min_width=20)
    table.add_column("Industry", min_width=14)
    table.add_column("Country", min_width=8)
    table.add_column("Employees", justify="right")
    table.add_column("Score", justify="center", min_width=8)
    table.add_column("Grade", justify="center", min_width=6)
    table.add_column("Status", min_width=14)
    table.add_column("Lead ID", min_width=36)

    for lead in leads:
        score = lead.score
        sc = score.total if score else 0
        grade = score.grade if score else "?"
        table.add_row(
            lead.company.name,
            lead.company.industry or "-",
            lead.company.country or "-",
            str(lead.company.employee_count or "-"),
            Text(str(sc), style=_score_color(sc)),
            Text(grade, style=_score_color(sc)),
            Text(lead.status.value, style=_status_color(lead.status.value)),
            lead.id or "-",
        )

    console.print(table)
    console.print(f"\n[green]✓[/green] {len(leads)} leads saved to CRM")


@app.command()
def research(
    company: str = typer.Argument(..., help="Company name to research"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Company domain for enrichment"),
    outreach: bool = typer.Option(False, "--outreach", "-o", help="Also generate outreach sequence"),
):
    """Research a specific company and qualify them as a lead."""
    console.print(Panel(
        f"[bold]Researching [cyan]{company}[/cyan][/bold]",
        title="[bold blue]AI SDR — Account Research[/bold blue]",
        border_style="blue",
    ))

    with console.status("[bold green]Running deep account research...[/bold green]"):
        lead = orchestrator.process_company(company, domain, verbose=False)

    score = lead.score
    sc = score.total if score else 0

    console.print(Panel(
        f"[bold]{lead.company.name}[/bold] — {lead.company.industry} | {lead.company.country}\n"
        f"Employees: {lead.company.employee_count or 'Unknown'}  |  Revenue: {lead.company.revenue or 'Unknown'}\n"
        f"Lead Score: [{_score_color(sc)}]{sc}/100 (Grade {score.grade if score else '?'})[/{_score_color(sc)}]  |  "
        f"Status: [{_status_color(lead.status.value)}]{lead.status.value}[/{_status_color(lead.status.value)}]",
        title="Company Profile",
        border_style="cyan",
    ))

    if lead.contacts:
        t = Table(title="Decision Makers", box=box.SIMPLE, header_style="bold")
        t.add_column("Name"); t.add_column("Title"); t.add_column("Email"); t.add_column("DM?")
        for c in lead.contacts[:5]:
            t.add_row(
                c.full_name, c.title or "-", c.email or "-",
                "[green]✓[/green]" if c.is_decision_maker else "–",
            )
        console.print(t)

    if lead.pain_points:
        console.print("\n[bold yellow]Pain Points:[/bold yellow]")
        for p in lead.pain_points:
            console.print(f"  • {p}")

    if lead.recommended_services:
        console.print("\n[bold cyan]Recommended Services:[/bold cyan]")
        for s in lead.recommended_services:
            console.print(f"  • {s}")

    if lead.buying_signals:
        console.print("\n[bold green]Buying Signals:[/bold green]")
        for s in lead.buying_signals[:5]:
            console.print(f"  ✓ {s}")

    console.print(f"\n[green]Lead saved:[/green] {lead.id}")

    if outreach and lead.status == QualificationStatus.QUALIFIED:
        _run_outreach(lead)


@app.command()
def outreach(
    lead_id: str = typer.Argument(..., help="Lead ID from CRM"),
):
    """Generate a full multi-touch outreach sequence for a qualified lead."""
    lead = db.get_lead(lead_id)
    if not lead:
        console.print(f"[red]Lead {lead_id} not found.[/red]")
        raise typer.Exit(1)
    _run_outreach(lead)


def _run_outreach(lead):
    contact = lead.primary_contact
    if not contact:
        console.print("[red]No decision maker found for this lead.[/red]")
        return

    console.print(Panel(
        f"Generating outreach for [bold]{contact.full_name}[/bold] ({contact.title})\nat [bold]{lead.company.name}[/bold]",
        title="[bold blue]AI SDR — Personalized Outreach[/bold blue]",
        border_style="blue",
    ))

    with console.status("[bold green]Crafting personalized sequence...[/bold green]"):
        sequence = orchestrator.generate_outreach_for_lead(lead, verbose=False)

    if sequence.day1_email:
        console.print(Panel(
            f"[bold]Subject:[/bold] {sequence.day1_email.subject}\n\n{sequence.day1_email.body}\n\n"
            f"[dim]Word count: {sequence.day1_email.word_count} | Hook: {sequence.day1_email.personalization_hook}[/dim]",
            title="📧 Day 1 Email",
            border_style="cyan",
        ))

    if sequence.day1_linkedin_connect:
        console.print(Panel(
            sequence.day1_linkedin_connect.connection_note,
            title="💼 LinkedIn Connection Note",
            border_style="blue",
        ))

    if sequence.day7_call:
        console.print(Panel(
            f"[bold]Opening:[/bold] {sequence.day7_call.opening}\n\n"
            f"[bold]Questions:[/bold]\n" + "\n".join(f"  • {q}" for q in sequence.day7_call.qualifying_questions),
            title="📞 Day 7 Call Script",
            border_style="yellow",
        ))

    console.print(f"\n[green]✓[/green] 6-touch sequence generated over 14 days")


@app.command()
def pipeline(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
):
    """Show CRM pipeline summary and lead list."""
    summary = db.get_pipeline_summary()

    kpi_table = Table(title="Pipeline KPIs", box=box.ROUNDED, header_style="bold blue")
    kpi_table.add_column("Metric"); kpi_table.add_column("Value", justify="right")
    kpi_table.add_row("Total Leads", str(summary["total_leads"]))
    kpi_table.add_row("Meetings Booked", str(summary["total_meetings"]))
    kpi_table.add_row("Total Interactions", str(summary["total_interactions"]))
    kpi_table.add_row("Replies Received", str(summary["reply_count"]))
    if summary["total_interactions"] > 0:
        rr = round(summary["reply_count"] / summary["total_interactions"] * 100, 1)
        kpi_table.add_row("Reply Rate", f"{rr}%")
    console.print(kpi_table)

    status_table = Table(title="Pipeline by Status", box=box.SIMPLE)
    status_table.add_column("Status"); status_table.add_column("Count", justify="right")
    for s, count in sorted(summary["status_breakdown"].items()):
        status_table.add_row(
            Text(s, style=_status_color(s)),
            str(count),
        )
    console.print(status_table)

    leads = db.get_all_leads(status)
    if leads:
        t = Table(title=f"Leads{' (' + status + ')' if status else ''}", box=box.ROUNDED)
        t.add_column("Company", min_width=20); t.add_column("Industry")
        t.add_column("Score", justify="center"); t.add_column("Status")
        t.add_column("Next Action", min_width=25)
        for lead in leads[:20]:
            sc = lead.score.total if lead.score else 0
            t.add_row(
                lead.company.name,
                lead.company.industry or "-",
                Text(str(sc), style=_score_color(sc)),
                Text(lead.status.value, style=_status_color(lead.status.value)),
                (lead.next_action or "-")[:50],
            )
        console.print(t)


@app.command()
def report():
    """Generate a full analytics and performance report."""
    with console.status("[bold green]Analyzing pipeline data...[/bold green]"):
        agent = AnalyticsAgent()
        kpis = agent.calculate_kpis()
        full_report = agent.generate_report()
        optimizations = agent.recommend_optimizations()

    kpi_table = Table(title="SDR Performance KPIs", box=box.ROUNDED, header_style="bold")
    kpi_table.add_column("Metric"); kpi_table.add_column("Value", justify="right"); kpi_table.add_column("Target", justify="right")
    kpi_table.add_row("Reply Rate", f"{kpis['reply_rate_pct']}%", "15%")
    kpi_table.add_row("Meeting Rate", f"{kpis['meeting_rate_pct']}%", "5%")
    kpi_table.add_row("SQL Rate", f"{kpis['sql_rate_pct']}%", "20%")
    kpi_table.add_row("Meetings Booked", str(kpis['total_meetings_booked']), "-")
    kpi_table.add_row("Total Leads", str(kpis['total_leads']), "-")
    console.print(kpi_table)

    console.print(Panel(full_report, title="Executive Report", border_style="blue"))

    console.print("\n[bold yellow]Optimization Recommendations:[/bold yellow]")
    for i, rec in enumerate(optimizations, 1):
        console.print(f"  {i}. {rec}")


@app.command()
def workflow():
    """Run the daily sales workflow — process follow-up queue and generate report."""
    console.print(Panel(
        "[bold]Running daily sales workflow...[/bold]",
        title="[bold blue]AI SDR — Daily Workflow[/bold blue]",
        border_style="blue",
    ))
    with console.status("[bold green]Processing...[/bold green]"):
        result = orchestrator.run_daily_workflow(verbose=False)

    console.print(f"[green]✓[/green] Follow-up queue: {result['leads_in_queue']} leads")
    console.print(f"[green]✓[/green] Processed: {result['leads_processed']} leads")
    console.print(Panel(result["report"], title="Daily Report", border_style="cyan"))


@app.command()
def qualify(
    lead_id: str = typer.Argument(..., help="Lead ID to qualify"),
):
    """Run MEDDICC qualification on a saved lead."""
    lead = db.get_lead(lead_id)
    if not lead:
        console.print(f"[red]Lead {lead_id} not found.[/red]")
        raise typer.Exit(1)

    with console.status("[bold green]Running MEDDICC qualification...[/bold green]"):
        agent = QualificationAgent()
        meddicc = agent.apply_meddicc(lead)

    console.print(Panel(
        f"[bold]{lead.company.name}[/bold] — Score: {lead.score.total if lead.score else 'N/A'}/100\n",
        title="MEDDICC Qualification",
        border_style="cyan",
    ))
    for key, val in meddicc.items():
        console.print(f"[bold yellow]{key.upper().replace('_', ' ')}:[/bold yellow] {val}")


if __name__ == "__main__":
    app()
