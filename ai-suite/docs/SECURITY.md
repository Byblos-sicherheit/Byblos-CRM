# Sicherheitskonzept

## Bereits umgesetzt

- Kein `OPENAI_API_KEY` oder `GEMINI_API_KEY` im Android-Projekt.
- HTTPS-Pflicht für Release-Builds und Build-Abbruch bei Platzhalter-URL.
- Eingabevalidierung, Payloadlimit, Timeouts und Parallelitätsgrenze in beiden Backends.
- CORS-Allowlist für Browser-Clients; native Android-Anfragen benötigen CORS technisch nicht.
- Pseudonyme Installations-ID wird im OpenAI-Backend vor Übergabe an den Provider per SHA-256 gehasht.
- OpenAI-Anfragen werden mit `store: false` erstellt.
- Keine Protokollierung von Prompts oder Modellantworten.
- Docker-Prozesse laufen als nicht privilegierte Benutzer.
- Secret-Scan im lokalen Prüfskript.
- Antigravity-Backend stellt dem Modell ausschließlich das `finish`-Werkzeug bereit.
- Shell, Dateizugriff, Webzugriff, MCP, Bildgenerierung und Subagenten sind im Antigravity-Profil deaktiviert.
- Skills werden aus explizit konfigurierten absoluten Verzeichnissen geladen; jedes Verzeichnis muss eine `SKILL.md` enthalten.

## Vertrauensgrenzen

1. **Android-Gerät:** vollständig als potenziell kompromittiert behandeln. Keine langfristigen Servergeheimnisse dort speichern.
2. **Backend:** einzige Komponente mit Provider-Credentials und Durchsetzungslogik.
3. **Modell/Agent:** Modellantworten und Toolvorschläge sind nicht vertrauenswürdig und dürfen keine Autorisierung ersetzen.
4. **Skill-Dateien:** als ausführbare Steuerungsanweisungen behandeln. Nur geprüfte, versionierte Skills deployen.
5. **Provider:** Datenübertragung, Speicherregeln, Region und Vertragslage vor Produktion rechtlich und technisch prüfen.

## Vor öffentlicher Veröffentlichung zwingend

1. OIDC-/OAuth2-basierte Anmeldung oder ein gleichwertiges Identitätssystem einführen.
2. Access Tokens serverseitig verifizieren; keine statischen Geheimnisse im APK als Vertrauensanker verwenden.
3. Rate Limits und Quoten in Redis oder einer Datenbank je Benutzer/Mandant speichern.
4. Secret Manager statt lokaler `.env`-Datei in Produktion verwenden.
5. Reverse Proxy/WAF, TLS, DDoS-Schutz, zentrale Logs, Alarmierung und Kostenlimits konfigurieren.
6. Datenschutz-Folgen prüfen: Rechtsgrundlage, Auftragsverarbeitung, Löschfristen, Betroffenenrechte und Datenübermittlungen.
7. Missbrauchstests, Dependency Scans, SAST und Penetrationstest vor öffentlichem Rollout durchführen.
8. Für jedes neue Agentenwerkzeug eine explizite Allowlist, Eingabevalidierung, Audit-Logs und Human-in-the-loop-Freigabe definieren.
9. Antigravity-PyPI-Wheel, Runtime-Binärdatei und exakte Version in CI mit Prüfsummen beziehungsweise vertrauenswürdigem Artefakt-Repository fixieren.

## Nicht behaupten

Root-Erkennung, Play Integrity oder Obfuskation beweisen keine Vertrauenswürdigkeit eines Geräts. Sie können nur zusätzliche Risikosignale liefern. Eine im APK enthaltene Zeichenfolge bleibt trotz R8 extrahierbar. Ein grüner Fake-Provider-Test beweist außerdem nicht, dass ein echter Providerzugriff oder die plattformspezifische Antigravity-Runtime funktioniert.
