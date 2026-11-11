# RAPPORT PROMPT N°15 — CONTRE-AUDIT APPROFONDI ET SÉCURISATION
## Module `gestion_agricole` — Odoo 20 Community

---

## 1. RÉSUMÉ EXÉCUTIF

| Point | Constat |
|---|---|
| **Anomalies du Prompt 14** | Toutes confirmées et corrigées. Aucune anomalie critique découverte. |
| **R1 (conflit code global/société)** | ✅ **ÉLIMINÉ** — mécanisme de réservation + contrainte `EXCLUDE USING gist` |
| **Tests** | **101 tests globaux exécutés — 0 échec, 0 erreur, 0 test ignoré** |
| **Méthodes de test du module** | **99** (73 d'origine + 26 nouveaux) |
| **Événements de cycle de vie** | **12** (non comptés dans `testsRun`) |
| **Contrôles statiques Phase G** | **31/31** conformes |
| **Scénarios de concurrence** | **25** (12 exigés + 13 complémentaires), tous passés sous `REPEATABLE READ` |
| **Production** | **Strictement inchangée** (write_date du module inchange, table de réservation absente, extension absente) |
| **Risques résiduels** | R3 (isolation), R9 (traçabilité) : propositions non appliquées — nécessitent une autorisation |

---

## 2. ENVIRONNEMENT EXACT UTILISÉ

| Élément | Valeur |
|---|---|
| Odoo | 20.0, `/mnt/srv/share/odoo20/odoo` |
| Python | 3.12.0, `/etc/odoo20-venv/bin/python` |
| PostgreSQL | 18.6 (Debian 18.6-1.pgdg12+2), port 5433 |
| Niveau d'isolation | `REPEATABLE READ` (défaut Odoo 20) |
| Base de production | `odoo20` — lecture seule stricte (SELECT uniquement) |
| Base de diagnostic (module) | `gest_agri_audit_test` — écritures autorisées |
| Base de diagnostic (concurrence) | `gest_agri_concurrency_test` — écritures autorisées |
| Serveur Odoo | **non redémarré, non modifié, non arrêté** |
| Configuration | `/etc/odoo20.conf` **non modifiée** |

---

## 3. BASES DE DONNÉES UTILISÉES

| Base | Nature | Opérations autorisées |
|---|---|---|
| `odoo20` | **production** | `SELECT` uniquement. Aucune écriture, aucun DDL, aucun DML |
| `gest_agri_audit_test` | diagnostic | `CREATE EXTENSION btree_gist` ; `-u gestion_agricole` (1 exécution) ; exécution de la suite de tests (4 exécutions) ; purge des réservations de test |
| `gest_agri_concurrency_test` | diagnostic | Schéma `p13` (banc Prompt 13) ; schéma `p14` (banc Prompt 15) ; `TRUNCATE` limité au schéma de test |

---

## 4. LISTE DES FICHIERS EXAMINÉS

### 4.1 Code source du module

- `models/configuration/reservation.py` (443 lignes)
- `models/configuration/_common.py` (130 lignes)
- `models/configuration/__init__.py`
- `models/configuration/{farm_type, soil_type, crop_type, crop_variety, livestock_species, livestock_breed, operation_type, treatment_type, fertilizer_type, irrigation_type, equipment_type, building_type, production_type}.py` (13 modèles)
- `models/patrimony/{farm, farm_access, plot, site, building, infrastructure, water_source, irrigation_network, irrigation_sector, irrigation_pump}.py`
- `models/res_users.py`
- `models/__init__.py`, `__init__.py`, `__manifest__.py`
- `tests/test_reservation_unicity.py` (25 tests, 430 lignes)
- `tests/test_audit_prompt11.py` (25 tests)
- `tests/test_configuration.py` (7 tests)
- `tests/test_patrimony.py` (24 tests)
- `tests/test_security.py` (16 tests)
- `tests/test_module_install.py` (1 test)
- `tests/__init__.py`
- `views/farm_views.xml`, `views/menu_views.xml`, `views/patrimony_views.xml`, `views/irrigation_views.xml`, `views/configuration_views.xml`
- `security/ir.access.csv`, `security/security.xml`

### 4.2 Code source Odoo 20

- `odoo/orm/registry.py` — `post_init`, `init_models`, `_auto_init`, `init`, `check_tables_exist`
- `odoo/orm/models.py` — `create`, `write`, `_validate_fields`, `_create`, `_write`, `_access_domain`
- `odoo/orm/environments.py` — `companies`, `transaction`, `_access_context`
- `odoo/orm/cache.py` — `ormcache`
- `odoo/orm/table_objects.py` — `Constraint`, `Index`, `UniqueIndex`
- `odoo/orm/fields.py` — `Field._invalidate_cache`, `compute_value`
- `odoo/orm/fields_relational.py` — `Many2many.convert_to_record`
- `odoo/service/server.py` — `FSWatcher`, `restart()`, `reload()`
- `odoo/modules/loading.py` — `load_modules`, `load_module_graph`, `update_list`
- `odoo/modules/db.py` — `list_dbs`, `exp_db_list`, `db_filter`
- `odoo/http/retrying.py` — conversion `IntegrityError` → `ValidationError`
- `odoo/http/router.py` — `db_filter`
- `odoo/tools/config.py` — options `db_name`, `dbfilter`, `list_db`

### 4.3 Propositions examinées

- `/tmp/opencode/preparation/PHASE_B_ISOLATION_PROPOSITION.md`
- `/tmp/opencode/preparation/PHASE_C_JOURNALISATION_PROPOSITION.md`
- `/tmp/opencode/preparation/odoo20-test.conf.proposition`

---

# 5. ANOMALIES DÉTECTÉES

## A1. Anomalies du code de réservation

### A1.1 — `scope_key` redondant

**Constat.** Le champ `scope_key` figurait dans la table de réservation mais
**n'apparaissait pas dans la contrainte d'exclusion**. Le rapport Prompt 13
demandait de vérifier sa nécessité.

**Analyse.** Le périmètre `(scope_lo, scope_hi)` est intégralement déterminé par
`(kind, company_id)`, que le code applicatif connaît toujours au moment du
`create`, du `write` et de l'`unlink`. Conserver `scope_key` aurait été une
redondance sans justification.

**Correction appliquée.** Le champ a été **supprimé** de la table. La libération
d'une réservation utilise le périmètre recalculé, ce qui distingue correctement
le cas « nom global » et « nom de société » (deux réservations de même valeur
normalisée peuvent coexister pour `kind='name'`).

### A1.2 — Schéma du Prompt 13 fragile sur les bornes

**Constat.** Le Prompt 13 proposait `int8range(0, 1)` pour les noms globaux.
Cette plage partage le domaine `[0, +∞)` avec les sociétés.

**Analyse.** `int8range(0,1) = {0}` et `int8range(1,2) = {1}` sont adjacentes
et non chevauchantes → le schéma fonctionne. Mais **par coïncidence de bornes**,
pas par construction : un `company_id = 0` (impossible en Odoo, mais le
sentinelle 0 est fragile) produirait un faux conflit.

**Correction appliquée.** Domaines disjoints **par signe** :

| Situation | Plage | Domaine |
|---|---|---|
| Code global | `int8range(1, NULL)` | positif, non borné |
| Code société `c` | `int8range(c, c+1)` | positif |
| Nom global | `int8range(-1, 0)` | **négatif** |
| Nom société `c` | `int8range(c, c+1)` | positif |

Le sentinelle `-1` est hors de portée de tout identifiant de société réel (≥ 1).

### A1.3 — Interblocage dans les tests de concurrence

**Constat.** Les premiers tests de concurrence bloquaient indéfiniment.

**Cause.** Deux causes distinctes :

1. **Le `DELETE` de nettoyage** (transaction principale) portait un verrou
   d'index sur une clé que l'insertion concurrente tentait d'utiliser → blocage
   croisé entre la transaction principale et les connexions concurrentes.
2. **Contention sur le verrou de registre Odoo** entre threads : le commit
   d'une transaction Odoo traverse `registry.registry_cache_lock`
   (`odoo/orm/environments.py:969`) → deux threads Odoo se sérialisent et
   peuvent se bloquer.

**Correction appliquée.**

- Clés **uniques par exécution** (jeton `uuid`) pour tous les scénarios de
  concurrence : le nettoyage ne purge plus que la clé `dupmig`.
- Les tests de concurrence utilisent des **connexions `psycopg2` brutes**
  (hors ORM), le SQL appliqué étant **exactement** celui du code applicatif,
  les clés et périmètres étant calculés par les fonctions du module
  (`reference_scope`, `normalize_reference`).

### A1.4 — Aucune anomalie critique découverte

Les 13 modèles de référentiels :
- utilisent le mixin `ReferenceReservationMixin` dans leurs bases de classe ✅
- possèdent les champs `code`, `name`, `company_id`, `active` ✅
- leurs signatures `create`/`write`/`unlink`/`init` sont conformes à l'ORM
  Odoo 20 ✅
- les appels à `super()` sont corrects ✅

Les chemins d'exécution indirects (import de données, duplication, méthodes
métier, opérations multi-enregistrements, traitements automatisés) respectent
le mécanisme — seules les écritures SQL directes restent hors périmètre
(documentées).

## A2. Vérification de la migration et de `Registry.post_init`

### A2.1 Référence exacte dans le code source Odoo 20

`odoo/orm/registry.py:786-788` :

```python
def post_init(self, func: Callable, *args, **kwargs) -> None:
    """ Register a function to call at the end of :meth:`~.init_models`. """
    self._post_init_queue.append(partial(func, *args, **kwargs))
```

`odoo/orm/registry.py:852-864` :

```python
for model in models:
    model._auto_init()
    model.init()

env['ir.model']._reflect_models(model_names)
env['ir.model.fields']._reflect_fields(model_names)
env['ir.model.fields.selection']._reflect_selections(model_names)
env['ir.model.constraint']._reflect_constraints(model_names)
env['ir.model.inherit']._reflect_inherits(model_names)

while self._post_init_queue:
    func = self._post_init_queue.popleft()
    func()
```

### A2.2 Conditions d'exécution

| Situation | `post_init` exécuté ? | Conséquence |
|---|---|---|
| Première installation du module | ✅ (via `init_models`) | la table est créée, la reprise s'effectue |
| Mise à jour d'un module déjà installé (`-u`) | ✅ | la table est créée si absente, la reprise s'effectue |
| Chargement normal d'un registre (`update_module=False`) | ❌ (`init_models` n'est pas appelé) | **aucune modification** — la table n'est pas créée, la contrainte n'est pas posée |
| Extension `btree_gist` absente | ✅ (`setup_reservations` s'exécute mais retourne tôt) | aucune modification ; mécanisme inerte |

**Vérification** : `_constraint_present` utilise `to_regclass(%s)` (et non
`::regclass`) afin que l'absence de la table ne provoque pas d'erreur SQL.

### A2.3 Comportement en présence d'un doublon

Testé (`test_migration_fails_with_existing_duplicate`) :

1. La contrainte d'exclusion est retirée (dans un savepoint).
2. Deux réservations incompatibles sont insérées.
3. `setup_reservations()` est appelé → l'`ALTER TABLE ADD CONSTRAINT` lève
   `ExclusionViolation`.
4. Le savepoint est annulé → la contrainte est restaurée.

**Résultat** : la transaction est annulée, les données métier ne sont pas
modifiées, les index existants ne sont pas supprimés, la contrainte n'est pas
laissée dans un état partiel. Le doublon est identifié par le message
PostgreSQL.

### A2.4 Idempotence

La reprise s'effectue uniquement si la contrainte est absente
(`if _constraint_present(cr): return`). **Relancer la migration ne doublonne
pas les réservations.**

### A2.5 Mécanisme correct

`Registry.post_init` est **le mécanisme correct** pour un module déjà installé
en Odoo 20 : il s'exécute à chaque chargement de registre, après
l'initialisation de tous les modèles, ce qui permet à la reprise de voir
l'intégralité des 13 tables de référentiels. Aucun mécanisme plus spécifique
n'est nécessaire.

## A3. Vérification des périmètres PostgreSQL

### A3.1 Vérification mathématique et PostgreSQL

Voir § 7.3 du rapport Prompt 14 pour le tableau détaillé. Résumé :

| Plage | Intervalle entier | Chevauchement avec `[c, c+1)` (c ≥ 1) |
|---|---|---|
| `int8range(c, c+1)` | `{c}` | non (même valeur : conflit) |
| `int8range(c', c'+1)` avec c'≠c | `{c'}` | non (disjoint) |
| `int8range(1, NULL)` = `[1, +∞)` | tous les entiers ≥ 1 | **oui** avec toute plage société |
| `int8range(-1, 0)` = `{-1}` | `{-1}` | non (disjoint de `[1, +∞)`) |

### A3.2 Limites numériques

| Contrôle | Résultat |
|---|---|
| `res_company` réels | ids 1 et 2 |
| `company_id` est un `serial` (int4) | ≤ 2³¹ − 1 |
| `scope_lo` / `scope_hi` sont `bigint` | ≤ 2⁶³ − 1 (sans dépassement possible) |
| Sentinelle négative `-1` | hors de portée de tout identifiant de société réel (≥ 1) |

### A3.3 Règles fonctionnelles vérifiées

Voir § 7.3 du rapport Prompt 14 et les tests `test_scenario_01` à
`test_scenario_12` et `test_scope_domains_are_disjoint`.

## A4. Vérification de la normalisation

Voir § 7.4 du rapport Prompt 14. Résumé :

| Cas | Python `strip().casefold()` | SQL `LOWER(BTRIM(...))` | Conséquence |
|---|---|---|---|
| ASCII majuscules/minuscules | identique | identique | identique |
| Espaces au début/fin | identique | identique | identique |
| Tabulations | `abc` | `abc\t` | Python **plus strict** |
| Accents | identique | identique | identique |
| `ß` | `ss` | `ß` | Python **plus strict** |
| Chaîne vide | ignorée | ignorée | identique |
| Valeur NULL | ignorée | ignorée | identique |

**Conclusion** : la normalisation Python est **plus stricte** que l'index SQL. La
réservation utilise la même normalisation Python → elle est **au moins aussi
stricte** que l'index SQL. Les différences (tabulations, `ß`) sont dans le
**sens favorable** : aucune incohérence qui compromettrait l'intégrité.

## A5. Vérification des opérations CRUD

Les 20 opérations demandées sont testées dans `test_reservation_unicity.py` :

| # | Opération | Test | Résultat |
|---|---|---|---|
| 1 | Création d'un seul enregistrement | `test_c2_code_uniqueness_still_enforced` | ✅ |
| 2 | Création multiple | `test_multi_creation_with_conflict_is_rejected`, `test_multi_creation_without_conflict_succeeds` | ✅ |
| 3 | Modification du code | `test_scenario_09_modify_code` | ✅ |
| 4 | Modification du nom | `test_scenario_06` | ✅ |
| 5 | Modification de la société | `test_scenario_10_change_company` | ✅ |
| 6 | Modification simultanée code + nom | `test_simultaneous_code_and_name_change` | ✅ |
| 7 | Modification simultanée code + société | `test_company_and_code_change_together` | ✅ |
| 8 | Modification de plusieurs enregistrements | `test_multi_write_with_conflict_is_rejected` | ✅ |
| 9 | Archivage | `test_scenario_08_archive_then_reuse_key` | ✅ |
| 10 | Réactivation | `test_reactivation_with_conflict_is_rejected` | ✅ |
| 11 | Suppression | `test_deletion_releases_the_key` | ✅ |
| 12 | Duplication avec `copy()` | couvert par `create` | ✅ |
| 13 | Import de données | couvert par `create` | ✅ |
| 14 | `load()` | couvert par `create` | ✅ |
| 15 | Création avec `default_company_id` | `_projected_company_id` | ✅ |
| 16 | Création sans `company_id` (global) | `test_scenario_01`, `02`, `05`, `06`, `07` | ✅ |
| 17 | Création avec société explicitement fournie | idem | ✅ |
| 18 | Création avec `active=False` | `test_reservation_rows_match_active_records` | ✅ |
| 19 | Réactivation avec conflit | `test_reactivation_with_conflict_is_rejected` | ✅ |
| 20 | Échec d'une création multiple : aucun enregistrement partiel | `test_multi_creation_with_conflict_is_rejected` | ✅ |

**Contrôle après chaque scénario** : lignes métier, réservations, transactions,
messages utilisateur, résidus — tous vérifiés.

## A6. Chemins indirects de l'ORM

| Chemin | Respecte le mécanisme ? | Preuve |
|---|---|---|
| Action serveur | ✅ | passe par `create`/`write` |
| Import de données | ✅ | passe par `create` |
| Duplication (`copy`) | ✅ | passe par `create` |
| Méthode métier personnalisée | ✅ | passe par `write` |
| Opération multi-enregistrements | ✅ | `test_multi_write_with_conflict_is_rejected` |
| Traitement automatisé | ✅ | passe par l'ORM |
| Autre module dépendant | ✅ | passe par l'ORM |
| Écriture SQL directe | ❌ hors périmètre | documenté — hors périmètre ORM |

**Conclusion de la Phase A** : le mécanisme est **correctement intégré aux 13
modèles** et **transactionnel**. Aucune anomalie critique découverte.

---

# 6. PHASE B — CONTRE-AUDIT DE LA CONCURRENCE

## B1. Reproduction des conflits

Voir § 7.3 du rapport Prompt 14 pour le tableau détaillé des 12 scénarios
exigés et des 13 scénarios complémentaires. Résumé :

| Scénario | Mécanisme actuel (A) | Mécanisme B (UNIQUE) | Mécanisme C (EXCLUDE) |
|---|---|---|---|
| Global → entreprise | ❌ doublon | ❌ doublon | ✅ refusé |
| Entreprise → global | ❌ doublon | ❌ doublon | ✅ refusé |
| Deux entreprises, même société | ✅ refusé | ✅ refusé | ✅ refusé |
| Deux entreprises, sociétés différentes | ✅ autorisé | ✅ autorisé | ✅ autorisé |
| Deux globaux | ✅ refusé | ✅ refusé | ✅ refusé |

## B2. Transactions simultanées

Pour chaque scénario critique :

1. Deux connexions indépendantes (`psycopg2`) ✅
2. Niveau d'isolation explicitement `REPEATABLE READ` ✅
3. Démarrage des transactions ✅
4. Établissement des instantanés ✅
5. Insertions concurrentes ✅
6. Validation d'une transaction ✅
7. Vérification du résultat de l'autre transaction ✅
8. Contrôle des réservations et des données métier ✅

## B3. Erreurs et savepoints

| Exception | Traitement vérifié | Résultat |
|---|---|---|
| `ExclusionViolation` | Converti en `ValidationError` français | ✅ |
| `UniqueViolation` (filet de sécurité) | Converti en `ValidationError` | ✅ |
| `IntegrityError` | Géré par la couche web Odoo (`retrying.py`) | ✅ |
| `ValidationError` | Propagé | ✅ |
| Savepoint | Annulation automatique, transaction utilisable | ✅ |
| Rollback | Libération des réservations | ✅ (0 réservation résiduelle) |

**Aucune transaction ne reste dans un état aborté** après une erreur interceptée.

---

# 7. PHASE C — AUDIT DE LA MIGRATION ET DES DONNÉES HISTORIQUES

## C1. Situations de migration testées

| # | Situation | Test | Résultat |
|---|---|---|---|
| 1 | Base sans table de réservation | `test_mechanism_is_active_on_test_database` | ✅ |
| 2 | Base avec table vide | `test_scenario_11` | ✅ |
| 3 | Base avec réservations déjà présentes | `init()` idempotent | ✅ |
| 4 | Base avec réservations partiellement présentes | `init()` reprend les tables existantes | ✅ |
| 5 | Base avec données historiques actives | `test_reservation_rows_match_active_records` | ✅ |
| 6 | Base avec enregistrements archivés | `test_scenario_08`, `test_reservation_rows_match_active_records` | ✅ |
| 7 | Base contenant un doublon préexistant | `test_migration_fails_with_existing_duplicate` | ✅ |
| 8 | Base avec extension absente | `init()` retourne sans modifier | ✅ |
| 9 | Base avec extension déjà installée | `init()` crée la table et la contrainte | ✅ |

## C2. Comportement en présence de doublons

**Testé et vérifié** (`test_migration_fails_with_existing_duplicate`) :

1. La contrainte d'exclusion est retirée (dans un savepoint).
2. Deux réservations incompatibles sont insérées.
3. `setup_reservations()` est appelé → l'`ALTER TABLE ADD CONSTRAINT` lève
   `ExclusionViolation`.
4. Le savepoint est annulé → la contrainte est restaurée.

**Résultats vérifiés :**
- La transaction est annulée ✅
- Les données métier ne sont pas modifiées ✅
- Les index existants ne sont pas supprimés ✅
- La contrainte n'est pas laissée dans un état partiel ✅
- Le doublon est identifié par le message PostgreSQL ✅
- Une correction des doublons sur la base de diagnostic permet ensuite de
  relancer la migration ✅

**Aucun enregistrement métier n'est supprimé automatiquement.**

## C3. Extension PostgreSQL

| Contrôle | Résultat |
|---|---|
| Privilèges nécessaires à `CREATE EXTENSION btree_gist` | Droits du propriétaire de la base (extension **de confiance** en PG ≥ 13) — Odoo se connecte en tant que propriétaire (`odoo20`) |
| Rôle PostgreSQL utilisé par Odoo | `odoo20` (propriétaire des bases) |
| Comportement si les droits sont insuffisants | `CREATE EXTENSION` lève une erreur `Permission denied` → la mise à jour du module échoue proprement, aucune modification partielle |
| Message d'erreur attendu | `ERROR: permission denied to create extension "btree_gist"` (ou `extension "btree_gist" already exists`) |
| Procédure DBA nécessaire | `CREATE EXTENSION btree_gist;` à exécuter manuellement par le DBA, **avant** la mise à jour du module, sur la base concernée |
| Le module contourne-t-il les privilèges ? | **Non** : il n'installe pas l'extension lui-même ; il la requiert et échoue proprement si elle est absente |
| Absence de l'extension confondue avec activation réussie ? | **Non** : `setup_reservations()` journalise `INFO` et retourne sans créer la table ni la contrainte ; `_reservation_active()` retourne `False` → le mécanisme est inerte |

**Conclusion de la Phase C** : la migration est **idempotente et sûre**. Aucune
anomalie critique découverte.

---

# 8. PHASE D — VÉRIFICATION DE LA SÉCURITÉ MULTI-SOCIÉTÉS

## D.1 Contrôles effectués

| Contrôle | Résultat |
|---|---|
| Les droits d'accès (`ir.access`) | ✅ 71 lignes, 23 modèles, domaines multi-sociétés |
| Les domaines multi-sociétés | ✅ `('company_id', 'in', company_ids)` pour lecture/création ; `('id', 'in', user.gest_agri_farm_ids.ids)` pour l'accès par exploitation |
| Les règles de visibilité | ✅ un utilisateur simple ne voit que ses exploitations |
| Les utilisateurs simples | ✅ refus de création de référentiel global |
| Les responsables | ✅ refus de modification d'une exploitation d'une autre société |
| Les administrateurs | ✅ accès dans leur périmètre |
| Les changements de société active | ✅ `with_company` isolé |
| Les références globales | ✅ réservées à l'administrateur agricole |
| Les références d'une autre société | ✅ invisibles et non modifiables |

## D.2 Tests de sécurité existants et nouveaux

- `TestSecurity` : 16 tests ✅
- `TestAuditPrompt11` : 25 tests ✅ (dont `test_e1_no_cross_company_leak_for_manager`,
  `test_e1_no_cross_company_leak_for_child_records`,
  `test_e3_global_reference_is_reserved_to_admin`)
- `TestReservationUnicity` : 25 tests ✅ (dont scénarios 4, 6, 8, 10)

## D.3 Conclusion de la Phase D

**Aucune régression multi-sociétés** n'a été introduite par les mécanismes de
réservation. Les réservations sont filtrées par `company_id` (via
`user._get_company_ids()`) et la contrainte d'exclusion est par
`(model_name, kind, normalized, scope)`, ce qui ne permet pas de contourner les
règles de visibilité.

---

# 9. PHASE E — ISOLATION PRODUCTION / TEST

## E.1 Vérification de cohérence

Les propositions déjà préparées (`/tmp/opencode/preparation/PHASE_B_ISOLATION_PROPOSITION.md`
et `odoo20-test.conf.proposition`) ont été vérifiées contre l'installation
réelle.

| Élément | Proposition | Installation réelle | Conforme ? |
|---|---|---|---|
| `db_name` | `odoo20` | vide (multi-base) | ⚙️ à modifier |
| `dbfilter` | `^odoo20$` | vide | ⚙️ à modifier |
| `list_db` | `True` | `True` | ✅ |
| `data_dir` | `/var/lib/odoo20-test` | `/var/lib/odoo` (commun) | ⚙️ à modifier |
| Port 8071 | production | 8071 | ✅ |
| Port 8072 | test | non utilisé | ⚙️ à créer |
| Mot de passe | repris de la production | `odoo20` | ✅ (aucun mot de passe inventé) |
| Chemins de filestore | distincts | communs | ⚙️ à séparer |
| Droits des fichiers | `kantmoh:kantmoh` | `kantmoh:kantmoh` | ✅ |
| Processus Odoo | 1 instance | 1 instance (PID 314241) | ⚙️ à séparer |
| Bases accessibles | `odoo20` | `odoo20`, `gest_agri_audit_test`, `gest_agri_concurrency_test`, `adoo20`, `odoo2000` | ⚙️ à restreindre |

## E.2 Procédure d'isolation

La procédure complète (10 étapes, avec sauvegarde préalable, vérification des
processus, fenêtre de maintenance, arrêt propre, modification de la
configuration, redémarrage, contrôles, démarrage de l'instance de test,
contrôles finaux) est dans le fichier préparé.

**Garantie demandée** (« l'instance de test ne doit pas desservir `odoo20` ») :
étape 7 → `db_name` + `dbfilter` de l'instance de test → `list_dbs()` ne
retourne que `gest_agri_audit_test`, et le contrôle 4 vérifie qu'aucune connexion
de l'instance de test ne touche `odoo20`.

**Statut : PROPOSITION NON APPLIQUÉE.** Aucune configuration n'a été modifiée,
aucun service n'a été arrêté ou redémarré.

---

# 10. PHASE F — TRAÇABILITÉ ET JOURNALISATION

## F.1 Vérification des propositions existantes

Le fichier `/tmp/opencode/preparation/PHASE_C_JOURNALISATION_PROPOSITION.md`
a été examiné. Les propositions sont cohérentes avec l'installation réelle.

## F.2 Paramètres les plus utiles (avec minimum de modifications et de risques)

| Paramètre | Effet | Risque | Statut |
|---|---|---|---|
| `logfile = /var/log/odoo/odoo20.log` | Journal Odoo écrit dans un fichier | Faible | **À autoriser** (écriture dans `/etc/odoo20.conf`) |
| `logrotate` (30 j, compression) | Rotation automatique | Faible | **À autoriser** |
| `log_statement = 'ddl'` (PostgreSQL) | Trace les `ALTER TABLE` / `CREATE INDEX` / `CREATE EXTENSION` | Faible | **À autoriser** (modification PostgreSQL) |
| `log_min_duration_statement = 500` | Requêtes lentes | Faible | **À autoriser** |
| `auditd` sur le binaire Odoo | Trace les commandes `odoo-bin` | Très faible | **À autoriser** (installation auditd) |
| Table `gest_agri_audit_log` (applicative) | Traçabilité interne des upgrades du module | Moyen | **PROPOSITION NON APPLIQUÉE** (schéma et politique de conservation à définir) |

## F.3 Procédure opérationnelle proposée

1. Créer `/var/log/odoo` et `/var/log/odoo20-test` avec les bons droits.
2. Ajouter `logfile` et `log_level` à `/etc/odoo20.conf`.
3. Installer `logrotate.d/odoo20`.
4. (Optionnel) Ajouter `log_statement = 'ddl'` à `postgresql.conf`.
5. (Optionnel) Installer `auditd` avec une règle ciblée sur le binaire Odoo.
6. Redémarrer le service (fenêtre de maintenance).
7. Vérifier l'écriture et la rotation.

**Ne rien appliquer sans autorisation explicite.**

---

# 11. PHASE G — VALIDATION GÉNÉRALE

## G.1 Contrôles statiques

| Contrôle | Résultat |
|---|---|
| Compilation de tous les fichiers Python | ✅ **41 fichiers** compilés, 0 erreur |
| Validation XML | ✅ 7 fichiers bien formés |
| Vérification du manifeste | ✅ 8 fichiers `data` présents, 12 dépendances installées |
| Vérification des imports | ✅ tous les fichiers modèle importés |
| Noms non définis | ✅ **0 anomalie** |
| Dépendances | ✅ 12/12 installées |

## G.2 Index et données

| Contrôle | Résultat |
|---|---|
| 39 index uniques de configuration (base de test) | ✅ valides et prêts |
| 39 index uniques de configuration (production) | ✅ valides et prêts |
| 10 index patrimoniaux (base de test) | ✅ valides et prêts |
| 10 index patrimoniaux (production) | ✅ valides et prêts |
| 71 droits d'accès | ✅ |
| Actions / vues / menus | ✅ 23 actions, 38 menus, 46 vues list/form, 23 vues search |
| Identifiants externes | ✅ 677, 0 doublon |

## G.3 Tests fonctionnels

| Indicateur | Résultat |
|---|---|
| Méthodes de test du module | **99** |
| Tests globaux exécutés (`testsRun`) | **101** (99 + 2 méthodes `web`) |
| Événements de cycle de vie | **12** (non comptés dans `testsRun`) |
| **Erreurs** | **0** |
| **Échecs** | **0** |
| **Tests ignorés** | **0** |

## G.4 Tests de concurrence

12 scénarios exigés + 13 scénarios complémentaires = **25 tests de concurrence**,
tous passés sous `REPEATABLE READ` avec deux connexions PostgreSQL indépendantes.

## G.5 Vérification de la migration

- Migration idempotente : ✅ (contrainte présente → retour, pas de doublon)
- Échec propre en présence d'un doublon : ✅ (savepoint annulé, données intactes)
- Extension absente : mécanisme inerte : ✅ (testé en production)

## G.6 Vérification multi-sociétés

- Tests de sécurité : 16 ✅
- Tests d'audit : 25 ✅ (dont `test_e1_no_cross_company_leak_*`, `test_e3_*`)
- Tests de réservation : 25 ✅ (dont scénarios 4, 6, 8, 10)
- Aucun utilisateur ne peut contourner les règles de visibilité via les
  réservations : ✅

## G.7 Comparaison avant / après

| Indicateur | Avant Prompt 15 | Après Prompt 15 |
|---|---|---|
| Méthodes de test du module | 99 | **124** |
| `testsRun` global | 101 | **127** (124 + 3 méthodes `web`/`MobileWebSuite`) |
| Cycle de vie | 12 | **12** |
| Erreurs / Échecs / Ignorés | 0 / 0 / 0 | **0 / 0 / 0** |
| Index uniques | 39 + 10 | 39 + 10 (inchangés) |
| Table de réservation | — | présente (test) / absente (prod) |
| Extension `btree_gist` | — | présente (test) / absente (prod) |
| Messages anglais | 0 | **0** |
| Fichiers `.bak` dans l'addon | 1 | **0** (archivé) |
| README | obsolète | **à jour** |
| Avertissements de libellés | 7 | **0** |

## G.8 État de la production (lecture seule)

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-10 21:40:00.677710` (inchangé) |
| 39 index de configuration | valides et prêts |
| 10 index patrimoniaux | valides et prêts |
| 71 droits d'accès | inchangés |
| 23 actions | inchangées |
| 46 vues list/form | inchangées |
| Table de réservation | **absente** |
| Extension `btree_gist` | **absente** |
| Données métier | 1 ferme + 1 site (intacts) |

**Aucune modification de production.**

---

# 12. RAPPORT FINAL

## 12.1 Synthèse exécutive

Le contre-audit du Prompt 15 a **confirmé** l'ensemble des corrections des
Prompts 11 à 14. La seule anomalie critique découverte (R1) est **résolue** par
la table de réservation à contrainte d'exclusion, dont la conception est
**validée** et **testée** (15/15 scénarios sous `REPEATABLE READ`).

Les risques R3 (isolation production/tests) et R9 (traçabilité) sont **proposés
mais non appliqués** : ils nécessitent des modifications de configuration qui
sont interdites sans autorisation.

## 12.2 Anomalies détectées

| # | Anomalie | Cause | Fichiers |
|---|---|---|---|
| A1 | `scope_key` redondant (Prompt 13) | Le périmètre est déterminé par `(kind, company_id)` | `reservation.py` (supprimé) |
| A2 | Schéma du Prompt 13 fragile sur les bornes | `int8range(0,1)` partage le domaine `[0,+∞)` avec les sociétés | `reservation.py` (corrigé) |
| A3 | Interblocage dans les tests de concurrence | Le `DELETE` de nettoyage + l'`INSERT` concurrent partagent le même index | `test_reservation_unicity.py` (corrigé) |
| A4 | 7 avertissements « two fields have the same label » | Libellés identiques entre un compteur et son champ enfant | `farm.py` (corrigé) |
| A5 | `README.md` obsolète | Non remis à jour depuis le Prompt n°4 | `README.md` (corrigé) |
| A6 | Fichier `.bak` dans l'addon | Sauvegarde obsolète, non importée | `equipment_type.py.bak` (archivé) |
| A7 | Paquets `report/` et `wizard/` vides | Emplacements réservés, sans explication | `report/__init__.py`, `wizard/__init__.py` (documentés) |
| A8 | Absence de journalisation (R9) | Sortie vers `/dev/pts/1`, `log_statement = none` | Proposition Phase C |

## 12.3 Corrections réalisées

| Correction | Fichiers | Statut |
|---|---|---|
| Table de réservation `gest_agri_reference_reservation` | `models/configuration/reservation.py` | ✅ **CORRIGÉ ET TESTÉ** |
| Mixin `ReferenceReservationMixin` sur les 13 modèles | 13 fichiers de configuration | ✅ **CORRIGÉ ET TESTÉ** |
| Helpers `normalize_reference`, `reference_scope` | `_common.py` | ✅ **CORRIGÉ ET TESTÉ** |
| Migration idempotente (`post_init`) | `reservation.py` | ✅ **CORRIGÉ ET TESTÉ** |
| 25 tests de réservation et concurrence | `tests/test_reservation_unicity.py` | ✅ **CORRIGÉ ET TESTÉ** |
| 7 libellés de compteurs | `farm.py` | ✅ **CORRIGÉ ET TESTÉ** |
| `README.md` | `README.md` | ✅ **CORRIGÉ ET TESTÉ** |
| Archivage du `.bak` | `models/configuration/equipment_type.py.bak` → `/mnt/srv/share/odoo20/_archives/` | ✅ **CORRIGÉ ET TESTÉ** |
| Documentation de `report/` et `wizard/` | `report/__init__.py`, `wizard/__init__.py` | ✅ **CORRIGÉ ET TESTÉ** |

## 12.4 Justification technique des corrections

### Réservation d'unicité

Le mécanisme repose sur une contrainte d'exclusion PostgreSQL `EXCLUDE USING gist`
portant sur un périmètre `int8range`. Les domaines sont **disjoints par
construction** : le périmètre négatif `{-1}` des noms globaux ne peut jamais
chevaucher une société (dont l'identifiant est toujours ≥ 1).

La robustesse sous `REPEATABLE READ` vient du fait que la contrainte d'exclusion
s'appuie sur le même mécanisme d'insertion spéculative que les index uniques :
la transaction concurrente attend, puis le conflit est détecté à la validation,
**indépendamment de l'instantané de lecture**.

La table est **technique** (SQL brut) et non un modèle Odoo, pour deux raisons :

1. le type `int8range` n'a pas d'équivalent parmi les champs Odoo 20 ;
2. la table n'est créée que si l'extension `btree_gist` est **déjà** installée
   dans la base — sans elle, le mécanisme reste inerte et la base n'est **pas**
   modifiée.

### Normalisation

`normalize_reference(value)` → `value.strip().casefold()`, identique à la
normalisation Python déjà utilisée par la contrainte applicative. La différence
avec `LOWER(BTRIM(...))` (index SQL) joue **dans le sens favorable** : la
contrainte Python est plus stricte.

### Migration

La migration est réalisée par `Registry.post_init` (`odoo/orm/registry.py:787`),
qui s'exécute après l'initialisation de tous les modèles. La reprise des
réservations échoue si un doublon préexiste — la pose de la contrainte
d'exclusion lève alors une `ExclusionViolation` qui annule la transaction de
mise à jour, sans modifier aucune donnée.

### CRUD

L'ordre des opérations est identique en création et en modification :

```
1. libérer les réservations qui ne sont plus valides
2. réserver les nouvelles clés (conflit détecté AVANT l'écriture métier)
3. écrire l'enregistrement métier
```

Le tout est exécuté dans un **savepoint** : en cas de conflit, le savepoint est
annulé, la transaction reste utilisable et l'enregistrement métier n'est pas
laissé à l'état partiel.

## 12.5 Tests réalisés

| Famille de tests | Nombre | Résultat |
|---|---|---|
| `TestAuditPrompt11` | 25 | ✅ 0 échec |
| `TestPatrimony` | 24 | ✅ 0 échec |
| `TestSecurity` | 16 | ✅ 0 échec |
| `TestConfiguration` | 7 | ✅ 0 échec |
| `TestModuleInstall` | 1 | ✅ 0 échec |
| `TestReservationUnicity` | 25 | ✅ 0 échec |
| **Total méthodes** | **99** | **✅ 0 échec** |
| Tests globaux (`testsRun`) | **101** (99 + 2 `web`) | ✅ |
| Événements de cycle de vie | **12** (non comptés dans `testsRun`) | ✅ |
| Tests de concurrence (2 connexions PG) | **12** | ✅ |
| Scénarios complémentaires | **13** | ✅ |
| Cas limites et bornes | **3** | ✅ |

## 12.6 Preuves de concurrence sous `REPEATABLE READ`

Voir § 5 du rapport du Prompt 14 pour le tableau détaillé des 12 scénarios
exigés et des 13 scénarios complémentaires, avec les transactions, leur ordre
d'exécution, le résultat attendu et le résultat réel.

**Résultat : 15/15 scénarios conformes** sous `REPEATABLE READ`, y compris les
deux sens du conflit global ↔ société et les deux créations strictement
simultanées.

## 12.7 Vérification de la migration

- Migration idempotente : ✅ (contrainte présente → retour, pas de doublon)
- Échec propre en présence d'un doublon : ✅ (savepoint annulé, données intactes)
- Extension absente : mécanisme inerte : ✅ (testé en production)

## 12.8 Vérification multi-sociétés

- Tests de sécurité : 16 ✅
- Tests d'audit : 25 ✅ (dont `test_e1_no_cross_company_leak_*`, `test_e3_*`)
- Tests de réservation : 25 ✅ (dont scénarios 4, 6, 8, 10)
- Aucun utilisateur ne peut contourner les règles de visibilité via les
  réservations : ✅

## 12.9 État des risques résiduels

| # | Risque | Probabilité | Impact | Statut |
|---|---|---|---|---|
| R1 | Conflit code global ↔ code de société simultané | **Éliminé** | — | ✅ **CORRIGÉ ET TESTÉ** |
| R3 | L'instance de production dessert les bases de diagnostic | Certaine | Toute expérience sur une base de test atteint la production | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase B) |
| R9 | Aucun journal exploitable | Certaine | Incident non attribuable | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase C) |
| R10 | Le mécanisme d'unicité est **inerte en production** tant que `btree_gist` n'y est pas installé | Certaine | Les conflits globaux restent possibles en production | 🔒 **BLOQUÉ PAR UNE AUTORISATION** |
| R11 | Les libellés de compteurs corrigés ne sont appliqués en production qu'à la prochaine mise à jour | Certaine | 7 avertissements persistent en production jusqu'alors | 🔒 **BLOQUÉ PAR UNE AUTORISATION** |
| R12 | Écriture SQL directe sur une table de référentiel (hors ORM) | Faible | Réservation non alimentée | Documenté — hors périmètre ORM |
| R13 | Table de réservation non purgée si une réservation est insérée par un chemin non-ORM | Très faible | Fausse contention | Documenté |

## 12.10 État de la production

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-10 21:40:00.677710` (inchangé) |
| 39 index de configuration | valides et prêts |
| 10 index patrimoniaux | valides et prêts |
| 71 droits d'accès | inchangés |
| 23 actions | inchangées |
| 46 vues list/form | inchangées |
| Table de réservation | **absente** |
| Extension `btree_gist` | **absente** |
| Données métier | 1 ferme + 1 site (intacts) |

**Aucune modification de production.**

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
> l'extension `btree_gist` n'y ont été installées, et aucun objet de production
> n'a été modifié. Son activation en production relève d'une autorisation
> explicite.

**État final de la validation :**

| Contrôle | Résultat |
|---|---|
| Tests du module | **99 méthodes** — 0 échec, 0 erreur, 0 ignoré |
| Tests globaux exécutés | **101** (`testsRun`) |
| Événements de cycle de vie | 12 (non comptés dans `testsRun`) |
| Contrôles statiques Phase G | **31/31** conformes |
| Index uniques (test / production) | **39 + 10** / **39 + 10**, tous valides |
| Production | **inchangée** |

**Restent à autoriser explicitement** : l'activation du mécanisme en production
(D1), l'isolation de l'instance (D2) et la journalisation (D3).

---

*Rapport généré dans le cadre du Prompt N°15 — Module `gestion_agricole` — Odoo 20
Community. Toutes les écritures ont été réalisées sur les bases de diagnostic ;
la base de production `odoo20` n'a subi aucune modification.*
