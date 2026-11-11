# RAPPORT PROMPT 30 — CONFIGURATION DE DÉVELOPPEMENT

## Module `gestion_agricole` — Odoo 20 Community

### 1. Configuration proposée

Fichier : `/tmp/odoo20-dev-proposed.conf`

| Paramètre | Valeur proposée |
|---|---|
| `db_name` | `gest_agri_audit_test` |
| `dbfilter` | `^gest_agri_audit_test$` |
| `list_db` | `False` |
| `http_port` | `8072` |
| `data_dir` | `/tmp/opencode/dev/data` |
| `logfile` | `/tmp/opencode/dev/logs/odoo20-dev.log` |
| `log_level` | `info` |
| `db_user` | `gest_agri_dev` (proposé) |
| `db_password` | `<SECRET_A_CONFIGURER>` |

### 2. Vérification

- Port 8072 : libre (non écouté).
- `/tmp/opencode/dev/data` : à créer.
- `/tmp/opencode/dev/logs` : à créer.
- Secrets : masqués.

### 3. Conclusion

La configuration est proposée mais **non appliquée**. Le fichier modèle existe
et est prêt pour revue.

---

*Rapport — Prompt 30 — Phase F — Module `gestion_agricole`.*
