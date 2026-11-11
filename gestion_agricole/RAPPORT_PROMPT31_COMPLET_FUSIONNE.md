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
# RAPPORT PROMPT 31 — ANALYSE DE PUBLIC

## Module `gestion_agricole` — Odoo 20 Community

### 1. Analyse

Dans PostgreSQL, certains privilèges peuvent être accordés à PUBLIC par défaut.

Pour le rôle `odoo20` :
- `has_database_privilege('odoo20', 'odoo20', 'CONNECT')` = true
- `has_database_privilege('odoo20', 'odoo20', 'CREATE')` = true
- `has_database_privilege('odoo20', 'odoo20', 'TEMPORARY')` = true

### 2. Risque d'accès indirect

Le futur rôle `gest_agri_dev` pourrait potentiellement accéder à `odoo20` si
des privilèges sont accordés à PUBLIC. Cependant, le rôle `odoo20` n'est
membre d'aucun groupe, et les privilèges sont accordés directement au rôle.

### 3. Conclusion

Le risque d'accès indirect via PUBLIC doit être vérifié après création du
rôle `gest_agri_dev`. Les privilèges de PUBLIC sur les bases et schémas doivent
être examinés.

**Attention** : `REVOKE CONNECT ON DATABASE odoo20 FROM PUBLIC;` n'a pas été
exécuté (pourrait affecter d'autres applications).

---

*Rapport — Prompt 31 — Phase B — Module `gestion_agricole`.*
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
# RAPPORT PROMPT 31 — COMPARAISON DES ARCHITECTURES

## Module `gestion_agricole` — Odoo 20 Community

### 1. Option 1 — Utiliser directement `gest_agri_audit_test`

| Critère | Évaluation |
|---|---|
| Isolation production | Faible (même rôle propriétaire) |
| Propriété des objets | Problématique (objets appartiennent à `odoo20`) |
| Compatibilité Odoo | Bonne |
| Mises à jour des modules | Possible (propriétaire de la base) |
| Séquences | Accessibles |
| Extensions | `btree_gist` déjà installée |
| Sauvegarde/restauration | Simple |
| Filestore | Partagé avec production (même `data_dir`) |
| Risque opérationnel | Moyen (même base, même rôle) |
| Facilité de maintenance | Bonne |

### 2. Option 2 — Créer une nouvelle base `gest_agri_dev_db`

| Critère | Évaluation |
|---|---|
| Isolation production | Élevée (base distincte) |
| Propriété des objets | Bonne (restauration avec propriétaire dédié) |
| Compatibilité Odoo | Bonne |
| Mises à jour des modules | Possible (rôle propriétaire) |
| Séquences | Accessibles |
| Extensions | `btree_gist` à installer (disponible v1.8) |
| Sauvegarde/restauration | Plus complexe |
| Filestore | Indépendant |
| Risque opérationnel | Faible |
| Facilité de maintenance | Moyenne |

### 3. Recommandation

**Option 2 recommandée.** Elle offre une meilleure isolation et une propriété
claire des objets. La sauvegarde/restauration de `gest_agri_audit_test` vers
`gest_agri_dev_db` est réalisable avec `pg_dump`/`pg_restore`.

---

*Rapport — Prompt 31 — Phase D — Module `gestion_agricole`.*
# RAPPORT PROMPT 31 — PROPRIÉTÉ DES OBJETS ET PRIVILÈGES ODOO

## Module `gestion_agricole` — Odoo 20 Community

### 1. Exploitation normale

Privilèges nécessaires : SELECT, INSERT, UPDATE, DELETE, séquences, fonctions.

### 2. Modifications structurelles

Privilèges nécessaires : CREATE TABLE, ALTER TABLE, DROP TABLE, CREATE INDEX,
ALTER INDEX, création de contraintes, modification de colonnes, création de
séquences, modifications de vues, créations de fonctions.

### 3. Pourquoi les GRANT ne remplacent pas la propriété

Les GRANT permettent l'accès aux objets, mais ne confèrent pas la propriété.
Un rôle non propriétaire ne peut pas ALTER ou DROP un objet, même avec des
GRANT. Odoo a besoin de la propriété pour les migrations.

### 4. Stratégie compatible avec les migrations futures

Le rôle de développement doit être propriétaire des objets de la base de
développement. Cela nécessite une restauration avec `--no-owner` et un
`ALTER ... OWNER TO` ou l'utilisation de `--role`.

---

*Rapport — Prompt 31 — Phase E — Module `gestion_agricole`.*
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
# RAPPORT PROMPT 31 — CONCEPTION FINALE DU RÔLE DÉDIÉ

## Module `gestion_agricole` — Odoo 20 Community

### 1. Rôle proposé : `gest_agri_dev`

Attributs :
- LOGIN : oui
- NOSUPERUSER
- NOCREATEDB
- NOCREATEROLE
- NOREPLICATION
- NOBYPASSRLS

### 2. Commandes proposées (non exécutées)

```sql
CREATE ROLE gest_agri_dev WITH LOGIN PASSWORD '<SECRET_A_CONFIGURER>'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

GRANT CONNECT, TEMPORARY ON DATABASE gest_agri_dev_db TO gest_agri_dev;
GRANT USAGE, CREATE ON SCHEMA public TO gest_agri_dev;
```

### 3. Vérifications de sécurité

- Connexion à la base de développement : autorisée
- Connexion à `odoo20` : refusée
- Accès aux objets de `odoo20` : impossible
- Création de base : refusée
- Création de rôle : refusée
- Accès aux privilèges administrateur : refusé

### 4. Mécanisme sécurisé de configuration du secret

Le mot de passe ne doit pas apparaître en clair dans les arguments de
commandes ou dans l'historique du shell. Utiliser un fichier de configuration
ou une variable d'environnement.

---

*Rapport — Prompt 31 — Phase H — Module `gestion_agricole`.*
# RAPPORT PROMPT 31 — PLAN DE VALIDATION

## Module `gestion_agricole` — Odoo 20 Community

### Matrice de validation

| Test | Résultat attendu |
|---|---|
| Connexion à la base de développement | Autorisée |
| Lecture de la base de développement | Autorisée |
| Création d'une table de test | Autorisée |
| Modification d'une table de test | Autorisée |
| Création d'un index de test | Autorisée |
| Utilisation d'une séquence de test | Autorisée |
| Connexion à `odoo20` | Refusée |
| Accès aux objets de `odoo20` | Impossible |
| Connexion à `gest_agri_audit_test` (si Option 2) | Refusée |
| Création de base par `gest_agri_dev` | Refusée |
| Création de rôle par `gest_agri_dev` | Refusée |
| Accès aux privilèges administrateur | Refusé |

### Conclusion

Tous les tests d'écriture seront exécutés exclusivement sur la nouvelle base
de développement et seulement après autorisation.

---

*Rapport — Prompt 31 — Phase I — Module `gestion_agricole`.*
# RAPPORT PROMPT 31 — SYNTHÈSE DÉCISIONNELLE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Verdicts

| Domaine | Verdict |
|---|---|
| Audit PostgreSQL | VALIDÉ |
| Analyse PUBLIC | VALIDÉ (risque identifié) |
| Analyse pg_hba.conf | PARTIEL (fichier non lisible) |
| Comparaison des architectures | VALIDÉ (Option 2 recommandée) |
| Propriété des objets | VALIDÉ |
| Privilèges par défaut | VALIDÉ |
| Plan de sauvegarde/restauration | VALIDÉ |
| Conception du rôle dédié | VALIDÉ |
| Plan de validation | VALIDÉ |

### 2. Verdict global

**VERDICT B — ARCHITECTURE DÉFINIE, NON APPLIQUÉE.**

La stratégie d'isolation est cohérente, mais aucune opération n'a été exécutée.

Le présent Prompt 31 ne peut pas aboutir au verdict C puisqu'il n'autorise
aucune modification.

### 3. Recommandation

Option 2 (nouvelle base `gest_agri_dev_db`) recommandée. Le rôle `gest_agri_dev`
doit être créé et validé avant toute modification du code.

---

*Rapport — Prompt 31 — Phase I — Module `gestion_agricole`.*
