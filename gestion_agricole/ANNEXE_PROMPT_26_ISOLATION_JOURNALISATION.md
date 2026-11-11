# ANNEXE 7 — ISOLATION ET JOURNALISATION

## Isolation actuelle

- PID Odoo 20 : 328398, port 8071, config `/etc/odoo20.conf`
- `db_name` vide, `dbfilter` vide, `list_db = True`
- L'instance dessert toutes les bases (`odoo20`, `gest_agri_audit_test`,
  `gest_agri_concurrency_test`, `adoo20`, `odoo2000`)

## Architecture cible proposée

### Production
- `db_name = odoo20`, `dbfilter = ^odoo20$`, `list_db = False`
- Port 8071, `data_dir = /var/lib/odoo`
- Journalisation dédiée

### Diagnostic
- `db_name = gest_agri_audit_test`, `dbfilter = ^gest_agri_audit_test$`
- Port 8072, `data_dir = /var/lib/odoo20-test`
- Journalisation dédiée, processus distinct

## Fichiers modèles

- `/tmp/odoo20-production-proposed.conf` (SHA256: `8c534760...`)
- `/tmp/odoo20-test-proposed.conf` (SHA256: `09f838b2...`)

Non appliqués.

## Journalisation actuelle

- `logfile` absent (stdout), `log_level = info`
- PostgreSQL : `log_statement = none`, `logging_collector = off`,
  `log_connections = off`, `log_disconnections = off`,
  `log_min_duration_statement = -1`
- Aucun journal exploitable

## Proposition

- Odoo : `logfile = /var/log/odoo/odoo20.log`, rotation logrotate (30 j)
- PostgreSQL : `log_statement = 'ddl'`, `log_connections = on`,
  `log_disconnections = on`, `log_min_duration_statement = 500`
- Accès : ajouter `kantmoh` au groupe `postgres` (lecture seule)

Non appliquée.
