# Byblos CRM v2 – Windows Fehlerbehebung

## Problem: WinError 32 (Datei wird von anderem Prozess verwendet)

**Ursache:** numpy oder andere Pakete sind noch in Verwendung.

**Lösung:**
1. Windows Task-Manager öffnen (Strg+Shift+Esc)
2. Tab "Prozesse" → alle `python.exe` und `pythonw.exe` beenden
3. Danach `INSTALL_WINDOWS_REPARIERT.bat` starten

Oder in PowerShell (als Admin):
```powershell
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "streamlit" -Force -ErrorAction SilentlyContinue
```

---

## Problem: "Could not install packages" (C++ Build Tools)

**Lösung:** Den reparierten Installer verwenden:
- `INSTALL_WINDOWS_REPARIERT.bat` (Doppelklick als Admin)

Er installiert nur Pakete die kein C++ brauchen.

---

## Problem: Python nicht gefunden

**Lösung:**
1. Python 3.11 herunterladen:  
   https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
2. Bei Installation: ✅ "Add Python 3.11 to PATH" anwählen!
3. Neues Kommandofenster öffnen
4. `python --version` testen

---

## Problem: Streamlit startet nicht

```bat
cd C:\Users\%USERNAME%\AppData\Local\ByblosCRM\app
pip install streamlit --upgrade
python -m streamlit run app.py
```

---

## Problem: Datenbank-Fehler beim Start

```bat
cd C:\Users\%USERNAME%\AppData\Local\ByblosCRM\app
python -c "import app; app.init_db(); print('OK')"
```

---

## Manueller Start (immer funktioniert)

```bat
cd C:\Users\%USERNAME%\AppData\Local\ByblosCRM\app
python -m streamlit run app.py --server.port=8501
```

Dann Browser: http://localhost:8501  
Login: admin / admin123

---

## Python 3.13 Hinweis

Python 3.13 kann Kompatibilitätsprobleme mit einigen Paketen haben.  
**Empfohlen: Python 3.11** verwenden:  
https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

Beide Versionen können parallel installiert sein. Der Installer erkennt automatisch welche verfügbar ist.
