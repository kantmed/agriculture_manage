# RAPPORT PROMPT 31 — PRIVILÈGES PAR DÉFAUT

## Module `gestion_agricole` — Odoo 20 Community

### 1. Fonctionnement de ALTER DEFAULT PRIVILEGES

`ALTER DEFAULT PRIVILEGES` définit les privilèges accordés aux futurs objets
créés par un rôle spécifié. Les privilèges s'appliquent au rôle créateur
des objets, pas au rôle qui exécute la commande.

### 2. Commandes proposées (non exécutées)

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gest_agri_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO gest_agri_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO gest_agri_dev;
```

### 3. Limites

Les privilèges par défaut ne s'appliquent qu'aux objets créés après
l'exécution de la commande. Les objets existants ne sont pas affectés.

---

*Rapport — Prompt 31 — Phase F — Module `gestion_agricole`.*
