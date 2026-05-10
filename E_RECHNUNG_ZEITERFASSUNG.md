# Erweiterung: E-Rechnung und Zeiterfassung

## Enthalten

- automatische Rechnungsnummerierung nach Muster `BY-JAHR-NUMMER`
- Rechnungserstellung direkt im CRM
- Zahlungsmethoden-Verwaltung
- Rechnungsvorlagen-Verwaltung
- CSV-Export pro Rechnung
- XML-Entwurf für strukturierte E-Rechnung
- Exportprotokoll mit SHA-256-Prüfsumme
- Zeiterfassung je Mitarbeiter/Kunde/Leistung
- Pausenberechnung
- Freigabe von Zeiten
- Rechnungserstellung aus abrechenbaren Zeiten
- CSV-Export der Zeiterfassung

## Wichtiger Hinweis zur XRechnung

Der XML-Export ist als technischer Entwurf markiert. Für eine produktive E-Rechnung muss die XML gegen EN 16931/XRechnung validiert werden. Vor produktiver Nutzung ist ein echter XRechnung/ZUGFeRD-Validator oder eine spezialisierte Bibliothek einzubinden.

## Rechtlicher Stand

Seit 1. Januar 2025 müssen Unternehmen in Deutschland im B2B-Bereich strukturierte E-Rechnungen empfangen können. Die Ausstellungspflicht wird über Übergangsfristen schrittweise eingeführt. PDFs allein gelten nicht als strukturierte E-Rechnung.

## Nächster technischer Schritt

Für echte Konformität sollte ergänzt werden:

- UBL/CII-konformer XRechnung-Generator
- EN-16931-Validator
- ZUGFeRD-Export
- Leitweg-ID-Feld für öffentliche Auftraggeber
- Peppol-/E-Mail-Versandlogik
- revisionssichere Archivierung der XML-Dateien
