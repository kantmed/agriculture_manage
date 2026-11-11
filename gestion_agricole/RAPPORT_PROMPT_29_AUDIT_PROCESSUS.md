# RAPPORT PROMPT N°29 — AUDIT DES PROCESSUS ODOO

## Module `gestion_agricole` — Odoo 20 Community

### 1. Processus Odoo actifs

| PID | Utilisateur | Commande | Config | Port |
|---|---|---|---|---|
| 766 | odoo16 | `/mnt/srv/share/odoo16/venv/bin/python3.11 /mnt/srv/share/odoo16/odoo/odoo-bin -c /etc/odoo16.conf` | odoo16 | (non vérifié) |
| 328398 | kantmoh | `python odoo-bin -c /etc/odoo20.conf` | `/etc/odoo20.conf` | 8071 |

### 2. Connexions PostgreSQL du processus 328398

Le processus Odoo 20 (PID 328398) est connecté aux bases suivantes :
- `odoo20` (production) — connexions multiples
- `gest_agri_audit_test` (diagnostic)
- `gest_agri_concurrency_test` (diagnostic)
- `adoo20`
- `odoo2000`

### 3. Conclusion

L'instance Odoo 20 actuelle dessert **simultanément** la production et les bases
de diagnostic. Il n'y a pas d'isolation au niveau processus.

L'ancien PID de production (314241) n'est plus actif, mais le processus actuel
(328398) est connecté à `odoo20` (production) via PostgreSQL.

### 4. Risque

Toute modification du code source dans le répertoire partagé pourrait être
chargée par ce processus, affectant la production.

**Isolation : NON DÉMONTRÉE.**

---

*Rapport — Prompt N°29 — Phase A — Module `gestion_agricole`.*
