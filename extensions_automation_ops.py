"""
Byblos CRM Automation Ops Extension

Adds operating rules for SLA monitoring, dunning stages, offer/order statuses,
import quarantine decisions, and AI assistant safety levels. This file is a
lightweight extension module that can be imported into app.py or used as a
reference for integrating the next operational layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class SlaRule:
    object_type: str
    trigger_status: str
    due_hours: int
    escalation: str


SLA_RULES: List[SlaRule] = [
    SlaRule("lead", "neu", 4, "Lead innerhalb von 4 Stunden kontaktieren"),
    SlaRule("angebot", "entwurf", 24, "Angebot innerhalb von 24 Stunden prüfen"),
    SlaRule("vertrag", "zur_unterschrift", 48, "Vertrag nach 48 Stunden nachfassen"),
    SlaRule("rechnung", "offen", 168, "Rechnung nach 7 Tagen prüfen"),
]

MAHNSTUFEN = [
    {"stage": 0, "name": "offen", "days_after_due": 0, "action": "freundliche Zahlungserinnerung vorbereiten"},
    {"stage": 1, "name": "mahnung_1", "days_after_due": 7, "action": "1. Mahnung senden"},
    {"stage": 2, "name": "mahnung_2", "days_after_due": 14, "action": "2. Mahnung senden"},
    {"stage": 3, "name": "inkasso_pruefen", "days_after_due": 30, "action": "Inkasso / Rechtsweg prüfen"},
]

ANGEBOTS_STATUS = ["neu", "entwurf", "geprueft", "gesendet", "angenommen", "abgelehnt", "abgelaufen"]
AUFTRAGS_STATUS = ["geplant", "aktiv", "pausiert", "abgeschlossen", "storniert"]
DOKUMENT_STATUS = ["entwurf", "zur_pruefung", "freigegeben", "unterschrieben", "archiviert", "geloescht"]


def parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except Exception:
        return None


def calculate_dunning_stage(due_date: Any, paid_amount: float = 0.0, gross_amount: float = 0.0) -> Dict[str, Any]:
    due = parse_date(due_date)
    if gross_amount > 0 and paid_amount >= gross_amount:
        return {"stage": -1, "name": "bezahlt", "action": "keine Aktion", "days_overdue": 0}
    if not due:
        return {"stage": 0, "name": "datum_fehlt", "action": "Fälligkeitsdatum prüfen", "days_overdue": 0}
    days_overdue = (date.today() - due).days
    selected = MAHNSTUFEN[0]
    for rule in MAHNSTUFEN:
        if days_overdue >= rule["days_after_due"]:
            selected = rule
    result = dict(selected)
    result["days_overdue"] = max(0, days_overdue)
    return result


def classify_import_confidence(confidence: float, has_duplicate: bool = False) -> Dict[str, str]:
    if has_duplicate:
        return {"zone": "quarantaene", "action": "Dublettenverdacht manuell prüfen"}
    if confidence >= 95:
        return {"zone": "auto", "action": "automatisch verarbeiten"}
    if confidence >= 75:
        return {"zone": "review", "action": "in Prüfliste mit Vorschlag"}
    return {"zone": "quarantaene", "action": "nicht automatisch buchen"}


def ai_answer_guard(question: str, context_found: bool, confidence: float) -> Dict[str, str]:
    if not context_found:
        return {
            "level": "rot",
            "answer_policy": "Ich weiß es nicht. Keine passende CRM-Quelle gefunden.",
            "next_action": "Suche erweitern oder Datensatz prüfen.",
        }
    if confidence < 70:
        return {
            "level": "gelb",
            "answer_policy": "Nur als Hinweis anzeigen, nicht automatisch entscheiden.",
            "next_action": "Menschliche Prüfung erforderlich.",
        }
    return {
        "level": "gruen",
        "answer_policy": "Antwort mit Quellenhinweis aus CRM anzeigen.",
        "next_action": "Bei Buchung/Freigabe trotzdem Freigabe verlangen.",
    }


def daily_close_checklist() -> List[str]:
    return [
        "Neue Leads geprüft",
        "Offene Angebote nachgefasst",
        "Neue Rechnungsimporte geprüft",
        "Quarantäne-Dokumente bearbeitet",
        "Offene Aufgaben mit Frist heute erledigt oder begründet verschoben",
        "Backup/Export-Status geprüft",
    ]


def monthly_close_checklist() -> List[str]:
    return [
        "Offene Rechnungen und Mahnstufen geprüft",
        "BWA-/Ausgabenexport erstellt",
        "Kunden- und Vertragsdaten geprüft",
        "Datenschutz-/AVV-Prüfpunkte geprüft",
        "Backup extern gesichert",
        "KI-Trainingsdaten bereinigt",
    ]
