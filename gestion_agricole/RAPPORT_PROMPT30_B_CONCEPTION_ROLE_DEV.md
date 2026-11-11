# RAPPORT PROMPT 30 — CONCEPTION DU RÔLE DE DÉVELOPPEMENT

## Module `gestion_agricole` — Odoo 20 Community

### 1. Rôle proposé : `gest_agri_dev`

| Attribut | Valeur proposée |
|---|---|
| LOGIN | oui |
| SUPERUSER | non |
| CREATEDB | non |
| CREATEROLE | non |
| REPLICATION | non |
| BYPASSRLS | non |

### 2. Matrice des privilèges

| Privilège | Base `gest_agri_audit_test` | Base `odoo20` |
|---|---|---|
| CONNECT | oui | **non** |
| CREATE | oui | **non** |
| TEMPORARY | oui | **non** |
| CREATE (schéma public) | oui | **non** |
| USAGE (schéma public) | oui | **non** |

### 3. Commandes SQL proposées (non exécutées)

```sql
-- Création du rôle (nécessite des droits administrateur PostgreSQL)
CREATE ROLE gest_agri_dev WITH LOGIN PASSWORD '<SECRET_A_CONFIGURER>'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

-- Privilèges sur la base de diagnostic
GRANT CONNECT, TEMPORARY ON DATABASE gest_agri_audit_test TO gest_agri_dev;

-- Privilèges sur le schéma
GRANT USAGE, CREATE ON SCHEMA public TO gest_agri_dev;

-- Privilèges par défaut pour les futurs objets
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gest_agri_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO gest_agri_dev;
```

### 4. Conclusion

Le rôle `gest_agri_dev` doit être créé par un administrateur PostgreSQL.
Il ne doit pas avoir de privilèges sur `odoo20`. Les commandes ci-dessus sont
proposées, non exécutées.

---

*Rapport — Prompt 30 — Phase B — Module `gestion_agricole`.*
