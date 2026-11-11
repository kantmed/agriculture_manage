# RAPPORT PROMPT N°29 — JOURNALISATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. État actuel

- `logfile` absent (stdout du processus)
- `log_level` = info
- Rotation : aucune
- PostgreSQL : `log_statement = none`, `logging_collector = off`
- Aucun journal exploitable

### 2. Proposition

- Odoo : `logfile = /var/log/odoo/odoo20.log`, rotation logrotate (30 j)
- PostgreSQL : `log_statement = 'ddl'`, `log_connections = on`,
  `log_disconnections = on`, `log_min_duration_statement = 500`
- Accès : ajouter `kantmoh` au groupe `postgres` (lecture seule)

### 3. Risques

- Exposition de données personnelles dans les logs.
- Risque de perte de lignes pendant la rotation (`copytruncate`).
- Permissions du groupe PostgreSQL à surveiller.

### 4. Statut

Non appliqué. Proposition documentée.

---

*Rapport — Prompt N°29 — Phase H — Module `gestion_agricole`.*
