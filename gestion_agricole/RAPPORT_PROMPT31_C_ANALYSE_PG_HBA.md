# RAPPORT PROMPT 31 — ANALYSE DE PG_HBA.CONF

## Module `gestion_agricole` — Odoo 20 Community

### 1. Accès au fichier

Le fichier `/etc/postgresql/18/main/pg_hba.conf` est en mode `640 postgres:postgres`.
L'utilisateur `kantmoh` ne peut pas le lire directement. La vue
`pg_hba_file_rules` n'est pas accessible (privilèges insuffisants).

### 2. Règles observées (via les connexions actives)

Les connexions PostgreSQL actives montrent :
- Connexions TCP depuis 127.0.0.1 (methode d'authentification non visible)
- Connexions locales (unix socket)

### 3. Conclusion

Le contenu exact de `pg_hba.conf` n'a pas pu être lu avec les privilèges
actuels. Les règles ne peuvent pas être vérifiées directement.

**Limite** : analyse incomplète. Nécessite un accès DBA ou la vue
`pg_hba_file_rules` avec des privilèges suffisants.

---

*Rapport — Prompt 31 — Phase C — Module `gestion_agricole`.*
