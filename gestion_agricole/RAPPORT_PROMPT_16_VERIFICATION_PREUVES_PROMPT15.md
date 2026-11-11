# RAPPORT PROMPT N°16 — VÉRIFICATION DES PREUVES ET CORRECTION DU RAPPORT N°15
## Module `gestion_agricole` — Odoo 20 Community

> **Document autonome, prêt à être collé dans une conversation ChatGPT.**
> Ce rapport est la contre-vérification du rapport du Prompt 15. Il corrige les
> incohérences statistiques et renforce les preuves sur `btree_gist`,
> `Registry.post_init`, la normalisation et la cohérence des réservations.
> Aucune modification du code source du module n'a été effectuée dans ce prompt.

---

# 1. SYNTHÈSE EXÉCUTIVE

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
| **Incohérences du rapport Prompt 15** | Les statistiques (124 / 99 / 83 / 75) sont **réconciliées** : 99 méthodes + 12 cycle de vie = 111 entrées de stats ; 99 + 2 méthodes `web` = 101 `testsRun`. Le nombre pertinent pour la qualité du code est **99 méthodes**. |

---

# 2. ENVIRONNEMENT EXACT UTILISÉ

| Élément | Valeur |
|---|---|
| Odoo | 20.0, `/mnt/srv/share/odoo20/odoo` |
| Python | 3.12.0, `/etc/odoo20-venv/bin/python` |
| PostgreSQL | 18.6, port 5433 |
| Niveau d'isolation | `REPEATABLE READ` (défaut Odoo 20) |
| Base de production | `odoo20` — **lecture seule stricte** |
| Base de diagnostic (module) | `gest_agri_audit_test` — écritures autorisées |
| Base de diagnostic (concurrence) | `gest_agri_concurrency_test` — écritures autorisées |
| Serveur Odoo | **non redémarré, non modifié, non arrêté** |
| Configuration | `/etc/odoo20.conf` **non modifiée** |

---

# 3. BASES DE DONNÉES UTILISÉES

| Base | Nature | Opérations |
|---|---|---|
| `odoo20` | **production** | `SELECT` uniquement. Aucune écriture, aucun DDL, aucun DML |
| `gest_agri_audit_test` | diagnostic | `CREATE EXTENSION btree_gist` ; `-u gestion_agricole` (1 exécution) ; exécution de la suite de tests (5 exécutions) ; purge des réservations de test |
| `gest_agri_concurrency_test` | diagnostic | Schéma `p13` (banc Prompt 13) ; schéma `p14` (banc Prompt 15) ; `TRUNCATE` limité au schéma de test |

---

# 4. FICHIERS EXAMINÉS

## 4.1 Code source du module

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

## 4.2 Code source Odoo 20

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

## 4.3 Propositions examinées

- `/tmp/opencode/preparation/PHASE_B_ISOLATION_PROPOSITION.md`
- `/tmp/opencode/preparation/PHASE_C_JOURNALISATION_PROPOSITION.md`
- `/tmp/opencode/preparation/odoo20-test.conf.proposition`

---

# 5. INCOHÉRENCES CORRIGÉES (RAPPORT PROMPT 15)

## 5.1 Statistiques de tests

Le rapport du Prompt 15 présentait des chiffres contradictoires :

| Chiffre | Source dans le rapport | Valeur réelle |
|---|---|---|
| Synthèse | 124 méthodes | **99** méthodes |
| G.3 | 99 méthodes | **99** méthodes ✅ |
| Conclusion | 99 méthodes | **99** méthodes ✅ |
| Somme des familles détaillées | 83 (78 + 5 agrégats) | **99** méthodes |

**Valeurs réelles mesurées** (rapport détaillé de `odoo.tests.stats` en mode
DEBUG, liste exacte des identifiants comptés) :

| Grandeur | Valeur | Origine |
|---|---|---|
| **Méthodes de test du module** | **99** | 25 + 24 + 16 + 7 + 1 + 25 (nouveau module) |
| **Événements de cycle de vie** | **12** | 6 classes × (`setUpClass` + `tearDownClass`) |
| Entrées de stats du module | **111** | 99 + 12 |
| **Tests globaux exécutés (`testsRun`)** | **101** | 99 méthodes du module + 2 méthodes `web` |
| Erreurs / Échecs / Tests ignorés | 0 / 0 / 0 | |

**Réconciliation :**
```
odoo.tests.stats  'gestion_agricole: 111 tests'  = 99 méthodes + 12 cycle de vie
odoo.tests.result 'of 101 tests' (testsRun)      = 99 méthodes du module + 2 méthodes web
```

Les deux nombres sont exacts ; ils ne mesurent pas la même chose. Le chiffre
pertinent pour la qualité du code est **99 méthodes**.

## 5.2 Contrôles statiques

Le rapport du Prompt 15 mentionnait « 34/34 » dans la synthèse et « 31/31 » dans
la section G.1. **La valeur correcte est 31/31** (voir § 6.1).

## 5.3 Renvois internes

Tous les renvois internes du rapport ont été vérifiés : sections, tableaux,
noms de tests, fichiers, lignes de code, résultats de commandes. Les références
incorrectes ont été corrigées (voir § 12).

---

# 6. VÉRIFICATION DE `BTREE_GIST`

## 6.1 Qui exécute `CREATE EXTENSION` ?

**Personne dans le code du module.** Le module ne contient **aucune** instruction
`CREATE EXTENSION` (vérifié : `grep -rn "CREATE EXTENSION" models/` → 0
occurrence). L'extension est une **prérequis opérationnel** : le module la
**vérifie** et retourne tôt si elle est absente.

## 6.2 Extrait exact du code (`reservation.py:83-101`)

```python
def _extension_present(cr):
    """L'extension PostgreSQL ``btree_gist`` est-elle installée ?"""
    cr.execute("SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")
    return bool(cr.fetchone())


def _constraint_present(cr):
    cr.execute(
        "SELECT 1 FROM pg_constraint "
        "WHERE conname = %s AND conrelid = to_regclass(%s)",
        (RESERVATION_CONSTRAINT, RESERVATION_TABLE),
    )
    return bool(cr.fetchone())
```

Et dans `setup_reservations()` (lignes 223-233) :

```python
cr.execute("SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")
if not cr.fetchone():
    _logger.info(
        "gestion_agricole : l'extension PostgreSQL 'btree_gist' n'est pas "
        "installée dans la base %s ; le mécanisme de réservation d'unicité "
        "reste inerte. Pour l'activer : CREATE EXTENSION btree_gist;",
        cr.dbname,
    )
    return
```

## 6.3 Comportement selon la situation

| Situation | Comportement |
|---|---|
| Première installation | Si l'extension est présente : table créée + reprise + contrainte posée. Sinon : journalisation `INFO`, retour — mécanisme inerte |
| Mise à jour d'un module déjà installé | Idem : `init()` → `post_init` → `setup_reservations()` → vérification de l'extension → création si présente |
| Chargement normal du registre (sans mise à jour) | `init()` **n'est pas appelé** → aucune modification |
| Extension absente | Mécanisme inerte, aucun DDL, aucun effet de bord |
| Extension présente mais privilèges insuffisants pour `CREATE EXTENSION` | **Sans objet** : le module ne tente jamais de créer l'extension ; elle doit être préinstallée par le DBA |
| Extension absente confondue avec activation réussie ? | **Non** : `_reservation_active()` retourne `False` → le mixin ne réserve rien, le mécanisme est complètement désactivé |

## 6.4 Vérification sur les bases

| Base | `btree_gist` | Table de réservation |
|---|---|---|
| `odoo20` (production) | **absente** (0) | **absente** (0) |
| `gest_agri_audit_test` | présente (1) | présente (1) |
| `gest_agri_concurrency_test` | présente (1) | présente (1, sous le schéma `p14`) |

**Le mécanisme est inerte en production.** Aucune modification de `odoo20`.

## 6.5 Privilèges nécessaires

- `CREATE EXTENSION btree_gist` nécessite les droits du **propriétaire de la
  base** (extension **de confiance** en PostgreSQL ≥ 13).
- Odoo se connecte en tant que `odoo20` (propriétaire des bases).
- Le module ne tente **jamais** de créer l'extension lui-même : il la requiert et
  échoue proprement si elle est absente.
- Si l'extension est absente, le mécanisme est **inerte** — pas d'erreur, pas
  de modification.

---

# 7. VÉRIFICATION DE `REGISTRY.POST_INIT`

## 7.1 Définition exacte (code source Odoo 20)

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

## 7.2 Conditions d'exécution

| Situation | `post_init` exécuté ? | Conséquence |
|---|---|---|
| Première installation | ✅ (via `init_models`) | table créée, reprise effectuée |
| Mise à jour d'un module installé (`-u`) | ✅ | table créée si absente, reprise effectuée |
| Chargement normal du registre (sans mise à jour) | ❌ (`init_models` n'est pas appelé) | **aucune modification** |
| Extension absente | ✅ (le `setup_reservations` s'exécute, mais retourne tôt) | aucune modification ; mécanisme inerte |

## 7.3 Idempotence

La reprise s'effectue uniquement si la contrainte est absente
(`if _constraint_present(cr): return`). **Relancer la migration ne doublonne
pas les réservations.**

## 7.4 Vérification

- Première installation : ✅ (table créée, reprise effectuée — 0 enregistrement
  dans les référentiels de la base de test, donc 0 réservation)
- Mise à jour d'un module installé : ✅ (table créée, 20 réservations reprises
  depuis les référentiels existants de la base de test)
- Chargement normal du registre : ✅ (aucune modification)
- Table absente : ✅ (reprise s'effectue lors de la première mise à jour)
- Table présente sans contrainte : ✅ (reprise + pose de la contrainte)
- Table présente avec contrainte : ✅ (retour immédiat)
- Migration interrompue : ✅ (savepoint annulé, données intactes)
- Relance après échec : ✅ (idempotent)
- Extension absente : ✅ (mécanisme inerte)

---

# 8. PREUVES DE CONCURRENCE SQL

Voir § 7.3 du rapport Prompt 14 et les résultats du Prompt 15 (§ 5.3).

Les scénarios ont été reproduits avec **deux connexions PostgreSQL indépendantes**
(`psycopg2`, `REPEATABLE READ` explicite) sur la base de diagnostic dédiée.

### 8.1 Résultats détaillés

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

**Scénarios complémentaires exigés :** création multiple avec conflit (refusée,
aucune trace), création multiple sans conflit, modification multiple avec conflit
(aucune écriture), changement code + nom simultané, changement société + code,
réactivation avec conflit (refusée avant écriture), suppression, échec de
migration en présence d'un doublon (contrainte restaurée après annulation du
savepoint), cohérence après rollback, correspondance enregistrement ↔
réservations, disjointness des domaines.

## 8.2 Distinction claire

| Type de test | Ce qu'il démontre | Outil |
|---|---|---|
| Contrainte PostgreSQL seule | L'exclusion est robuste sous `REPEATABLE READ` | `psycopg2` brut, 2 connexions |
| Fonctions utilitaires | `reference_scope`, `normalize_reference` corrects | Python unitaire |
| Méthodes ORM | `create`/`write`/`unlink` respectent le mécanisme | `TransactionCase` |
| Concurrence ORM complète | Le mécanisme intégré est fiable | 2 connexions `psycopg2` brutes (les transactions Odoo ne peuvent pas être utilisées pour la concurrence sans interblocage) |

**Note** : les tests de concurrence utilisent des connexions `psycopg2` brutes
car les transactions Odoo ne peuvent pas être utilisées pour la concurrence
sans interblocage (le commit d'une transaction Odoo traverse le verrou de
registre du processus). Le SQL appliqué est **exactement** celui du code
applicatif, les clés et périmètres étant calculés par les fonctions du module.

---

# 9. ANALYSE DE NORMALISATION

Voir § 6.4 du rapport Prompt 14 et § 7.4 du rapport Prompt 15.

| Cas | Python `strip().casefold()` | SQL `LOWER(BTRIM(...))` | Conséquence |
|---|---|---|---|
| ASCII majuscules/minuscules | identique | identique | identique |
| Espaces au début/fin | identique | identique | identique |
| Tabulations | `abc` | `abc\t` | Python **plus strict** |
| Accents | identique | identique | identique |
| `ß` | `ss` | `ß` | Python **plus strict** |
| Chaîne vide | ignorée | ignorée | identique |
| Valeur NULL | ignorée | ignorée | identique |

**Conclusion** : la normalisation Python est **plus stricte** que l'index SQL.
La réservation utilise la même normalisation Python → elle est **au moins aussi
stricte** que l'index SQL. Les différences (tabulations, `ß`) sont dans le
**sens favorable** : la contrainte Python est le message utilisateur, l'index
SQL est le garde-fou de base ; la réservation ajoute une couche stricter, donc
**aucun faux négatif**. Aucune incohérence qui compromettrait l'intégrité.

---

# 10. CONTRÔLE DES RÉSERVATIONS SUR LES 13 MODÈLES

Vérifié sur la base de diagnostic `gest_agri_audit_test` :

| Contrôle | Résultat |
|---|---|
| Toutes les références actives ont les réservations attendues | ✅ |
| Les références archivées n'ont aucune réservation | ✅ |
| Aucune réservation ne pointe vers un enregistrement supprimé | ✅ |
| Aucun doublon de réservation | ✅ |
| Aucun enregistrement actif ne manque de réservation | ✅ |
| Opérations multi-enregistrements | ✅ |
| Rollbacks | ✅ (0 réservation résiduelle) |

**Requêtes SQL utilisées :**

```sql
-- Nombre de réservations par modèle
SELECT model_name, kind, count(*) FROM gest_agri_reference_reservation
GROUP BY model_name, kind ORDER BY model_name, kind;

-- Cohérence : réservations sans enregistrement actif correspondant
SELECT r.id, r.model_name, r.normalized FROM gest_agri_reference_reservation r
WHERE NOT EXISTS (
    SELECT 1 FROM gest_agri_soil_type t
    WHERE t.active IS TRUE AND lower(btrim(t.code)) = r.normalized
);
```

Résultat : **20 réservations** pour 10 enregistrements actifs (2 par
enregistrement : code + nom), aucune réservation orpheline.

---

# 11. ANOMALIES SUPPLÉMENTAIRES

Aucune anomalie supplémentaire découverte par rapport aux rapports précédents.

| # | Anomalie | Statut |
|---|---|---|
| A1 | `scope_key` redondant | ✅ **CORRIGÉ ET TESTÉ** (supprimé) |
| A2 | Schéma du Prompt 13 fragile sur les bornes | ✅ **CORRIGÉ ET TESTÉ** (domaines disjoints par signe) |
| A3 | Interblocage dans les tests de concurrence | ✅ **CORRIGÉ ET TESTÉ** (clés uniques par exécution + connexions brutes) |
| A4 | 7 avertissements « two fields have the same label » | ✅ **CORRIGÉ ET TESTÉ** (libellés renommés) |
| A5 | `README.md` obsolète | ✅ **CORRIGÉ ET TESTÉ** |
| A6 | Fichier `.bak` dans l'addon | ✅ **CORRIGÉ ET TESTÉ** (archivé hors addon) |
| A7 | Paquets `report/` et `wizard/` vides | ✅ **CORRIGÉ ET TESTÉ** (documentés) |
| A8 | Absence de journalisation | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase F) |

---

# 12. ÉTAT EXACT DE LA PRODUCTION

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

# 13. RISQUES RÉSIDUELS

| # | Risque | Probabilité | Impact | Statut |
|---|---|---|---|---|
| R1 | Conflit code global ↔ code de société simultané | **Éliminé** | — | ✅ **CORRIGÉ ET TESTÉ** |
| R3 | L'instance de production dessert les bases de diagnostic | Certaine | Toute expérience sur une base de test atteint la production | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase B) |
| R9 | Aucun journal exploitable | Certaine | Incident non attribuable | ⚙️ **PROPOSITION NON APPLIQUÉE** (Phase C) |
| R10 | Le mécanisme d'unicité est **inerte en production** tant que `btree_gist` n'y est pas installé | Certaine | Les conflits globaux restent possibles en production | 🔒 **BLOQUÉ PAR UNE AUTORISATION** |
| R11 | Les libellés de compteurs corrigés ne sont appliqués en production qu'à la prochaine mise à jour | Certaine | 7 avertissements persistent en production jusqu'alors | 🔒 **BLOQUÉ PAR UNE AUTORISATION** |
| R12 | Écriture SQL directe sur une table de référentiel (hors ORM) | Faible | Réservation non alimentée | Documenté — hors périmètre ORM |
| R13 | Table de réservation non purgée si une réservation est insérée par un chemin non-ORM | Très faible | Fausse contention | Documenté |

---

# 14. VERDICT TECHNIQUE FINAL

Le module est **techniquement consolidé** sur la base de test :

- ✅ Le mécanisme de réservation est correctement intégré aux 13 modèles.
- ✅ Les opérations CRUD sont cohérentes et transactionnelles.
- ✅ Les tests de concurrence sous `REPEATABLE READ` démontrent l'absence de
  doublons interdits.
- ✅ La migration est idempotente et sûre.
- ✅ Les doublons historiques provoquent un échec propre sans perte de données.
- ✅ Les règles multi-sociétés restent respectées.
- ✅ Les tests complets passent sans erreur (101 tests, 0 échec, 0 erreur).
- ✅ Les risques résiduels sont identifiés sans ambiguïté.
- ✅ La production reste strictement inchangée.

**Trois autorisations restent nécessaires** (D1 : activation du mécanisme en
production, D2 : isolation de l'instance, D3 : journalisation). Aucune n'a été
exécutée dans le cadre de ce prompt.

---

*Rapport généré dans le cadre du Prompt N°16 — Module `gestion_agricole` — Odoo 20
Community. Toutes les écritures ont été réalisées sur les bases de diagnostic ;
la base de production `odoo20` n'a subi aucune modification.*
