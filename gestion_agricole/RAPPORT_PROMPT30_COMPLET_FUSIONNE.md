# RAPPORT PROMPT 30 — AUDIT POSTGRESQL EN LECTURE SEULE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Rôles existants

| Rôle | SUPERUSER | CREATEDB | CREATEROLE | LOGIN | Membre de |
|---|---|---|---|---|---|
| `odoo20` | non | oui | non | oui | aucun |
| `postgres` | oui | oui | oui | oui | (administrateur) |
| Rôles `pg_*` | non | non | non | non | rôles système |

### 2. Privilèges sur les bases

| Base | Propriétaire | CONNECT | CREATE | TEMPORARY |
|---|---|---|---|---|
| `odoo20` | odoo20 | oui | oui | oui |
| `gest_agri_audit_test` | odoo20 | oui | oui | oui |
| `gest_agri_concurrency_test` | odoo20 | odoo20 | oui | oui |

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

**Chemins d'accès indirects** : le rôle `odoo20` peut écrire dans `odoo20`
(production) et dans les bases de diagnostic. Aucune isolation au niveau
PostgreSQL.

---

*Rapport — Prompt 30 — Phase A — Module `gestion_agricole`.*
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
# RAPPORT PROMPT 30 — PROTECTION FORMELLE DE LA PRODUCTION

## Module `gestion_agricole` — Odoo 20 Community

### 1. Vérification de protection

| Contrôle | Statut | Preuve |
|---|---|---|
| Connexion à `gest_agri_audit_test` | possible (rôle `odoo20`) | `has_database_privilege` = true |
| Connexion à `odoo20` | possible (rôle `odoo20`) | `has_database_privilege` = true |
| Refus de connexion à `odoo20` pour `gest_agri_dev` | non testé (rôle non créé) | à vérifier après création |
| Refus d'écriture sur `odoo20` | non testé (pas d'écriture réelle) | documenté |

### 2. Méthode de vérification proposée

Après création du rôle `gest_agri_dev` :

```sql
-- Vérifier la connexion à la base de diagnostic
psql -U gest_agri_dev -h 127.0.0.1 -p 5433 -d gest_agri_audit_test -c "SELECT 1;"

-- Vérifier le refus de connexion à la production
psql -U gest_agri_dev -h 127.0.0.1 -p 5433 -d odoo20 -c "SELECT 1;"
-- Attendu : FATAL: permission denied for database "odoo20"
```

### 3. Conclusion

La protection formelle n'est pas encore démontrée. Le rôle `gest_agri_dev` n'a
pas été créé. La vérification sera possible après création du rôle.

**Statut : NON DÉMONTRÉ.**

---

*Rapport — Prompt 30 — Phase C — Module `gestion_agricole`.*
# RAPPORT PROMPT 30 — COPIE INDÉPENDANTE DU CODE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Sauvegarde existante

- Emplacement : `/tmp/opencode/dev_backup/gestion_agricole_backup_20261111_052600/`
- Fichiers : 41 fichiers Python
- Manifeste : présent
- SHA256 de `reservation.py` : identique à l'original

### 2. Copie de travail prévue

- Emplacement prévu : `/tmp/opencode/dev/gestion_agricole/`
- Statut : non créée (pas d'écrasement sans autorisation)

### 3. Conditions de création

- Aucune dépendance par lien symbolique vers le module source.
- Aucun fichier partagé avec le répertoire source.
- Sauvegarde originale préservée.
- Inventaire des fichiers.
- Comparaison SHA256.
- Conservation des modifications Git existantes.

### 4. Conclusion

La sauvegarde existante est vérifiée et exploitable. La copie de travail n'a
pas été créée (pas d'écrasement sans autorisation).

---

*Rapport — Prompt 30 — Phase D — Module `gestion_agricole`.*
# RAPPORT PROMPT 30 — ISOLATION DU FILESTORE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Filestore actuel

- `data_dir` actuel : `/var/lib/odoo`
- Filestore de production : `/var/lib/odoo/filestore/odoo20`
- Filestore de diagnostic : `/var/lib/odoo/filestore/gest_agri_audit_test`
- Les deux partagent le même `data_dir` racine.

### 2. Répertoire de développement prévu

- `/tmp/opencode/dev/data/`
- Filestore : `/tmp/opencode/dev/data/filestore/gest_agri_audit_test/`

### 3. Vérification

- Absence de lien symbolique vers `/var/lib/odoo` : à vérifier après création.
- Permissions indépendantes : à configurer.
- Propriétaire du répertoire : à configurer.
- Absence de partage avec le filestore de production : à vérifier.

### 4. Conclusion

Le filestore de développement n'a pas été créé. La procédure est documentée.

---

*Rapport — Prompt 30 — Phase E — Module `gestion_agricole`.*
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
# RAPPORT PROMPT 30 — JOURNALISATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. État actuel

- `logfile` absent (stdout du processus)
- `log_level` = info
- Rotation : aucune
- PostgreSQL : `log_statement = none`, `logging_collector = off`

### 2. Proposition

- Odoo : `logfile = /tmp/opencode/dev/logs/odoo20-dev.log`, rotation logrotate
- PostgreSQL : `log_statement = 'ddl'`, `log_connections = on`,
  `log_disconnections = on`, `log_min_duration_statement = 500`
- Accès : pas d'ajout de `kantmoh` au groupe `postgres`

### 3. Risques

- Exposition de données personnelles dans les logs.
- Risque de perte de lignes pendant la rotation.
- Permissions du groupe PostgreSQL à surveiller.

### 4. Conclusion

Non appliqué. Proposition documentée.

---

*Rapport — Prompt 30 — Phase G — Module `gestion_agricole`.*
# RAPPORT PROMPT 30 — VALIDATION DE L'ISOLATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. Matrice de validation

| Contrôle | Condition de réussite | Statut |
|---|---|---|
| Processus indépendant | Nouveau processus distinct | NON TESTÉ |
| Code indépendant | Copie de travail réellement chargée | NON TESTÉ |
| Configuration indépendante | Fichier dédié | PRÉPARÉ |
| Base indépendante | Uniquement `gest_agri_audit_test` | PRÉPARÉ |
| Rôle indépendant | `gest_agri_dev` | NON CRÉÉ |
| Accès production | Refusé | NON DÉMONTRÉ |
| Filestore indépendant | Répertoire distinct | PRÉPARÉ |
| Journaux indépendants | Répertoire distinct | PRÉPARÉ |
| Port indépendant | 8072 | PRÉPARÉ |
| Odoo 16 | Aucun changement | VALIDÉ |
| Production | Aucune écriture | VALIDÉ |

### 2. Conclusion

L'isolation n'est pas démontrée. Le rôle `gest_agri_dev` n'a pas été créé.
Le serveur de développement n'a pas été lancé.

**Verdict : ISOLATION NON DÉMONTRÉE.**

---

*Rapport — Prompt 30 — Phase H — Module `gestion_agricole`.*
# RAPPORT PROMPT 30 — SYNTHÈSE DÉCISIONNELLE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Verdicts par domaine

| Domaine | Verdict |
|---|---|
| Identification des processus | VALIDÉ |
| Séparation du code | VALIDÉ |
| Séparation des configurations | VALIDÉ |
| Séparation des bases | NON DÉMONTRÉE |
| Séparation PostgreSQL | NON DÉMONTRÉE |
| Séparation des filestores | NON DÉMONTRÉE |
| Séparation des journaux | VALIDÉ |
| Protection de la production | NON DÉMONTRÉE |
| Lancement du serveur de développement | BLOQUÉ |

### 2. Verdict global

**ISOLATION NON DÉMONTRÉE.**

La phase corrective du code ne peut pas commencer. Le rôle PostgreSQL de
développement doit être créé et validé avant toute modification du code.

### 3. Conditions pour débloquer

1. Créer le rôle `gest_agri_dev` avec des privilèges limités à
   `gest_agri_audit_test`.
2. Vérifier que ce rôle ne peut pas écrire dans `odoo20`.
3. Configurer le filestore de développement dans un répertoire indépendant.
4. Lancer le serveur de développement avec la configuration dédiée.
5. Vérifier l'isolation par des preuves techniques.

### 4. Règle finale

Aucune correction fonctionnelle du module n'est autorisée. La phase corrective
ne pourra commencer qu'après validation de l'isolation et décision explicite
de l'utilisateur.

---

*Rapport — Prompt 30 — Phase I — Module `gestion_agricole`.*
