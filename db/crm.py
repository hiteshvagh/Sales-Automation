from __future__ import annotations
import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from config.settings import DB_PATH
from models.lead import Lead, Company, Contact, LeadScore, QualificationStatus


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize() -> None:
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                company_json TEXT NOT NULL,
                contacts_json TEXT NOT NULL DEFAULT '[]',
                score_json TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                pain_points_json TEXT NOT NULL DEFAULT '[]',
                opportunities_json TEXT NOT NULL DEFAULT '[]',
                buying_signals_json TEXT NOT NULL DEFAULT '[]',
                recommended_services_json TEXT NOT NULL DEFAULT '[]',
                estimated_deal_value TEXT,
                notes TEXT DEFAULT '',
                next_action TEXT,
                next_action_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'outbound',
                content TEXT NOT NULL,
                outcome TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(lead_id) REFERENCES leads(id)
            );

            CREATE TABLE IF NOT EXISTS outreach_sequences (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                sequence_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(lead_id) REFERENCES leads(id)
            );

            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                contact_name TEXT,
                scheduled_at TEXT NOT NULL,
                timezone TEXT DEFAULT 'UTC',
                platform TEXT DEFAULT 'Zoom',
                agenda TEXT,
                status TEXT DEFAULT 'scheduled',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(lead_id) REFERENCES leads(id)
            );
        """)


def save_lead(lead: Lead) -> str:
    initialize()
    if not lead.id:
        lead.id = str(uuid.uuid4())
    lead.updated_at = datetime.utcnow()
    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO leads (
                id, company_name, company_json, contacts_json, score_json,
                status, pain_points_json, opportunities_json, buying_signals_json,
                recommended_services_json, estimated_deal_value, notes,
                next_action, next_action_date, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            lead.id,
            lead.company.name,
            lead.company.model_dump_json(),
            json.dumps([c.model_dump() for c in lead.contacts]),
            lead.score.model_dump_json() if lead.score else None,
            lead.status.value,
            json.dumps(lead.pain_points),
            json.dumps(lead.opportunities),
            json.dumps(lead.buying_signals),
            json.dumps(lead.recommended_services),
            lead.estimated_deal_value,
            lead.notes,
            lead.next_action,
            lead.next_action_date,
            lead.created_at.isoformat(),
            lead.updated_at.isoformat(),
        ))
    return lead.id


def get_lead(lead_id: str) -> Optional[Lead]:
    initialize()
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        return None
    return _row_to_lead(row)


def update_lead_status(lead_id: str, status: QualificationStatus, notes: str = "") -> None:
    initialize()
    with _get_conn() as conn:
        conn.execute(
            "UPDATE leads SET status=?, notes=notes||?, updated_at=? WHERE id=?",
            (status.value, f"\n{notes}" if notes else "", datetime.utcnow().isoformat(), lead_id),
        )


def log_interaction(lead_id: str, channel: str, content: str, outcome: str = "", direction: str = "outbound") -> None:
    initialize()
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO interactions (id,lead_id,channel,direction,content,outcome,created_at) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), lead_id, channel, direction, content, outcome, datetime.utcnow().isoformat()),
        )


def get_all_leads(status: Optional[str] = None) -> list[Lead]:
    initialize()
    with _get_conn() as conn:
        if status:
            rows = conn.execute("SELECT * FROM leads WHERE status=? ORDER BY updated_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM leads ORDER BY updated_at DESC").fetchall()
    return [_row_to_lead(r) for r in rows]


def get_follow_up_queue() -> list[Lead]:
    initialize()
    today = datetime.utcnow().date().isoformat()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM leads WHERE next_action_date<=? AND status NOT IN ('closed_won','closed_lost','disqualified') ORDER BY next_action_date",
            (today,),
        ).fetchall()
    return [_row_to_lead(r) for r in rows]


def save_meeting(lead_id: str, contact_name: str, scheduled_at: str, timezone: str,
                 platform: str, agenda: str) -> str:
    initialize()
    meeting_id = str(uuid.uuid4())
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO meetings (id,lead_id,contact_name,scheduled_at,timezone,platform,agenda,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (meeting_id, lead_id, contact_name, scheduled_at, timezone, platform, agenda, datetime.utcnow().isoformat()),
        )
    return meeting_id


def get_pipeline_summary() -> dict:
    initialize()
    with _get_conn() as conn:
        rows = conn.execute("SELECT status, COUNT(*) as cnt FROM leads GROUP BY status").fetchall()
        total_leads = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        total_meetings = conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
        total_interactions = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        replies = conn.execute("SELECT COUNT(*) FROM interactions WHERE direction='inbound'").fetchone()[0]
    status_counts = {r["status"]: r["cnt"] for r in rows}
    return {
        "total_leads": total_leads,
        "total_meetings": total_meetings,
        "total_interactions": total_interactions,
        "reply_count": replies,
        "status_breakdown": status_counts,
    }


def _row_to_lead(row: sqlite3.Row) -> Lead:
    company = Company.model_validate_json(row["company_json"])
    contacts_data = json.loads(row["contacts_json"])
    contacts = [Contact.model_validate(c) for c in contacts_data]
    score = LeadScore.model_validate_json(row["score_json"]) if row["score_json"] else None
    return Lead(
        id=row["id"],
        company=company,
        contacts=contacts,
        score=score,
        status=QualificationStatus(row["status"]),
        pain_points=json.loads(row["pain_points_json"]),
        opportunities=json.loads(row["opportunities_json"]),
        buying_signals=json.loads(row["buying_signals_json"]),
        recommended_services=json.loads(row["recommended_services_json"]),
        estimated_deal_value=row["estimated_deal_value"],
        notes=row["notes"] or "",
        next_action=row["next_action"],
        next_action_date=row["next_action_date"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
