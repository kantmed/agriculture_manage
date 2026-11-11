# RAPPORT PROMPT N°32 — FINALISATION TECHNIQUE DE L'ISOLATION POSTGRESQL ET PROCÉDURE SÉCURISÉE DE CRÉATION DE `gest_agri_dev_db`

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. RÉSUMÉ EXÉCUTIF

| Élément | Statut |
|---|---|
| Audit PostgreSQL en lecture seule | ✅ effectué |
| Analyse de PUBLIC | ✅ effectuée (risque identifié) |
| Analyse de pg_hba.conf | ⚠️ fichier non lisible (permissions) |
| Comparaison des architectures | ✅ Option 2 recommandée |
| Propriété des objets | ✅ analysée |
| Privilèges par défaut | ✅ documentés |
| Procédure de sauvegarde | ✅ documentée |
| Procédure de restauration | ✅ documentée |
| Analyse btree_gist | ✅ disponible v1.8, non installé |
| Configuration Odoo proposée | ✅ documentée |
| Matrice de validation | ✅ préparée |
| Procédure de retour arrière | ✅ documentée |

**Verdict : B — PROCÉDURE TECHNIQUEMENT VALIDÉE, NON APPLIQUÉE.**

Aucune modification n'a été effectuée. Aucune écriture en production.

---

# 2. ÉTAT RÉEL VÉRIFIÉ

| Élément | Valeur |
|---|---|
| PostgreSQL | 18.6, port 5433 |
| Rôle `odoo20` | LOGIN, CREATEDB, non-SUPERUSER, non-CREATEROLE |
| Bases possédées par `odoo20` | `odoo20`, `gest_agri_audit_test`, `gest_agri_concurrency_test` |
| Appartenances de `odoo20` | aucune |
| `btree_gist` | disponible v1.8, non installé |
| pg_hba.conf | non lisible (mode 640 postgres:postgres) |
| Processus Odoo | PID 328398, port 8071, config `/etc/odoo20.conf` |

---

# 3. ÉCARTS PAR RAPPORT AU PROMPT 31

| Point | Prompt 31 | Prompt 32 |
|---|---|---|
| Privilèges PUBLIC | Mentionné | Analysé en détail (risque identifié) |
| pg_hba.conf | Non lu | Confirmé non lisible, proposition documentée |
| btree_gist | Disponible | Fichiers .so et .control vérifiés |
| Restauration | Procédure proposée | Propriété des objets explicitement traitée |
| Privilèges par défaut | Mentionnés | Analysés en détail avec `FOR ROLE` |

---

# 4. ANALYSE DES RÔLES

| Rôle | SUPERUSER | CREATEDB | CREATEROLE | LOGIN | Membre de |
|---|---|---|---|---|---|
| `odoo20` | non | oui | non | oui | aucun |
| `postgres` | oui | oui | oui | oui | administrateur |
| Rôles `pg_*` | non | non | non | non | rôles système |

Le rôle `odoo20` n'est membre d'aucun autre rôle. Aucun privilège hérité.

---

# 5. ANALYSE DES PRIVILÈGES PUBLIC

Dans PostgreSQL, certains privilèges sont accordés à PUBLIC par défaut :
- CONNECT sur les bases (par défaut)
- TEMPORARY sur les bases (par défaut)
- USAGE sur le schéma public (par défaut)

Le futur rôle `gest_agri_dev` pourrait hériter de ces privilèges même sans
GRANT explicite. Il faut examiner les ACL effectives après création du rôle.

**Attention** : `REVOKE CONNECT ON DATABASE odoo20 FROM PUBLIC;` n'a pas été
exécuté (pourrait affecter d'autres applications). C'est une opération
distincte nécessitant une autorisation explicite.

---

# 6. MATRICE DES PRIVILÈGES EFFECTIFS

| Base | Rôle | CONNECT | CREATE | TEMPORARY | Accès souhaité |
|---|---|---|---|---|---|
| `odoo20` | `odoo20` | oui | oui | oui | (production) |
| `odoo20` | `gest_agri_dev` (proposé) | **à refuser** | **à refuser** | **à refuser** | Aucun |
| `gest_agri_audit_test` | `odoo20` | oui | oui | oui | (diagnostic) |
| `gest_agri_audit_test` | `gest_agri_dev` (proposé) | **à refuser** | **à refuser** | **à refuser** | Aucun (si Option 2) |
| `gest_agri_dev_db` | `gest_agri_dev` (proposé) | **à autoriser** | **à autoriser** | **si nécessaire** | Développement |

---

# 7. ANALYSE DE PG_HBA.CONF

Le fichier `/etc/postgresql/18/main/pg_hba.conf` est en mode `640 postgres:postgres`.
L'utilisateur `kantmoh` ne peut pas le lire. La vue `pg_hba_file_rules` n'est
pas accessible (privilèges insuffisants).

Les règles effectives n'ont pas pu être vérifiées. C'est une limite documentée.

Proposition de règles (documentaire, non appliquée) :
- Règle spécifique pour `gest_agri_dev` → `gest_agri_dev_db` uniquement.
- Ne pas modifier les règles existantes sans analyse d'impact.

---

# 8. ARCHITECTURE CIBLE DU RÔLE `gest_agri_dev`

| Attribut | Valeur cible |
|---|---|
| LOGIN | Oui |
| SUPERUSER | Non |
| CREATEDB | Non |
| CREATEROLE | Non |
| REPLICATION | Non |
| BYPASSRLS | Non |
| INHERIT | À définir (justifier) |
| Memberships | Aucune par défaut |

Le rôle ne doit pas être membre de `odoo20` ni de `postgres`.

---

# 9. ARCHITECTURE CIBLE DE `gest_agri_dev_db`

Option 2 recommandée : créer une nouvelle base indépendante à partir de
`gest_agri_audit_test`.

Propriétaire : `gest_agri_dev`.

La restauration doit garantir que les objets applicatifs appartiennent au rôle
de développement. Utiliser `pg_restore --no-owner` et restaurer sous le rôle
`gest_agri_dev`.

---

# 10. PROCÉDURE DE SAUVEGARDE

1. Vérification de l'espace disque.
2. Vérification de la version de `pg_dump`.
3. Sauvegarde personnalisée (`pg_dump -Fc`).
4. Vérification de l'intégrité (`pg_restore --list`).
5. Calcul SHA256.
6. Conservation d'une copie protégée.

Source : `gest_agri_audit_test` uniquement. Jamais `odoo20`.

---

# 11. PROCÉDURE DE RESTAURATION ET PROPRIÉTÉ DES OBJETS

1. Création de `gest_agri_dev_db` avec propriétaire `gest_agri_dev`.
2. Restauration avec `pg_restore --no-owner --role=gest_agri_dev`.
3. Vérification des propriétaires de tous les objets.
4. Vérification des contraintes et index.
5. Vérification des séquences.
6. Vérification du filestore correspondant.

**Ne pas affirmer que `--role` suffit à garantir tous les propriétaires.**
Vérifier après restauration.

---

# 12. PROCÉDURE FILESTORE

- `data_dir` distinct : `/tmp/odoo20-dev-data`
- Filestore : `/tmp/odoo20-dev-data/filestore/gest_agri_audit_test/`
- Ne jamais copier le filestore de production.
- Vérifier la cohérence temporelle entre dump et filestore.
- Vérifier les pièces jointes `ir.attachment`.

---

# 13. ANALYSE BTREE_GIST

- Disponible : v1.8 (fichiers .so et .control présents dans `/usr/share/postgresql/18/extension/`)
- Non installé dans `odoo20` (0 dans `pg_extension`)
- Installé dans `gest_agri_audit_test` (1 dans `pg_extension`)
- Le rôle `gest_agri_dev` devra pouvoir créer l'extension (privilèges DBA
  nécessaires, car `CREATE EXTENSION` nécessite les droits du propriétaire de
  la base)

---

# 14. PRIVILÈGES PAR DÉFAUT

Commandes proposées (non exécutées) :

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gest_agri_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO gest_agri_dev;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO gest_agri_dev;
```

Les privilèges par défaut dépendent du rôle créateur. Si `gest_agri_dev` est
propriétaire et créateur de tous les objets, les privilèges supplémentaires
sont limités.

---

# 15. CONFIGURATION ODOO PROPOSÉE

Fichier : `/tmp/odoo20-dev-proposed.conf`

| Paramètre | Valeur |
|---|---|
| `db_name` | `gest_agri_audit_test` |
| `dbfilter` | `^gest_agri_audit_test$` |
| `list_db` | `False` |
| `http_port` | `8072` |
| `data_dir` | `/tmp/odoo20-dev-data` |
| `logfile` | `/tmp/odoo20-dev-logs/odoo20-dev.log` |
| `log_level` | `info` |
| `db_user` | `gest_agri_dev` |
| `db_password` | `<SECRET_A_CONFIGURER>` |

**Attention** : `db_name` et `dbfilter` ne remplacent pas les privilèges
PostgreSQL. `list_db = False` n'interdit pas toutes les connexions SQL.

---

# 16. MATRICE DE VALIDATION

| Test | Résultat attendu |
|---|---|
| Connexion `gest_agri_dev` à `gest_agri_dev_db` | Autorisée |
| Connexion `gest_agri_dev` à `odoo20` | Refusée |
| Connexion `gest_agri_dev` à `gest_agri_audit_test` | Refusée |
| Création de base par `gest_agri_dev` | Refusée |
| Création de rôle par `gest_agri_dev` | Refusée |
| SUPERUSER | Faux |
| BYPASSRLS | Faux |
| REPLICATION | Faux |

---

# 17. PROCÉDURE DE RETOUR ARRIÈRE

1. Ne jamais supprimer une base sans vérifier son identité.
2. Ne jamais supprimer un rôle qui possède encore des objets.
3. Ne jamais supprimer un répertoire sans vérifier son chemin exact.
4. Ne jamais modifier la configuration de production.
5. Ne jamais redémarrer le serveur PostgreSQL ou Odoo sans autorisation.
6. Conserver les preuves avant/après.

---

# 18. COMMANDES EXACTES À EXÉCUTER ULTÉRIEUREMENT

Les commandes SQL et shell nécessaires sont documentées dans les rapports
précédents (Prompts 30-31). Elles ne sont pas exécutées dans ce prompt.

---

# 19. RISQUES ET POINTS BLOQUANTS

| Risque | Niveau | Détail |
|---|---|---|
| Accès indirect via PUBLIC | Moyen | À vérifier après création du rôle |
| Propriété des objets restaurés | Moyen | `--no-owner` + vérification post-restauration |
| btree_gist installation | Moyen | Nécessite des droits DBA |
| Filestore cohérence | Moyen | Sauvegarde PostgreSQL + filestore synchronisés |
| pg_hba.conf non lisible | Faible | Nécessite un accès DBA |

---

# 20. DÉCISION FINALE

**VERDICT B — PROCÉDURE TECHNIQUEMENT VALIDÉE, NON APPLIQUÉE.**

La stratégie d'isolation est cohérente, mais aucune opération n'a été exécutée.

### Ce qui est prouvé

- Rôle `odoo20` : LOGIN, CREATEDB, non-SUPERUSER, non-CREATEROLE.
- Bases possédées par `odoo20` : `odoo20`, `gest_agri_audit_test`, `gest_agri_concurrency_test`.
- `btree_gist` disponible v1.8 sur le serveur.
- Processus Odoo : PID 328398, port 8071, config `/etc/odoo20.conf`.

### Ce qui est seulement proposé

- Rôle `gest_agri_dev` (commandes SQL documentées, non exécutées).
- Base `gest_agri_dev_db` (procédure documentée, non exécutée).
- Configuration de développement (fichier modèle, non appliqué).
- Isolation complète (non démontrée).

### Ce qui reste inconnu

- Contenu exact de `pg_hba.conf`.
- Privilèges effectifs de PUBLIC sur les bases.
- Origine de la modification de `write_date`.

### Ce qui nécessite l'intervention du DBA

- Création du rôle `gest_agri_dev`.
- Installation de `btree_gist` dans `gest_agri_dev_db`.
- Vérification de `pg_hba.conf`.
- Vérification des privilèges de PUBLIC.

### Ce qui nécessite l'autorisation du propriétaire du système

- Création de la base `gest_agri_dev_db`.
- Restauration de la sauvegarde.
- Lancement du serveur de développement.
- Modification des règles HBA.

### Opérations interdites tant que cette autorisation n'est pas donnée

- Création de rôle ou de base.
- Installation d'extension.
- Modification de privilèges.
- Modification de configuration.
- Lancement de serveur.
- Modification du code.

---

*Rapport — Prompt N°32 — Module `gestion_agricole` — Odoo 20 Community.
Aucune modification, création, restauration, installation, suppression ou
activation n'a été autorisée ou exécutée.*
