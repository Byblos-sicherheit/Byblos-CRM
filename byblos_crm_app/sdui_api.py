"""Builds the SDUI config for Byblos CRM (Python/Streamlit backend).

Usage:
    python byblos_crm_app/sdui_api.py
Outputs the full SDUI JSON config to stdout.
"""
import json
from .sdui_types import (
    SDUIAction, SDUIColumn, SDUIComponent,
    SDUIScreen, SDUINavItem, SDUIConfig,
)


# --- helpers ----------------------------------------------------------------

def _header(title: str, subtitle: str = "", tag: str = "") -> SDUIComponent:
    props: dict = {"title": title}
    if subtitle:
        props["subtitle"] = subtitle
    if tag:
        props["tag"] = tag
    return SDUIComponent(type="page_header", props=props)


def _stat(label: str, value: str, direction: str = "neutral", trend_label: str = "") -> SDUIComponent:
    props: dict = {
        "label": label,
        "value": value,
        "trend": {"direction": direction, "label": trend_label},
    }
    return SDUIComponent(type="stat_card", props=props)


def _grid(cols: int, children: list) -> SDUIComponent:
    return SDUIComponent(type="grid", props={"cols": cols}, children=children)


def _stack(children: list) -> SDUIComponent:
    return SDUIComponent(type="stack", children=children)


def _table(columns: list[SDUIColumn], rows: list[dict]) -> SDUIComponent:
    return SDUIComponent(
        type="data_table",
        props={"columns": [c.to_dict() for c in columns], "rows": rows},
    )


def _chart(title: str, bars: list[dict]) -> SDUIComponent:
    return SDUIComponent(type="metric_chart", props={"title": title, "bars": bars})


def _section(title: str, children: list) -> SDUIComponent:
    return SDUIComponent(type="section", props={"title": title}, children=children)


# --- screens ----------------------------------------------------------------

def _build_dashboard() -> SDUIScreen:
    return SDUIScreen(
        id="dashboard",
        title="Dashboard",
        root=_stack([
            _header("Dashboard", "Willkommen im Byblos CRM", "Heute"),
            _grid(4, [
                _stat("Aktive Kunden",    "248", "up",   "+12 diese Woche"),
                _stat("Offene Deals",     "34",  "up",   "+5 diese Woche"),
                _stat("Pipeline-Wert",    "€ 1.2M", "up", "+8.4%"),
                _stat("Abschlussrate",    "68%", "down", "-2% vs Vormonat"),
            ]),
            _grid(2, [
                _chart("Umsatz letzte 6 Monate", [
                    {"label": "Feb", "value": 65000},
                    {"label": "Mrz", "value": 82000},
                    {"label": "Apr", "value": 74000},
                    {"label": "Mai", "value": 91000},
                    {"label": "Jun", "value": 88000},
                    {"label": "Jul", "value": 103000},
                ]),
                _chart("Neue Kunden pro Monat", [
                    {"label": "Feb", "value": 8},
                    {"label": "Mrz", "value": 14},
                    {"label": "Apr", "value": 11},
                    {"label": "Mai", "value": 18},
                    {"label": "Jun", "value": 15},
                    {"label": "Jul", "value": 22},
                ]),
            ]),
            _table(
                columns=[
                    SDUIColumn("name",    "Name"),
                    SDUIColumn("firma",   "Firma"),
                    SDUIColumn("status",  "Status",  "badge"),
                    SDUIColumn("wert",    "Wert",    "currency"),
                    SDUIColumn("datum",   "Datum"),
                ],
                rows=[
                    {"id": "r1", "cells": {
                        "name":  {"value": "Anna Bauer"},
                        "firma": {"value": "Bauer GmbH"},
                        "status":{"value": "Aktiv",   "color": "green"},
                        "wert":  {"value": "48500",   "format": "EUR"},
                        "datum": {"value": "2024-07-18"},
                    }},
                    {"id": "r2", "cells": {
                        "name":  {"value": "Thomas Müller"},
                        "firma": {"value": "Müller AG"},
                        "status":{"value": "Ausstehend", "color": "yellow"},
                        "wert":  {"value": "72300",   "format": "EUR"},
                        "datum": {"value": "2024-07-17"},
                    }},
                ],
            ),
        ]),
    )


def _build_kunden() -> SDUIScreen:
    cols = [
        SDUIColumn("name",    "Name"),
        SDUIColumn("firma",   "Firma"),
        SDUIColumn("email",   "E-Mail"),
        SDUIColumn("status",  "Status",  "badge"),
        SDUIColumn("umsatz",  "Umsatz",  "currency"),
    ]
    rows = [
        {"id": f"k{i}", "cells": {
            "name":   {"value": name},
            "firma":  {"value": firma},
            "email":  {"value": email},
            "status": {"value": status, "color": color},
            "umsatz": {"value": str(umsatz), "format": "EUR"},
        }}
        for i, (name, firma, email, status, color, umsatz) in enumerate([
            ("Anna Bauer",     "Bauer GmbH",      "anna@bauer.de",     "Aktiv",       "green",  48500),
            ("Thomas Müller", "Müller AG",       "t.m@mueller.de",  "Aktiv",       "green",  72300),
            ("Sara Klein",     "Klein & Co.",     "sara@kleinco.de",   "Ausstehend",  "yellow", 15200),
            ("David Braun",    "Braun Tech",      "d.braun@tech.de",   "Inaktiv",     "red",     9800),
            ("Julia Weber",    "WebSolutions",    "j.weber@web.de",    "Aktiv",       "green",  61000),
        ], 1)
    ]
    return SDUIScreen(
        id="kunden",
        title="Kunden",
        root=_stack([
            _header("Kunden", "Alle Kunden und Kontakte"),
            _grid(3, [
                _stat("Gesamt",    "248", "up",   "+12 diese Woche"),
                _stat("Aktiv",     "201", "up",   "+8 diese Woche"),
                _stat("Inaktiv",   "47",  "down", "+4 diese Woche"),
            ]),
            _table(columns=cols, rows=rows),
        ]),
    )


def _build_deals() -> SDUIScreen:
    def _card(title: str, value: str, kunde: str, color: str = "blue") -> dict:
        return {
            "id": title.lower().replace(" ", "_"),
            "title": title,
            "tags": [
                {"label": value,  "color": color},
                {"label": kunde,  "color": "gray"},
            ],
        }

    return SDUIScreen(
        id="deals",
        title="Deals",
        root=_stack([
            _header("Deals", "Aktuelle Pipeline"),
            _grid(4, [
                _stat("Gesamt",          "34",     "up",   "+5 diese Woche"),
                _stat("Pipeline-Wert",   "€ 1.2M", "up",   "+8.4%"),
                _stat("Abschlussrate",   "68%",   "down", "-2%"),
                _stat("Ø Deal-Größe",    "€ 35k",  "up",   "+3%"),
            ]),
            SDUIComponent(
                type="pipeline_board",
                props={
                    "columns": [
                        {"id": "lead",     "title": "Lead",          "cards": [
                            _card("K\u00uhlanlage Upgrade", "€ 12.000", "Bauer GmbH"),
                            _card("Server Migration",     "€ 8.500",  "Tech AG"),
                        ]},
                        {"id": "kontakt",  "title": "Erstkontakt",   "cards": [
                            _card("ERP Einführung",   "€ 45.000", "Müller AG", "purple"),
                        ]},
                        {"id": "angebot",  "title": "Angebot",       "cards": [
                            _card("Netzwerk Ausbau",     "€ 23.000", "Klein & Co.", "yellow"),
                            _card("Cloud Migration",     "€ 67.000", "WebSolutions", "yellow"),
                        ]},
                        {"id": "verhandlung", "title": "Verhandlung", "cards": [
                            _card("Jahresvertrag 2025",  "€ 120.000", "Lange Consulting", "orange"),
                        ]},
                        {"id": "gewonnen", "title": "Gewonnen",     "cards": [
                            _card("IT-Support Paket",   "€ 18.000", "Schmidt Logistik", "green"),
                        ]},
                    ]
                },
            ),
        ]),
    )


# --- main config ------------------------------------------------------------

def build_sdui_config() -> SDUIConfig:
    return SDUIConfig(
        nav=[
            SDUINavItem("dashboard", "Dashboard", "layout-dashboard"),
            SDUINavItem("kunden",    "Kunden",    "users"),
            SDUINavItem("deals",     "Deals",     "trending-up"),
        ],
        screens=[
            _build_dashboard(),
            _build_kunden(),
            _build_deals(),
        ],
        defaultScreenId="dashboard",
    )


if __name__ == "__main__":
    config = build_sdui_config()
    print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))
