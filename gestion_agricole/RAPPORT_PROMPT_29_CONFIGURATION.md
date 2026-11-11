# RAPPORT PROMPT N°29 — CONFIGURATION ODOO DE DÉVELOPPEMENT

## Module `gestion_agricole` — Odoo 20 Community

### 1. Configuration proposée

Fichier modèle : `/tmp/odoo20-test-proposed.conf` (créé au Prompt 22)

| Paramètre | Valeur proposée |
|---|---|
| `db_name` | `gest_agri_audit_test` |
| `dbfilter` | `^gest_agri_audit_test$` |
| `list_db` | `True` |
| `http_port` | `8072` |
| `data_dir` | `/var/lib/odoo20-test` |
| `logfile` | `/var/log/odoo20-test/odoo20-test.log` |
| `log_level` | `info` |

### 2. Vérification

- Port 8072 : libre (non écouté)
- `/var/lib/odoo20-test` : à créer
- `/var/log/odoo20-test` : à créer
- Secrets : masqués (`<SECRET_A_CONFIGURER>`)

### 3. Conclusion

La configuration est proposée mais **non appliquée**. Le fichier modèle existe
et est prêt pour revue.

---

*Rapport — Prompt N°29 — Phase D — Module `gestion_agricole`.*
