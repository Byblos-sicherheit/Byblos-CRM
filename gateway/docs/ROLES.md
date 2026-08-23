# Rollen- und Zugriffsmatrix

Das Gateway kennt nur „zugelassen“ oder „nicht zugelassen“. Fachliche Rollen
werden in LexAI-Pro, CRM, WKS-Pro und FileBrowser selbst verwaltet.

| Rolle | Gateway-Konfiguration | Benutzer anlegen/entfernen | Apps öffnen |
|---|---:|---:|---:|
| Server-Administrator | Ja | Ja | Ja |
| Zugelassener Benutzer | Nein | Nein | Ja |
| Nicht angemeldet | Nein | Nein | Nein |

Die Skripte verhindern das Entfernen des letzten aktiven Gateway-Benutzers.
