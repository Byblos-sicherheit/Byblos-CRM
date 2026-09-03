# Open-Source-Lizenzen

Dieses Projekt steht selbst unter der MIT-Lizenz (siehe `LICENSE`) und verwendet die
folgenden Open-Source-Abhaengigkeiten (`pyproject.toml`). Fast alle Komponenten sind
permissiv lizenziert (MIT, BSD, Apache-2.0) und erlauben eine Nutzung in kommerzieller
Software ohne Offenlegung des eigenen Quellcodes. Eine Ausnahme ist die optionale
Abhaengigkeit `pikepdf` (siehe Hinweis unten).

## Kern-Abhaengigkeiten

| Paket | Lizenz |
|---|---|
| streamlit | Apache-2.0 |
| pandas | BSD-3-Clause |
| openpyxl | MIT |
| reportlab | BSD-3-Clause |
| qrcode | BSD-3-Clause |
| Pillow | MIT-CMU (HPND) |
| scikit-learn | BSD-3-Clause |
| cryptography | Apache-2.0 / BSD-3-Clause (dual) |
| fastapi | MIT |
| uvicorn | BSD-3-Clause |
| python-multipart | Apache-2.0 |
| requests | Apache-2.0 |
| psutil | BSD-3-Clause |

## Optionale Abhaengigkeiten

| Paket | Lizenz |
|---|---|
| pytesseract | Apache-2.0 |
| pdf2image | MIT |
| pikepdf | **MPL-2.0** (Mozilla Public License 2.0) |

## Hinweis zu MPL-2.0 (`pikepdf`)

MPL-2.0 ist eine schwache Copyleft-Lizenz: Aenderungen an MPL-lizenzierten Dateien selbst
muessen bei Weitergabe offengelegt werden, die Nutzung als Bibliothek erzwingt jedoch
**keine** Offenlegung des restlichen Anwendungscodes. Da `pikepdf` nur optional
(`pdf_embed`-Extra) eingebunden wird, betrifft dies ausschliesslich diesen Funktionsumfang.

Keine der Abhaengigkeiten unterliegt GPL/LGPL/AGPL. Bei neuen Abhaengigkeiten sollte vor
der Aufnahme die Lizenz geprueft werden (z. B. mit `pip-licenses`).
