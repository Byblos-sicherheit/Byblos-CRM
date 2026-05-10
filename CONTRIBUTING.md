# 🤝 Beitragen zu Byblos CRM

Danke, dass du zu Byblos CRM beitragen möchtest! 🎉

## Arten von Beiträgen

### 🐛 Bugs melden
1. [GitHub Issues](https://github.com/byblos-security/byblos-crm/issues) öffnen
2. Template ausfüllen: Beschreibung, Schritte zum Reproduzieren, erwartetes Verhalten
3. Python-Version und Betriebssystem angeben

### 💡 Feature-Ideen
1. [GitHub Discussions](https://github.com/byblos-security/byblos-crm/discussions) → "Ideas"
2. Beschreibe den Anwendungsfall
3. Community-Feedback abwarten

### 🔧 Code beitragen (Pull Request)

```bash
# 1. Repository forken (GitHub: Fork-Button)

# 2. Lokal klonen
git clone https://github.com/DEIN-USERNAME/byblos-crm.git
cd byblos-crm

# 3. Virtuelle Umgebung
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# 4. Abhängigkeiten
pip install -r byblos_crm_app/requirements.txt
pip install pytest

# 5. Feature-Branch erstellen
git checkout -b feature/mein-tolles-feature

# 6. Entwickeln & testen
cd byblos_crm_app
streamlit run app.py  # Lokal testen

# 7. Tests ausführen
cd ..
pytest tests/ -v

# 8. Commit & Push
git add .
git commit -m "feat: Beschreibung des Features"
git push origin feature/mein-tolles-feature

# 9. Pull Request auf GitHub erstellen
```

## Code-Stil

- **Sprache:** Deutsch für UI-Texte, Englisch für Variablen/Kommentare
- **Format:** PEP 8, max. 120 Zeichen pro Zeile
- **Docstrings:** Kurzform für alle öffentlichen Funktionen
- **Tests:** Neue Features brauchen Unit-Tests in `tests/test_byblos_crm.py`

### Neues Modul anlegen

```python
# extensions_v2_mein_modul.py
"""
extensions_v2_mein_modul.py – Kurzbeschreibung
================================================
1. Feature A
2. Feature B
"""

def register_mein_modul(run_fn, df_fn) -> None:
    """DB-Tabellen erstellen."""
    run_fn("""CREATE TABLE IF NOT EXISTS ...""")

def page_mein_feature(run_fn, df_fn) -> None:
    """Streamlit-Seite rendern."""
    import streamlit as st
    st.title("Mein Feature")
    # ...
```

### Route in app.py registrieren

```python
# In init_db():
try:
    from extensions_v2_mein_modul import register_mein_modul
    register_mein_modul(run, df)
except Exception:
    pass

# In SECTIONS:
"Meine Gruppe": ["Mein Feature"],

# Im Router:
elif page == "Mein Feature":
    try:
        from extensions_v2_mein_modul import page_mein_feature
        page_mein_feature(run, df)
    except Exception as e:
        st.error(f"Fehler: {e}")
```

## Commit-Konventionen

```
feat:     Neues Feature
fix:      Bugfix
docs:     Dokumentation
test:     Tests hinzufügen/ändern
refactor: Code-Umbau ohne neue Features
perf:     Performance-Verbesserung
chore:    Sonstiges (Dependencies, Config)
```

## Prioritäten für Beiträge

🔴 **Hoch (Bugs):** Installer-Fehler, Datenverlust, Absturz  
🟡 **Mittel:** UI-Verbesserungen, fehlende Validierungen  
🟢 **Niedrig:** Neue Features, optionale Integrationen

## Fragen?

→ [GitHub Discussions](https://github.com/byblos-security/byblos-crm/discussions)  
→ Schreibe ein Issue mit Label `question`
