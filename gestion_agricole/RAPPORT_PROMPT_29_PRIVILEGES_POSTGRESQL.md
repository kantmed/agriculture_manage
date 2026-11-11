# RAPPORT PROMPT N°29 — PRIVILÈGES POSTGRESQL

## Module `gestion_agricole` — Odoo 20 Community

### 1. Rôle utilisé par Odoo

- Rôle : `odoo20`
- LOGIN : oui
- SUPERUSER : non (vérifié)
- CREATEDB : oui (probable, à vérifier)
- CREATEROLE : non (probable)

### 2. Privilèges sur les bases

Le rôle `odoo20` est propriétaire des bases `odoo20`, `gest_agri_audit_test`,
`gest_agri_concurrency_test`. En tant que propriétaire, il a tous les privilèges
(CREATE, CONNECT, TEMPORARY) sur ces bases.

### 3. Conclusion

Le rôle `odoo20` peut écrire dans `odoo20` (production). Il n'y a pas de
séparation des rôles entre production et diagnostic.

**Isolation PostgreSQL : NON DÉMONTRÉE.**

Une isolation stricte nécessiterait un rôle dédié au développement avec des
privilèges limités à `gest_agri_audit_test`.

---

*Rapport — Prompt N°29 — Phase B — Module `gestion_agricole`.*
