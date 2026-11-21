"""CRM Stufe 5: Rollen vereinheitlichen und Menübereiche nach tatsächlicher Rolle freigeben.

Grundsatz: Was nicht ausdrücklich freigegeben ist, sieht nur Inhaber/Admin.
"""

ADMIN = "Inhaber/Admin"
ROLES = (ADMIN, "Buchhaltung", "Einsatzleitung", "Vertrieb", "Mitarbeiter", "Kunde/Portal")

# Im Code existieren mehrere alte Rollennamen; sie werden auf die Rollen der Rechte-Matrix abgebildet.
# Unbekannte Rollen bekommen die geringsten Rechte (Mitarbeiter).
ROLE_ALIASES = {
    "admin": ADMIN, "administrator": ADMIN, "inhaber/admin": ADMIN, "inhaber": ADMIN,
    "buchhaltung": "Buchhaltung", "buchhalter": "Buchhaltung", "büro": "Buchhaltung",
    "einsatzleitung": "Einsatzleitung", "disposition": "Einsatzleitung", "manager": "Einsatzleitung",
    "vertrieb": "Vertrieb",
    "mitarbeiter": "Mitarbeiter", "user": "Mitarbeiter", "lesen": "Mitarbeiter", "readonly": "Mitarbeiter",
    "kunde/portal": "Kunde/Portal", "kunde": "Kunde/Portal",
}

FIN, OPS, SALES, STAFF = "Buchhaltung", "Einsatzleitung", "Vertrieb", "Mitarbeiter"

# Bereich (Schlüssel aus SECTIONS in app.py) -> Rollen außer Inhaber/Admin, die ihn sehen dürfen.
SECTION_ROLES = {
    "📊 Übersicht": {FIN},
    "👥 CRM": {FIN, OPS, SALES},
    "💰 Finanzen": {FIN},
    "📋 Angebote": {FIN, SALES},
    "🚚 Lieferanten": {FIN},
    "🔄 Dauerrechnungen": {FIN},
    "🏖️ Personal Plus": {OPS},
    "📊 SLA & Projekte": {OPS, SALES},
    "🏦 DATEV & Steuern": {FIN},
    "💶 Lohn & Berichte": {FIN},
    "🎓 Qualifikationen": {OPS},
    "🧮 Kalkulation": {FIN},
    "📄 Dokumente": {FIN},
    "📁 Projektrechnungen": {FIN},
    "🖨️ Druck & Ansicht": {OPS},
    "👷 Mitarbeiterportal": {FIN, OPS, SALES, STAFF},
    "📍 GPS & Stempel": {OPS, STAFF},
    "⚠️ Mahnwesen Plus": {FIN},
    "❌ Storno": {FIN},
    "⏱️ Überstunden": {FIN},
    "💼 Minijobler": {FIN},
    "📋 Verträge Plus": {FIN, SALES},
    "📊 Vergleich": {FIN},
    "✉️ Serienbriefe": {SALES},
    "🏢 Objekte & Wachbuch": {OPS},
    "📒 Buchhaltung Plus": {FIN},
    "💧 Liquidität": {FIN},
    "📦 Lieferschein": {FIN},
    "📋 Schicht-Vorlagen": {OPS},
    "💼 Personalanalyse": {FIN},
    "🏗️ Field-Ops": {OPS},
    "⏱️ Zeit & Personal": {FIN, OPS},
    "✉️ Kommunikation": {FIN, SALES},
    "🛡️ Sicherheit": {FIN, OPS, SALES, STAFF},  # nur eigene 2FA (Stufe 8)
}


def canonical_role(role):
    """Rollenname aus der Datenbank auf eine der ROLES abbilden; unbekannt -> Mitarbeiter."""
    if not role:
        return STAFF
    return ROLE_ALIASES.get(str(role).strip().lower(), STAFF)


def can_access_section(role, section):
    role = canonical_role(role)
    return role == ADMIN or role in SECTION_ROLES.get(section, set())


def allowed_sections(role, sections):
    """Nur die Bereiche aus sections (dict Bereich -> Seiten), die die Rolle sehen darf."""
    return {name: pages for name, pages in sections.items() if can_access_section(role, name)}


def can_access_page(role, sections, page):
    """True, wenn die Seite in mindestens einem für die Rolle freigegebenen Bereich liegt."""
    return any(page in pages for pages in allowed_sections(role, sections).values())
