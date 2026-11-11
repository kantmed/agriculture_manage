# RAPPORT PROMPT 30 — JOURNALISATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. État actuel

- `logfile` absent (stdout du processus)
- `log_level` = info
- Rotation : aucune
- PostgreSQL : `log_statement = none`, `logging_collector = off`

### 2. Proposition

- Odoo : `logfile = /tmp/opencode/dev/logs/odoo20-dev.log`, rotation logrotate
- PostgreSQL : `log_statement = 'ddl'`, `log_connections = on`,
  `log_disconnections = on`, `log_min_duration_statement = 500`
- Accès : pas d'ajout de `kantmoh` au groupe `postgres`

### 3. Risques

- Exposition de données personnelles dans les logs.
- Risque de perte de lignes pendant la rotation.
- Permissions du groupe PostgreSQL à surveiller.

### 4. Conclusion

Non appliqué. Proposition documentée.

---

*Rapport — Prompt 30 — Phase G — Module `gestion_agricole`.*
