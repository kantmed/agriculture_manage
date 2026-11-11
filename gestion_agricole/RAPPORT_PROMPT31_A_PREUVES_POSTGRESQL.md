# RAPPORT PROMPT 31 — PREUVES POSTGRESQL EN LECTURE SEULE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Rôles existants

| Rôle | SUPERUSER | CREATEDB | CREATEROLE | LOGIN | Membre de |
|---|---|---|---|---|---|
| `odoo20` | non | oui | non | oui | aucun |
| `postgres` | oui | oui | oui | oui | (administrateur) |
| Rôles `pg_*` | non | non | non | non | rôles système |

Commande : `SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin FROM pg_roles;`

### 2. Privilèges sur les bases

| Base | Propriétaire | CONNECT | CREATE | TEMPORARY |
|---|---|---|---|---|
| `odoo20` | odoo20 | oui | oui | oui |
| `gest_agri_audit_test` | odoo20 | oui | oui | oui |
| `gest_agri_concurrency_test` | odoo20 | oui | oui | oui |

Commande : `SELECT datname, pg_get_userbyid(datdba), has_database_privilege(...) FROM pg_database;`

### 3. Privilèges sur les schémas (base odoo20)

| Schéma | Propriétaire | CREATE | USAGE |
|---|---|---|---|
| `public` | pg_database_owner | oui | oui |
| `information_schema` | postgres | non | oui |

### 4. Appartenances aux rôles

Le rôle `odoo20` n'est membre d'aucun autre rôle. Aucun privilège hérité.

### 5. Conclusion

Le rôle `odoo20` est propriétaire des trois bases et dispose des privilèges
CREATE, CONNECT et TEMPORARY sur chacune. Il n'y a pas de séparation des rôles
entre production et diagnostic.

---

*Rapport — Prompt 31 — Phase A — Module `gestion_agricole`.*
