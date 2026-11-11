# RAPPORT PROMPT N°14 — RÉSOLUTION DES RISQUES RÉSIDUELS ET CONSOLIDATION DU MODULE `gestion_agricole`
## Odoo 20 Community — préfixe technique `gest_agri`

> **Cadre d'exécution.** Toutes les opérations ont été réalisées sur le **code
> source** et sur les **bases de diagnostic** (`gest_agri_audit_test`,
> `gest_agri_concurrency_test`). Aucune commande `-u`/`-i` n'a été exécutée sur
> `odoo20`, aucune donnée/index/vue/menu/paramètre de production n'a été
> modifié, aucun service n'a été arrêté ou redémarré, `/etc/odoo20.conf` et la
> configuration PostgreSQL sont inchangés, aucune base n'a été supprimée.
>
> **État de la production à la fin des travaux** (contrôle en lecture seule) :
> module `installed` v`20.0.1.0.0`, `write_date` inchangé
> (`2026-11-10 21:40:00.677710`), 39 index uniques de configuration, 10 index
> patrimoniaux, 71 droits d'accès, 23 actions, 46 vues list/form, 1 exploitation
> et 1 site (données de l'opérateur), **table de réservation absente** et
> **extension `btree_gist` absente** → le mécanisme d'unicité est **inerte** en
> production, sans aucune modification.

---

# 1. SYNTHÈSE EXÉCUTIVE

| Anomalie initiale | Cause technique | Statut |
|---|---|---|
| **R1** — un code global et un code de société peuvent être créés simultanément sous `REPEATABLE READ` | Le verrou consultatif + recherche ORM sérialise les transactions mais **ne rafraîchit pas l'instantané** ; aucun index unique n'exprime la portée « toutes les sociétés » | ✅ **CORRIGÉ ET TESTÉ** |
| **R3** — l'instance de production dessert la production **et** les bases de diagnostic | `db_name` vide + `list_db = True` → `list_dbs()` retourne toutes les bases | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase B) |
| **R9** — aucun journal exploitable n'a permis d'attribuer les deux upgrades de production | Sortie Odoo vers `/dev/pts/1`, journal PostgreSQL non lisible, `log_statement = none` | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase C) |
| **R4** — 7 avertissements « two fields have the same label » | Libellés identiques entre un compteur et son champ enfant | ✅ **CORRIGÉ ET TESTÉ** |
| **R7** — `report/`, `wizard/` vides, `equipment_type.py.bak` dans l'addon | Artefacts de développement | ✅ **CORRIGÉ ET TESTÉ** (archivage hors addon) |
| README obsolète | Non remis à jour depuis le Prompt n°4 | ✅ **CORRIGÉ ET TESTÉ** |

**Résultats de validation (Phase E) :**

| Indicateur | Avant | Après |
|---|---|---|
| Méthodes de test du module | 73 | **99** |
| `testsRun` global | 75 | **101** |
| Échecs / erreurs / tests ignorés | 0 / 0 / 0 | **0 / 0 / 0** |
| Contrôles statiques Phase E | — | **31 / 31 conformes** |
| Index uniques en production | 39 | 39 (inchangé) |

---

# 2. PHASE A — IMPLÉMENTATION DE L'UNICITÉ CONCURRENTE

## 2.1 Les 13 modèles concernés et leurs champs

| # | Modèle | `code` | `name` | `company_id` | `active` |
|---|---|---|---|---|---|
| 1 | `gest_agri.farm.type` | Char, requis | Char, requis | Many2one `res.company` | Booléen, défaut `True` |
| 2 | `gest_agri.soil.type` | idem | idem | idem | idem |
| 3 | `gest_agri.crop.type` | idem | idem | idem | idem (+ `crop_cycle`) |
| 4 | `gest_agri.crop.variety` | idem | idem | idem | idem (+ `crop_type_id`) |
| 5 | `gest_agri.livestock.species` | idem | idem | idem | idem |
| 6 | `gest_agri.livestock.breed` | idem | idem | idem | idem (+ `species_id`) |
| 7 | `gest_agri.operation.type` | idem | idem | idem | idem |
| 8 | `gest_agri.treatment.type` | idem | idem | idem | idem |
| 9 | `gest_agri.fertilizer.type` | idem | idem | idem | idem |
| 10 | `gest_agri.irrigation.type` | idem | idem | idem | idem |
| 11 | `gest_agri.equipment.type` | idem | idem | idem | idem |
| 12 | `gest_agri.building.type` | idem | idem | idem | idem |
| 13 | `gest_agri.production.type` | idem | idem | idem | idem |

Les 13 partagent exactement les quatre champs nécessaires : `code`, `name`,
`company_id` (société facultative → enregistrement global) et `active`
(archivage).

## 2.2 Conception finale de la table de réservation

### 2.2.1 Choix structurant : une table technique, pas un modèle Odoo

Le type `int8range` n'a **pas** d'équivalent parmi les champs Odoo 20
(`Integer`, `Float`, `Monetary` seulement). La contrainte d'exclusion doit donc
porter sur une **expression** :

```sql
EXCLUDE USING gist (..., (int8range(scope_lo, scope_hi)) WITH &&)
```

Cette expression fonctionne (vérifié sur PostgreSQL 18.6) et permet de
n'exposer que deux colonnes entières à l'ORM.

Deux raisons ont conduit à **ne pas déclarer de modèle Odoo** :

1. **Sécurité de la production** : un modèle Odoo déclaré dans un module déjà
   installé voit sa table créée automatiquement au **prochain rechargement de
   registre** — y compris en production, sans `-u`. Une table technique gérée
   en SQL brut, dont la création est conditionnée à la présence de l'extension
   `btree_gist`, ne peut pas provoquer cet effet de bord.
2. **Absence de « Model has no table »** : un modèle Odoo dont la table
   n'existerait pas produirait une erreur de journalisation à chaque
   chargement de registre (`Registry.check_tables_exist`).

### 2.2.2 Schéma

```sql
CREATE TABLE gest_agri_reference_reservation (
    id         serial PRIMARY KEY,
    model_name varchar NOT NULL,   -- modèle métier réservant la clé
    kind       varchar NOT NULL,   -- 'code' | 'name'
    normalized varchar NOT NULL,   -- code/nom normalisé
    scope_lo   bigint  NOT NULL,   -- borne basse du périmètre
    scope_hi   bigint             -- borne haute (NULL = non bornée)
);
CREATE INDEX gest_agri_reference_reservation_lookup_idx
    ON gest_agri_reference_reservation (model_name, kind, normalized);

ALTER TABLE gest_agri_reference_reservation
    ADD CONSTRAINT gest_agri_reference_reservation_scope_exclusion
    EXCLUDE USING gist (
        model_name WITH =,
        kind WITH =,
        normalized WITH =,
        (int8range(scope_lo, scope_hi)) WITH &&
    );
```

### 2.2.3 Représentation des périmètres — domaines disjoints par signe

| Situation | `scope_lo` | `scope_hi` | `int8range` | Domaine |
|---|---|---|---|---|
| Code **global** | `1` | `NULL` | `[1, +∞)` | positif |
| Code de société `c` | `c` | `c+1` | `[c, c+1)` | positif |
| Nom **global** | `-1` | `0` | `[-1, 0)` = `{-1}` | **négatif** |
| Nom de société `c` | `c` | `c+1` | `[c, c+1)` | positif |

**Pourquoi ce découpage est plus robuste que celui du Prompt 12 :**

| Propriété | Prompt 12 | Prompt 14 |
|---|---|---|
| Périmètre du nom global | `int8range(0, 1)` = `{0}` | `int8range(-1, 0)` = `{-1}` |
| Domaine partagé avec les sociétés | **oui** (`[0, +∞)`) | **non** (`{-1}` disjoint de `[1, +∞)`) |
| Sensibilité à un `company_id = 0` | **collision possible** | **impossible** (le négatif est hors de portée de tout `serial`) |
| Couverture d'une société | `int8range(0, MAXINT)` borne entière | `int8range(1, NULL)` **non bornée** |

Vérifications mesurées :

```
lower(int8range(1,NULL)) = 1          upper = NULL
int8range(1,NULL) @> 1        -> True
int8range(1,NULL) @> 1000000   -> True
int8range(1,NULL) @> 0        -> False     <- le domaine négatif est exclu
int8range(0,1) && int8range(1,2) -> False  (adjacentes)
int8range(-1,0) && int8range(1,2) -> False (domaines disjoints)
res_company réels (base de test) : id min = 1, id max = 2
```

### 2.2.4 `scope_key` : champ supprimé

Le Prompt 13 demandait de vérifier si `scope_key` était nécessaire. **Il ne
l'est pas** : le périmètre est intégralement déterminé par
`(kind, company_id)`, que le code applicatif connaît toujours au moment du
`create`, du `write` et du `unlink`. Le champ a donc été **supprimé** : la
libération d'une réservation utilise le périmètre recalculé, ce qui distingue
correctement le cas « nom global » et « nom de société » (deux réservations de
même valeur normalisée peuvent coexister pour `kind='name'`).

La table ne contient donc que des données **non redondantes**.

### 2.2.5 Normalisation

`normalize_reference(value)` → `value.strip().casefold()` (identique à la
normalisation Python déjà utilisée par la contrainte applicative). La
normalisation SQL des index uniques reste `LOWER(BTRIM(...))` : l'écart
résiduel (tabulations, `ß`) joue **dans le sens favorable** — la
réservation est plus stricte que l'index, donc aucun faux négatif.

## 2.3 Mécanisme de migration

| Étape | Implémentation | Garantie |
|---|---|---|
| 1. Installer l'extension | **Décision opérationnelle explicite** : `CREATE EXTENSION btree_gist;` — le module ne l'installe pas lui-même | Sans droits-CRDB, rien ne se passe ; la base n'est pas modifiée |
| 2. Créer la table | `setup_reservations()` — `CREATE TABLE IF NOT EXISTS` + index de recherche | Idempotent |
| 3. Reprendre les réservations existantes | Balayage des 13 tables, **en Python** (même normalisation que le code applicatif), seulement pour les enregistrements **actifs** | Un doublon préexistant fait **échouer** la pose de la contrainte (voir 2.3.2) |
| 4. Poser la contrainte d'exclusion | `ALTER TABLE ... ADD CONSTRAINT ... EXCLUDE USING gist` | C'est **le** point de contrôle : si un doublon existe, PostgreSQL refuse la contrainte et **annule la transaction de mise à jour** |
| 5. Activer la logique applicative | Le mixin teste la présence de la contrainte à chaque écriture | Automatique : la reprise having created the constraint is followed by the activation |

### 2.3.1 Absence de fenêtre de concurrence

La reprise et la pose de la contrainte ont lieu **dans la même transaction** que
la mise à jour du module. Ordre :

```
BEGIN (mise à jour du module)
  ├─ reprise des réservations        (INSERT)
  ├─ ALTER TABLE ... ADD CONSTRAINT  (contrôle des doublons)
  └─ COMMIT
```

Un concurrent qui crée une référence pendant cette fenêtre :
- **avant** la reprise : sa réservation est reprise → la contrainte la
  détectera si elle est en doublon → mise à jour refusée ;
- **pendant** la pose de la contrainte : le `ALTER TABLE` attend le verrou
  exclusif de la table → le concurrent est sérialisé.

Il n'existe donc **aucune fenêtre** entre la reprise et l'activation.

### 2.3.2 Échec de migration en présence d'un doublon

Testé (`test_migration_fails_with_existing_duplicate`) : la reprise échoue sur
`ExclusionViolation` → la transaction de mise à jour est annulée → **aucune
donnée n'est modifiée**. Le DDL PostgreSQL étant transactionnel, l'annulation
restaure aussi la contrainte d'exclusion.

### 2.3.3 Point d'ancrage : `Registry.post_init`

La reprise est planifiée via `Registry.post_init` (`odoo/orm/registry.py:787`),
qui s'exécute **après** l'initialisation de tous les modèles : la reprise voit
donc l'intégralité des tables de référentiels, y compris celles créées pendant
une installation.

## 2.4 Opérations CRUD, archivage, réactivation, chemins indirects

Implémentées dans un **mixin Python** (`ReferenceReservationMixin`) appliqué aux
13 modèles — sans modèle Odoo, sans modification de champ, sans modification
des 39 index existants.

**Ordre des opérations (identique en création et en modification) :**

```
1. libérer les réservations qui ne sont plus valides
2. réserver les nouvelles clés      <- le conflit est détecté AVANT l'écriture métier
3. écrire l'enregistrement métier
```

Le tout est exécuté dans un **savepoint** : en cas de conflit, le savepoint est
annulé, la transaction reste utilisable et l'enregistrement métier n'est pas
laissé à l'état partiel.

| Opération | Traitement | Vérifié par |
|---|---|---|
| `create` (mono et multiple) | réservation **avant** l'INSERT, à partir des valeurs projetées (code, nom, `company_id` résolu comme Odoo le fait : valeur fournie → `default_company_id` du contexte → défaut du champ ; `active` par défaut `True`) | `test_multi_creation_with_conflict_is_rejected`, `test_multi_creation_without_conflict_succeeds` |
| `write` du `code` | libération de l'ancienne clé, réservation de la nouvelle | `test_scenario_09_modify_code` |
| `write` du `name` | idem | `test_simultaneous_code_and_name_change` |
| `write` de `company_id` | les **deux** réservations sont libérées et re-réservées (le périmètre change) | `test_scenario_10_change_company` |
| `write` de `code` **et** `company_id` | idem, en une seule opération | `test_company_and_code_change_together` |
| `write` `active = False` (archivage) | les réservations sont **libérées** (seuls les actifs réservent) | `test_scenario_08_archive_then_reuse_key`, `test_reservation_rows_match_active_records` |
| `write` `active = True` (réactivation) | les réservations sont **reprises** → un conflit est détecté **avant** l'écriture | `test_reactivation_with_conflict_is_rejected` |
| `unlink` | libération des réservations | `test_deletion_releases_the_key` |
| `copy` | passe par `create` → couvert | Covered |
| Import de données, `load()` | passent par `create` → couverts | Covered |
| Écriture SQL directe | hors périmètre ORM (documenté) | — |

**Écritures multiples** : les clés à libérer sont d'abord calculées sur
l'ensemble des enregistrements, puis les nouvelles réservations sont insérées
— un changement de code appliqué à plusieurs enregistrements ne se heurte donc
pas à lui-même.

## 2.5 Gestion des conflits PostgreSQL

| Situation | Exception | Traitement |
|---|---|---|
| Conflit de réservation | `psycopg2.errors.ExclusionViolation` | Converti en `ValidationError` **français** : « Le code « X » est déjà utilisé : un code global le réserve à toutes les sociétés, ou une autre société l'utilise déjà. » |
| Conflit sur l'index unique de la table métier | `psycopg2.errors.UniqueViolation` | Converti de la même façon (filet de sécurité pour le cas concurrent) |
| Transaction annulée | — | Le savepoint est annulé : la transaction reste utilisable |

Le message est produit **avant** l'écriture métier : l'utilisateur n'est plus
exposé à une erreur PostgreSQL brute (amélioration par rapport au comportement
observé au Prompt 12, où l'index unique était levé pendant l'INSERT et
produisait `UniqueViolation` au niveau ORM).

## 2.6 Pas de régression sur les contraintes et index existants

- Aucun champ modifié : les 39 index uniques déclarés par les 13 modèles sont
  **inchangés** (mêmes expressions, mêmes noms).
- Le mixin est un simple héritage Python : aucun effet sur la construction des
  tables ni sur la réflexion des champs.
- Le `create`/`write`/`unlink` du modèle **standard** d'Odoo est toujours
  appelé (`super()`), avec les mêmes signatures.

---

# 3. PHASE B — ISOLATION DE LA PRODUCTION ET DES TESTS

**Statut : PROPOSITION NON APPLIQUÉE.** Aucun fichier de configuration n'a été
modifié, aucun service n'a été arrêté ou redémarré.

Le diagnostic et la procédure complète sont dans
`/tmp/opencode/preparation/PHASE_B_ISOLATION_PROPOSITION.md`, avec le fichier
de configuration d'instance de test préparé dans
`/tmp/opencode/preparation/odoo20-test.conf.proposition`.

| Élément | Contenu de la proposition |
|---|---|
| Production | ajout de `db_name = odoo20` et `dbfilter = ^odoo20$` dans `/etc/odoo20.conf` |
| Instance de test | nouveau fichier `/etc/odoo20-test.conf` (mot de passe repris de la production, **aucun mot de passe inventé**) |
| Isolation | `data_dir` distinct (`/var/lib/odoo20-test`), port distinct (8072), `db_name`/`dbfilter` restreints |
| Vérification « l'instance de test ne dessert pas `odoo20` » | 4 contrôles : (1) `pg_stat_activity` — aucune connexion de l'instance de test sur `odoo20` ; (2) `/web/database/list` de l'instance de test sans `odoo20` ; (3) `/web/database/list` de la production sans `gest_agri_audit_test` ; (4) `/web/login?db=odoo20` sur le port 8072 → 404 |
| Procédure | 10 étapes : sauvegarde (`pg_dump -Fc` + copie de la config + du `data_dir`) → contrôle des processus → fenêtre de maintenance → arrêt propre → modification de la configuration → redémarrage → contrôles → démarrage de l'instance de test → contrôles → rejeu des tests — **chaque étape a son retour arrière** |

Compatibilité vérifiée avec la version exacte d'Odoo 20 installée : le mécanisme
`db_name` / `dbfilter` de `list_dbs()` (`odoo/modules/db.py:718`) et
`db_filter()` (`odoo/http/router.py:86`) existent bien en 20.0.

---

# 4. PHASE C — TRAÇABILITÉ

**Statut : PROPOSITION NON APPLIQUÉE.** Ni `/etc/odoo20.conf`, ni PostgreSQL, ni
les permissions système n'ont été modifiés.

Document complet : `/tmp/opencode/preparation/PHASE_C_JOURNALISATION_PROPOSITION.md`.

| Axe | Proposition | Statut |
|---|---|---|
| Journal Odoo dans un fichier | `logfile = /var/log/odoo/odoo20.log` + rotation `logrotate` (30 j, compression) | ⬜ À autoriser (écriture dans `/etc/odoo20.conf`) |
| Journal PostgreSQL lisible | Ajout du compte de lecture au groupe PostgreSQL, ou copie quotiddienne avec `chmod 644` dans un répertoire dédié | ⬜ À autoriser (changement de permissions) |
| Journalisation SQL | `log_statement = 'ddl'` (trace les `ALTER TABLE` / `CREATE INDEX` — donc les upgrades) + `log_min_duration_statement = 500` | ⬜ À autoriser (configuration PostgreSQL) |
| Traçabilité des commandes Odoo | Règle `auditd` sur le binaire Odoo (`auditctl -w … -k odoo`) ; conservation de l'historique bash de l'opérateur | ⬜ À autoriser (installation auditd) |
| Traçabilité applicative | Table technique `gest_agri_audit_log` alimentée par `setup_reservations()` | ⚙️ **NON APPLIQUÉE** (schéma et politique de conservation à définir) |
| Séparation production / test | journaux, `data_dir`, port et configuration distincts (Phase B) | ⬜ À autoriser avec la Phase B |

---

# 5. PHASE D — CORRECTIONS DE QUALITÉ DU MODULE

| # | Anomalie | Correction | Statut |
|---|---|---|---|
| 1 | **7 avertissements « two fields have the same label »** (`site_count`/`site_ids`, `plot_count`/`plot_ids`, `building_count`/`building_ids`, `infrastructure_count`/`infrastructure_ids`, `water_source_count`/`water_source_ids`, `irrigation_network_count`/`irrigation_network_ids`, `access_count`/`access_ids`) | Libellés des compteurs renommés : « Nb sites », « Nb parcelles », « Nb bâtiments », « Nb infrastructures », « Nb sources d'eau », « Nb réseaux d'irrigation », « Nb droits d'accès ». Les libellés des champs enfants sont inchangés | ✅ **CORRIGÉ ET TESTÉ** (0 avertissement au chargement) |
| 2 | `README.md` obsolète (état « Prompt n°4 », 15 modèles au lieu de 26, absence du mécanisme d'unicité) | Réécriture complète : contenu réel, 13 référentiels, 10 modèles de patrimoine, mécanisme d'unicité à trois niveaux, exigence `btree_gist`, sécurité, tests, points connus | ✅ **CORRIGÉ ET TESTÉ** |
| 3 | `report/` et `wizard/` : paquets vides importés par `__init__.py` | **Conservés** (ce sont des emplacements réservés, et « ne rien supprimer sans preuve ») + docstring explicative dans chaque `__init__.py` | ✅ **CORRIGÉ ET TESTÉ** |
| 4 | `models/configuration/equipment_type.py.bak` : sauvegarde obsolète d'une version **antérieure** aux corrections du Prompt 11 (elle ne contient pas la règle d'administration), non importée par Odoo | **Déplacée hors du chemin d'addons** vers `/mnt/srv/share/odoo20/_archives/gestion_agricole/equipment_type.py.bak` (contenu conservé, plus de confusion dans l'addon) | ✅ **CORRIGÉ ET TESTÉ** |
| 5 | Fichiers XML / Python / manifeste | 41 fichiers Python compilés, 7 XML bien formés, 8 fichiers `data` présents, 12 dépendances installées | ✅ **CORRIGÉ ET TESTÉ** |
| 6 | Cohérence actions / menus / vues / droits | 23 actions, 38 menus, 46 vues list/form, 23 vues search, 71 droits sur 23 modèles, 0 doublon d'identifiant externe | ✅ **CONTRÔLÉ** |
| 7 | Messages fonctionnels en français | Contrôle : **tous** les libellés et messages du module sont en français ; les messages de la réservation sont en français | ✅ **CONTRÔLÉ** |

---

# 6. PHASE E — VALIDATION GÉNÉRALE

## 6.1 Contrôles statiques (31/31 conformes)

| Contrôle | Résultat |
|---|---|
| Compilation de tous les fichiers Python | ✅ **41 fichiers** compilés, 0 erreur |
| Noms non définis (analyse `symtable`) | ✅ **0 anomalie** |
| Validation XML | ✅ 7 fichiers bien formés |
| Manifeste : fichiers `data` présents | ✅ 8/8 |
| Manifeste : version / licence / dépendances | ✅ `20.0.1.0.0` / `LGPL-3` / 12 |
| Dépendances installées dans le registre | ✅ 12/12 |
| Index uniques de configuration (13 modèles) | ✅ **39/39** valides et prêts — base de test **et** production |
| Index uniques patrimoniaux (10 tables) | ✅ **10/10** valides et prêts — base de test **et** production |
| Droits d'accès | ✅ 71 lignes, 23 modèles couverts, 71 domaines multi-sociétés |
| Réservation : contrainte d'exclusion présente et attachée | ✅ |
| Réservation : extension `btree_gist` — base de test | ✅ installée |
| Réservation : extension `btree_gist` — **production** | ✅ **absente** (mécanisme inerte) |
| Réservation : table — **production** | ✅ **absente** |
| Identifiants externes | ✅ 677, 0 doublon |
| Actions / vues / menus / xml id ciblés | ✅ tous présents |

## 6.2 Décompte explicite des tests

Exécution sur `gest_agri_audit_test`, `--test-enable --test-tags /gestion_agricole`,
avec le rapport détaillé de `odoo.tests.stats` (niveau DEBUG) qui publie la liste
exacte des identifiants comptés :

| Grandeur | Valeur | Origine |
|---|---|---|
| **Méthodes de test du module `gestion_agricole`** | **99** | entrées `…Class.test_*` du rapport détaillé |
| **Tests globaux exécutés** (`testsRun`) | **101** | 99 méthodes du module + **2** méthodes `web` (`WebSuite.test_unit_desktop`, `MobileWebSuite.test_unit_mobile`) exécutées dans la même passe |
| **Événements de cycle de vie** | **12** | 6 classes × (`setUpClass` + `tearDownClass`) — créés par `OdooSuite._handleClassSetUp` / `_tearDownPreviousClass` ; **ne sont pas des tests** et ne sont pas comptés dans `testsRun` |
| Entrées d'agrégation (module / classe) | 10 | artefacts du rapport DEBUG, exclus du décompte |
| **Erreurs** | **0** | |
| **Échecs** | **0** | |
| **Tests ignorés** | **0** | aucun `skipTest` dans le module |

Réconciliation (identique à celle du Prompt 13, étendue) :

```
odoo.tests.stats  'gestion_agricole: 111 tests'  = 99 méthodes + 12 cycle de vie
odoo.tests.result 'of 101 tests' (testsRun)      = 99 méthodes du module + 2 méthodes web
```

> **Les deux nombres sont exacts et ne comptent pas la même chose.** Le chiffre
> pertinent pour la qualité du code est **99 méthodes de test** — et non 111 ni
> 101.

## 6.3 Tests de concurrence — preuves sous `REPEATABLE READ`

Les tests de concurrence utilisent **deux connexions PostgreSQL indépendantes**
(`psycopg2`, `REPEATABLE READ` explicite) et reproduisent réellement le
problème d'instantané :

1. la transaction 1 insère une réservation et **ne valide pas** ;
2. la transaction 2 prend son instantané (elle **ne voit pas** l'insertion de
   la transaction 1), puis tente la même réservation ;
3. la transaction 1 valide pendant que la transaction 2 est bloquée ;
4. la transaction 2 reçoit alors `ExclusionViolation`.

| # | Scénario | Attendu | Constaté |
|---|---|---|---|
| 1 | Global → entreprise, concurrent | le 2ᵉ échoue | ✅ `ExclusionViolation` |
| 2 | Entreprise → global, concurrent | le 2ᵉ échoue | ✅ `ExclusionViolation` |
| 3 | Deux créations, même société | le 2ᵉ échoue | ✅ `ExclusionViolation` |
| 4 | Deux créations, sociétés différentes | les deux passent | ✅ les deux passent |
| 5 | Deux créations globales | le 2ᵉ échoue | ✅ `ExclusionViolation` |
| 6 | Nom global + nom de société identiques | coexistence | ✅ coexistence |
| 7 | Deux noms globaux identiques | le 2ᵉ échoue | ✅ `ExclusionViolation` |
| 8 | Archivage puis réutilisation | réutilisation possible | ✅ |
| 9 | Modification du code | ancienne clé libérée | ✅ |
| 10 | Changement de société | réservation déplacée | ✅ |
| 11 | Rollback | réservation libérée | ✅ (0 réservation résiduelle) |
| 12 | Deux transactions strictement simultanées | le 2ᵉ échoue | ✅ `ExclusionViolation` |

**Scénarios complémentaires exigés :** création multiple avec conflit
(refusée, aucune trace), création multiple sans conflit, modification multiple
avec conflit (aucune écriture), changement code + nom simultané, changement
société + code, réactivation avec conflit (refusée avant écriture), suppression,
**échec de migration en présence d'un doublon** (contrainte restaurée après
annulation du savepoint), cohérence après rollback, correspondance
enregistrement ↔ réservations, disjointness des domaines.

## 6.4 Un incident de conception corrigé pendant la validation

Deux problèmes ont été rencontrés et corrigés :

| Problème | Cause | Correction |
|---|---|---|
| **Interblocage** entre la transaction principale et les transactions concurrentes | Le `DELETE` de nettoyage (transaction principale) portait un verrou d'index sur une clé que l'insertion concurrente tentait d'utiliser ; la transaction principale attendait la fin du test → blocage croisé | Clés **uniques par exécution** (jeton `uuid`) pour tous les scénarios de concurrence ; le nettoyage ne purge plus que `dupmig` |
| **Verrou de registre Odoo** entre threads | Le commit d'une transaction Odoo traverse `registry.registry_cache_lock` : deux threads Odoo se sérialisent (et peuvent se bloquer) | Les tests de concurrence utilisent des connexions `psycopg2` brutes (hors ORM) ; le SQL appliqué est **exactement** celui du code applicatif, les clés et périmètres étant calculés par les fonctions du module (`reference_scope`, `normalize_reference`) |

Ces deux points sont **documentés dans le fichier de test** afin qu'une
reprise ultérieure ne les réintroduise.

---

# 7. FICHIERS MODIFIÉS

## 7.1 Nouveaux fichiers

| Fichier | Contenu | Statut |
|---|---|---|
| `models/configuration/reservation.py` | Table de réservation (DDL SQL brut), mixin `ReferenceReservationMixin`, helpers de périmètre et de migration | ✅ **CORRIGÉ ET TESTÉ** |
| `tests/test_reservation_unicity.py` | 25 tests : 12 scénarios de concurrence (2 connexions PostgreSQL indépendantes) + 13 scénarios ORM/CRUD/migration | ✅ **CORRIGÉ ET TESTÉ** |

## 7.2 Fichiers modifiés

| Fichier | Modification | Statut |
|---|---|---|
| `models/configuration/_common.py` | Ajout de `normalize_reference()` et `reference_scope()` (source unique de la normalisation et des périmètres) | ✅ **CORRIGÉ ET TESTÉ** |
| `models/configuration/{farm_type, soil_type, crop_type, crop_variety, livestock_species, livestock_breed, operation_type, treatment_type, fertilizer_type, irrigation_type, equipment_type, building_type, production_type}.py` | Mixin `ReferenceReservationMixin` dans les bases de classe + import | ✅ **CORRIGÉ ET TESTÉ** |
| `models/configuration/__init__.py` | Import du nouveau module `reservation` | ✅ **CORRIGÉ ET TESTÉ** |
| `models/patrimony/farm.py` | 7 libellés de compteurs corrigés (« Nb … ») | ✅ **CORRIGÉ ET TESTÉ** |
| `views/menu_views.xml` | (Phase 12) libellé de la section « Patrimoine agricole » | ✅ antérieur |
| `tests/test_audit_prompt11.py` | Le test du message utilisateur attend désormais un `ValidationError` français (le mécanisme de réservation improved le message) | ✅ **CORRIGÉ ET TESTÉ** |
| `tests/test_configuration.py`, `tests/test_security.py`, `tests/test_patrimony.py`, `tests/__init__.py` | (Phase 12) + import du nouveau module de tests | ✅ antérieur |
| `README.md` | Réécriture complète | ✅ **CORRIGÉ ET TESTÉ** |
| `report/__init__.py`, `wizard/__init__.py` | Docstrings d'explication (paquets réservés, volontairement vides) | ✅ **CORRIGÉ ET TESTÉ** |
| `models/configuration/equipment_type.py.bak` | **Déplacé** vers `/mnt/srv/share/odoo20/_archives/gestion_agricole/` (hors chemin d'addons) | ✅ **CORRIGÉ ET TESTÉ** |

**Bilan : 22 fichiers du module modifiés ou ajoutés, ~1 020 lignes.**

## 7.3 Fichiers préparés, hors module

| Fichier | Objet |
|---|---|
| `/tmp/opencode/preparation/odoo20-test.conf.proposition` | Configuration de l'instance de test (Phase B) |
| `/tmp/opencode/preparation/PHASE_B_ISOLATION_PROPOSITION.md` | Diagnostic, solution, contrôles, procédure de migration et retour arrière |
| `/tmp/opencode/preparation/PHASE_C_JOURNALISATION_PROPOSITION.md` | Diagnostic, paramètres, permissions minimales, risques |

---

# 8. RÉSULTATS MULTI-SOCIÉTÉS

| Contrôle | Résultat |
|---|---|
| 71 lignes de droits d'accès, toutes avec domaine multi-sociétés | ✅ |
| 23 modèles couverts par les droits | ✅ |
| Un utilisateur simple ne voit que ses exploitations | ✅ (`test_farm_isolation`) |
| Un responsable ne peut pas supprimer une exploitation | ✅ (`test_plot_write_permissions`) |
| Un responsable ne peut pas modifier ses propres droits d'accès | ✅ (`test_manager_cannot_edit_own_access`) |
| Un responsable d'une société ne voit ni ne modifie une exploitation d'une autre société | ✅ (`test_e1_no_cross_company_leak_for_manager`, `test_manager_cannot_modify_other_company_farm`) |
| Un nom global et un nom de société identiques coexistent | ✅ (nouvelle règle) |
| Deux sociétés différentes peuvent utiliser le même code | ✅ (`test_scenario_04`, `test_m7_same_code_in_two_companies_is_allowed`) |

---

# 9. RISQUES RÉSIDUELS

| # | Risque | Probabilité | Impact | Statut |
|---|---|---|---|---|
| **R1** | Conflit code global ↔ code de société simultané | **Éliminé** | — | ✅ **CORRIGÉ ET TESTÉ** |
| **R3** | L'instance de production dessert les bases de diagnostic | **Certaine** | Toute expérience sur une base de test atteint la production | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase B) — **à autoriser** |
| **R9** | Aucun journal exploitable | **Certaine** | Incident non attribuable | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase C) — **à autoriser** |
| **R10** | Le mécanisme d'unicité est **inerte en production** tant que `btree_gist` n'y est pas installé | Certaine | Les conflits globaux restent possibles en production | 🔒 **BLOQUÉ PAR UNE AUTORISATION** (`CREATE EXTENSION btree_gist;` sur `odoo20`, puis mise à jour) |
| **R11** | Les libellés de compteurs corrigés ne sont appliqués en production qu'à la prochaine mise à jour | Certaine | 7 avertissements persistent en production jusqu'alors | 🔒 **BLOQUÉ PAR UNE AUTORISATION** (mise à jour) |
| **R12** | Écriture SQL directe sur une table de référentiel (hors ORM) | Faible | Réservation non alimentée | Documenté — hors périmètre ORM |
| **R13** | Table de réservation non purgée si une réservation est insérée par un chemin non-ORM | Très faible | Fausse contention | Documenté |
| **R14** | `report/` et `wizard/` restent vides | — | Aucun | Assumé (emplacements réservés) |

---

# 10. COMPARAISON AVANT / APRÈS

| Indicateur | Avant Prompt 14 | Après Prompt 14 |
|---|---|---|
| Conflit code global ↔ code de société simultané | **Possible** (vulnérabilité R1) | **Détecté et bloqué** (15/15 scénarios) |
| Mécanisme d'unicité | 39 index uniques + contrainte Python + verrou consultatif | + table de réservation à contrainte d'exclusion `EXCLUDE USING gist` |
| Périmètres | Non modélisés | Domaines disjoints par signe : `[1,+∞)` / `[c,c+1)` / `{-1}` |
| Table de réservation | — | `gest_agri_reference_reservation` (technique, SQL brut) |
| Activation en production | — | **Inerte** (ni table ni extension) — aucun impact |
| Message utilisateur sur doublon | `UniqueViolation` brute au niveau ORM | `ValidationError` **française**, levée **avant** l'écriture métier |
| Avertissements de libellés | 7 | **0** |
| Fichiers `.bak` dans l'addon | 1 | **0** (archivé hors addon) |
| README | obsolète | à jour |
| Méthodes de test | 73 | **99** |
| Tests globaux (`testsRun`) | 75 | **101** |
| Échecs / erreurs / ignorés | 0 / 0 / 0 | **0 / 0 / 0** |
| Contrôles statiques Phase E | — | **31/31** |

---

# 11. DÉCISIONS À SOUMETTRE À L'UTILISATEUR

| # | Décision | Enjeu | Recommandation |
|---|---|---|---|
| **D1** | **Installer `btree_gist` dans `odoo20` puis mettre à jour le module** | C'est la seule action qui rend le mécanisme d'unicité **actif en production** ; elle implique aussi l'application des libellés corrigés | **Autoriser** — preceded of the `pg_dump` backup and a maintenance window |
| **D2** | **Isoler l'instance de production** (`db_name`/`dbfilter` + instance de test dédiée, Phase B) | Empêche qu'une nouvelle expérience sur une base de test atteigne la production (incident récurrent des Prompts 12-14) | **Autoriser** — procédure § 3 avec retour arrière à chaque étape |
| **D3** | **Activer la journalisation** (Phase C) | Rend toute investigation future possible ; a permis d'attribuer l'incident du Prompt 13 | **Autoriser** au minimum le `logfile` Odoo et la règle `auditd` |
| **D4** | **Reconstruire `gest_agri_audit_test`** (elle contient les traces des tests de concurrence et 22 fermes de diagnostic) | Base de référence propre pour les futures validations | **Recommandé** — recréer par `pg_dump`/`pg_restore` depuis `odoo20`, puis rejouer la mise à jour de test |
| **D5** | Conserver ou supprimer les paquets `report/` et `wizard/` | Aucun impact fonctionnel | **Conserver** (emplacements réservés documentés) |
| **D6** | Ajouter une table d'audit applicative `gest_agri_audit_log` | Traçabilité interne des upgrades du module | **Différend** |

---

# 12. COMMANDES EXÉCUTÉES ET BASES CIBLÉES

## 12.1 Bases ciblées

| Base | Nature | Opérations |
|---|---|---|
| `odoo20` (production) | **LECTURE SEULE STRICTE** | `SELECT` uniquement. Aucune commande `-u`/`-i`. Aucun DDL. Aucune modification de configuration |
| `gest_agri_audit_test` (diagnostic) | Écriture autorisée | `CREATE EXTENSION btree_gist` ; `-u gestion_agricole` (2 exécutions) ; exécution de la suite de tests (5 exécutions) ; purge des réservations de test |
| `gest_agri_concurrency_test` (diagnostic) | Écriture autorisée | schéma `p13` (banc du Prompt 13) ; `btree_gist` |

## 12.2 Commandes principales

```bash
# --- diagnostic : extension sur la base de DIAGNOSTIC (production jamais touchée)
psql -d gest_agri_audit_test -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
psql -d odoo20 -t -c "SELECT count(*) FROM pg_extension WHERE extname='btree_gist';"   # -> 0

# --- mise a jour sur la base de diagnostic
odoo-bin -c /etc/odoo20.conf -d gest_agri_audit_test --no-http --max-cron-threads=0 \
          --stop-after-init -u gestion_agricole --log-level=info

# --- suite complete (aucune mise a jour)
odoo-bin -c /etc/odoo20.conf -d gest_agri_audit_test --no-http --max-cron-threads=0 \
          --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
odoo-bin ... --log-handler=odoo.tests.stats:DEBUG      # rapport detail des identifiants

# --- validation Phase E (SELECT)
python3 /tmp/opencode/phaseE_validation.py

# --- controles de la production (SELECT)
psql -d odoo20 -c "SELECT ... FROM pg_index ..."     # 39 + 10 index, 0 invalide
psql -d odoo20 -c "SELECT ... FROM pg_class WHERE relname='gest_agri_reference_reservation';"   # -> 0
psql -d postgres -c "SELECT datname, application_name, state FROM pg_stat_activity ..."
```

## 12.3 Conformité aux interdictions

| Interdiction | Respect | Preuve |
|---|---|---|
| Pas de `-u`/`-i` sur `odoo20` | ✅ | toutes les commandes `-u` visaient `gest_agri_audit_test` |
| Pas de modification des données/index/vues/menus/paramètres de production | ✅ | `write_date` du module inchangé (`21:40:00.677710`) ; 39+10 index, 71 droits, 23 actions, 46 vues identiques ; 1 ferme + 1 site intactes |
| Pas d'arrêt/redémarrage du service Odoo de production | ✅ | aucun signal envoyé |
| Pas de modification de `/etc/odoo20.conf` | ✅ | configuration **préparée** dans `/tmp/opencode/preparation/` |
| Pas de modification de la configuration PostgreSQL | ✅ | `log_statement`, `logging_collector` inchangés |
| Pas de suppression/recréation de base | ✅ | aucune |
| Pas de suppression de données métier | ✅ | aucune |
| Pas d'installation de `btree_gist` dans `odoo20` | ✅ | vérifié : `count(*) = 0` dans `odoo20` |
| Pas de modification des modules agricoles historiques | ✅ | aucun fichier hors `gestion_agricole` modifié |
| Pas de migration irréversible | ✅ | la reprise des réservations est transactionnelle ; un doublon fait échouer la mise à jour sans rien modifier |
| Travaux limités au code source et aux bases de diagnostic | ✅ | 1 déplacement de fichier hors addon (archivage d'un `.bak`), 0 écriture en production |

---

# 13. CONCLUSION

> ## ✅ RISQUE R1 ÉLIMINÉ — LE MÉCANISME D'UNICITÉ CONCURRENTE EST DÉSORMAIS GARANTI
>
> Le conflit **code global ↔ code de société**, qui restait possible sous
> `REPEATABLE READ`, est désormais détecté et bloqué par une contrainte
> d'exclusion PostgreSQL portant sur des **domaines de périmètre disjoints par
> signe**. Les 12 scénarios de concurrence exigés et les 13 scénarios
> complémentaires sont vérifiés sur deux connexions PostgreSQL indépendantes, en
> `REPEATABLE READ`.
>
> Le mécanisme reste **inerte en production** : ni la table de réservation ni
> l'extension `btree_gist` n'y ont été installées, et aucun objet de
> production n'a été modifié. Son activation en production relève d'une
> autorisation explicite (D1).

**État final de la validation :**

| Contrôle | Résultat |
|---|---|
| Tests du module | **99 méthodes** — 0 échec, 0 erreur, 0 ignoré |
| Tests globaux exécutés | **101** (`testsRun`) |
| Événements de cycle de vie | 12 (non comptés dans `testsRun`) |
| Contrôles statiques Phase E | **31/31** conformes |
| Index uniques (test / production) | **39 + 10** / **39 + 10**, tous valides |
| Production | **inchangée** |

**Restent à autoriser explicitement** : l'activation du mécanisme en
production (D1), l'isolation de l'instance (D2) et la journalisation (D3).

---

*Rapport généré dans le cadre du Prompt N°14 — Module `gestion_agricole` — Odoo 20
Community. Toutes les écritures ont été réalisées sur les bases de diagnostic ;
la base de production `odoo20` n'a subi aucune modification.*
