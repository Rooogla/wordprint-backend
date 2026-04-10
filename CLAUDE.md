# CLAUDE.md – Arbeitsregeln für dieses Repository

## Commits
- Nach **jedem abgeschlossenen Arbeitsschritt** wird ein Commit gemacht – nicht erst am Ende.
- Commit-Message im Format: `type(scope): kurze Beschreibung` (Conventional Commits).
- Beispiele: `feat(nlp): add lemmatization pipeline`, `fix(api): correct 404 on missing analysis`
- Kein Rückfragen, ob ein Commit gemacht werden soll – er wird immer gemacht.

## Docker
- Wenn sich `requirements.txt`, `package.json`, `Dockerfile` oder `docker-compose.yml` ändern:
  Docker **eigenständig neu bauen und neu starten** (`docker compose up --build -d`).
- Wenn ein Service nach einer Codeänderung nicht mehr korrekt antwortet:
  Container eigenständig neu starten (`docker compose restart <service>`).
- Kein Rückfragen, ob Docker neu gestartet werden soll – eigenständig entscheiden und handeln.

## Allgemein
- Fehler werden eigenständig analysiert und behoben, bevor der nächste Schritt beginnt.
- Lauffähigkeit nach jeder Änderung prüfen (zumindest Health-Check oder Smoke-Test).
- Kein Schritt bleibt halb fertig.
