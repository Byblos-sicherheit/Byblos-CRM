# Finance & Time Ops Erweiterung

Diese Erweiterung ergänzt die Module E-Rechnung und Zeiterfassung um operative Abläufe für den echten Tagesbetrieb.

## Neu enthalten

- Zahlungsbuchungen je Rechnung
- Teilzahlungen und vollständige Zahlung
- Zahlungsstatus: offen, teilbezahlt, bezahlt, überfällig
- Mahnvorschläge nach Fälligkeit
- Mahn-Entwürfe in einer E-Mail-Outbox
- Versand-Entwürfe für Rechnungen
- Plausibilitätsprüfung für E-Rechnungen
- Prüfhinweise zu Pflichtfeldern
- Käuferreferenz / Leitweg-ID als Prüffeld
- Zeitfreigabe per ID-Auswahl
- Freigabe-Batches pro Kunde und Zeitraum
- Abrechnungsläufe aus freigegebenen Zeiten
- CSV-Exporte für offene Rechnungen und Zeiten

## Wichtige Wahrheit

Die XRechnung-Prüfung in diesem Paket ist eine Plausibilitätsprüfung. Sie ist kein offizieller EN-16931-Validator und ersetzt keine rechtliche oder steuerliche Prüfung.

Für produktive E-Rechnungen muss der XML-Export mit einem gültigen XRechnung-/EN-16931-Validator geprüft oder durch eine spezialisierte Bibliothek erzeugt werden.

## Neuer Seitenbereich im CRM

- E-Rechnung Prüfung
- Zahlungen & Mahnwesen
- Zeiten freigeben

## Empfohlener Ablauf

1. Rechnung erstellen.
2. Rechnungsdaten prüfen.
3. E-Rechnung-Plausibilitätscheck ausführen.
4. XML/PDF erzeugen.
5. Versand-Entwurf erstellen.
6. Zahlungseingang buchen.
7. Offene Rechnungen regelmäßig über Mahnwesen prüfen.
8. Zeiten erfassen.
9. Zeiten freigeben.
10. Freigabe-Batch erstellen.
11. Abrechnungslauf vorbereiten.

## Nächster produktiver Schritt

- echter XRechnung-/ZUGFeRD-Generator
- Validator-Integration
- SMTP-Versand nach Freigabe
- DATEV-/Steuerberater-Export
- SEPA-Lastschriftmandate
- GoBD-konforme Unveränderbarkeit prüfen
