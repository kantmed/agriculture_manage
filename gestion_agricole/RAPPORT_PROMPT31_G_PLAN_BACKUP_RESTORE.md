# RAPPORT PROMPT 31 — PLAN DE SAUVEGARDE ET RESTAURATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. Plan de sauvegarde de `gest_agri_audit_test`

1. Vérification de l'espace disque (`df -h`).
2. Vérification de la version de `pg_dump` (`pg_dump --version`).
3. Sauvegarde personnalisée (`pg_dump -Fc`).
4. Vérification de l'intégrité de l'archive (`pg_restore --list`).
5. Inventaire des objets sauvegardés.
6. Analyse des propriétaires.
7. Analyse des extensions (`btree_gist`).

### 2. Plan de restauration

1. Création de la base de développement (`createdb`).
2. Restauration (`pg_restore`).
3. Vérification des objets restaurés.
4. Vérification des contraintes.
5. Vérification des index.
6. Vérification des séquences.
7. Vérification du filestore correspondant.

### 3. Commandes proposées (non exécutées)

```bash
pg_dump -Fc -U odoo20 -h 127.0.0.1 -p 5433 gest_agri_audit_test > /tmp/opencode/dev/backup_gest_agri_audit_test.dump
pg_restore --list /tmp/opencode/dev/backup_gest_agri_audit_test.dump | head
```

---

*Rapport — Prompt 31 — Phase G — Module `gestion_agricole`.*
