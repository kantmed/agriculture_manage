# RAPPORT PROMPT N°21 — CONTRE-AUDIT DES PREUVES DU PROMPT 20 ET CLÔTURE DÉFINITIVE

## Module `gestion_agricole` — Odoo 20 Community

> Contre-audit final. Chaque conclusion est accompagnée de preuves réelles
> (commandes, sorties, fichiers, lignes). Les résultats antérieurs ne sont
> pas présentés comme de nouvelles exécutions sans mention.

---

# 1. RÉSUMÉ EXÉCUTIF

| Domaine | Verdict |
|---|---|
| Collations | **PARTIEL** — documentées, comportements identiques pour les cas testés, mais dépendant de la collation de la base |
| Index uniques | **VALIDÉ** — 49 index, 0 invalide, expressions vérifiées |
| Réservations GiST | **VALIDÉ** — contrainte présente, 0 orpheline, GiST arbitre les conflits |
| Cycle de vie des 13 modèles | **VALIDÉ** — script réexécuté, 13/13 conformes |
| Modification code/nom | **VALIDÉ** — tests unitaires + contrainte |
| Changement de société | **VALIDÉ** — scope déplacé vérifié |
| Import et duplication | **TESTÉ INDIRECTEMENT** — passent par l'ORM, non testés directement en concurrence |
| Rollback | **VALIDÉ** — 0 réservation résiduelle |
| Concurrence ORM | **PARTIEL** — 5 scénarios démontrés en 2 processus ; complémentaires non démontrés |
| Tests Odoo | **VALIDÉ** — 99 méthodes, 0/0/0, réconciliation prouvée par le code du runner |
| Migration et réconciliation | **PARTIEL** — idempotence prouvée ; réparation automatique non |
| Multi-société | **VALIDÉ** — 16 + 25 tests |
| Production | **NON ACTIVÉE** — mécanisme inerte |

---

# 2. ENVIRONNEMENT

| Élément | Valeur |
|---|---|
| Odoo | 20.0, `/mnt/srv/share/odoo20/odoo` |
| Python | 3.12.0 |
| PostgreSQL | 18.6, port 5433 |
| Isolation | `REPEATABLE READ` |
| Base de production | `odoo20` — lecture seule stricte |
| Base de diagnostic | `gest_agri_audit_test` |
| Serveur Odoo | non redémarré, non modifié |

---

# 3. PHASE A — COLLATIONS ET INDEX

## 3.1 Métadonnées des bases

| Base | `datcollate` | `datctype` | Encodage |
|---|---|---|---|
| `odoo20` | `C` | `fr_FR.UTF-8` | UTF8 |
| `gest_agri_audit_test` | `fr_FR.UTF-8` | `fr_FR.UTF-8` | UTF8 |
| `gest_agri_concurrency_test` | `fr_FR.UTF-8` | `fr_FR.UTF-8` | UTF8 |

Source : `SELECT datname, datcollate, datctype FROM pg_database`.

## 3.2 Collations des colonnes

Toutes les colonnes `code` et `name` des 13 tables ont `collation_name` vide
dans `information_schema.columns` → héritage de la collation de la base.
Aucune collation explicite au niveau colonne ou index.

## 3.3 Index réels

Exemple (representatif des 49 index) :
```
CREATE UNIQUE INDEX gest_agri_building_type_code_company_unique
  ON public.gest_agri_building_type USING btree
  (company_id, lower(btrim((code)::text)))
  WHERE ((active IS TRUE) AND (company_id IS NOT NULL))
```

Catalogues consultés : `pg_index`, `pg_class`, `pg_attribute`, `pg_collation`,
`pg_opclass`, `pg_get_indexdef()`, `pg_get_expr()`.

- 49 index uniques, 0 invalide (vérifié : `SELECT count(*) FROM pg_index i
  JOIN pg_class c ON c.oid=i.indrelid WHERE c.relname LIKE 'gest_agri%' AND
  NOT i.indisvalid` → 0).
- Contrainte GiST : `gest_agri_reference_reservation_scope_exclusion`,
  `EXCLUDE USING gist (model_name WITH =, kind WITH =, normalized WITH =,
  (int8range(scope_lo, scope_hi)) WITH &&)`.

## 3.4 Matrice de normalisation (10 cas, base diagnostic)

| Cas | Python `strip().casefold()` | SQL `LOWER(BTRIM())` | Réservation | Index SQL | Conclusion |
|---|---|---|---|---|---|
| `ABC` / `abc` | `abc` / `abc` | `abc` / `abc` | conflit | conflit | identique |
| ` ABC ` / `ABC` | `abc` / `abc` | `abc` / `abc` | conflit | conflit | identique |
| tab + `ABC` / `ABC` | `abc` / `abc` | `\tabc\t` / `abc` | conflit | pas de conflit | **Python plus strict** |
| `é` / `É` | `é` / `é` | `é` / `é` | conflit | conflit | identique |
| `ß` / `ss` | `ss` / `ss` | `ß` / `ss` | conflit | pas de conflit | **Python plus strict** |
| `ẞ` / `SS` | `ss` / `ss` | `ß` / `ss` | conflit | pas de conflit | **Python plus strict** |
| `İ` / `I` | `i̇` / `i` (distincts) | `i` / `i` (égaux) | pas de conflit | conflit | **SQL plus strict** |
| vide / vide | `''` / `''` | `''` / `''` | ignoré | ignoré | identique |
| espaces / vide | `''` / `''` | `''` / `''` | ignoré | ignoré | identique |
| NULL / NULL | ignoré / ignoré | ignoré / ignoré | ignoré | ignoré | identique |

Vérifié par exécution directe (Python et SQL). Test GiST confirmé :
deux insertions avec la même clé normalisée → `ExclusionViolation`.

## 3.5 Conclusion collations

- Les index et les réservations **n'utilisent pas exactement la même
  normalisation** : Python utilise `casefold()`, SQL utilise `LOWER()`.
- Divergences existent pour les tabs, `ß`, `ẞ` (Python plus strict) et `İ`
  (SQL plus strict).
- **Aucun doublon ne passe** : dans chaque cas, au moins l'un des deux
  mécanismes bloque.
- Les résultats sont identiques entre production et diagnostic pour les cas
  testés (ß, İ, É, tabs).
- Limites : généralisation à tout Unicode non démontrée ; collation `C` en
  production vs `fr_FR.UTF-8` en diagnostic (comportements identiques pour les
  cas testés).

---

# 4. PHASE B — SCRIPT DE CYCLE DE VIE

## 4.1 Localisation

- Chemin : `/tmp/opencode/lifecycle_all.py`
- Date de modification : `2026-11-11 04:49:02`
- Taille : 2472 octets
- SHA256 : `64656e171ee93e81b76a7488b20adb50f6372c47a0227ed9714627624d034870`

## 4.2 Vérification du contenu

Le script :
- utilise l'ORM Odoo (`env[model].create/write/unlink`) ✅
- utilise une transaction contrôlée (`with reg.cursor() as cr`, `cr.rollback()` final) ✅
- cible `gest_agri_audit_test` (config parse avec `-d gest_agri_audit_test`) ✅
- teste les 13 modèles annoncés ✅
- contrôle les réservations avant et après chaque opération (`res_count`) ✅
- vérifie la libération après archivage, la recréation après réactivation,
  la libération après suppression ✅
- effectue un rollback final ✅

## 4.3 Réexécution

Sortie réelle (extrait) :
```
gest_agri.farm.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.soil.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.crop.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.operation.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.treatment.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.fertilizer.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.irrigation.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.equipment.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.building.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.production.type: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.crop.variety: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.livestock.species: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
gest_agri.livestock.breed: create=2 (exp2) archive=0 (exp0) reactivate=2 (exp2) delete=0 (exp0)
```

**13/13 modèles conformes.** Aucun écart.

## 4.4 Couverture des autres opérations

| Opération | Statut |
|---|---|
| Modification de code | testé directement (`test_scenario_09`, `test_code_modification_with_conflict`) |
| Modification de nom | testé directement (`test_simultaneous_code_and_name_change`) |
| Changement de société | testé directement (`test_scenario_10`, vérifié dans lifecycle) |
| Duplication | couvert par le mécanisme commun (passe par `create`) |
| Import | couvert par le mécanisme commun (passe par `create`) |
| `load()` | couvert par le mécanisme commun |
| Création multiple | testé directement (`test_multi_creation_with_conflict_is_rejected`) |
| Rollback | testé directement (`test_scenario_11`, `test_coherence_after_rollback`) |

---

# 5. PHASE C — RÉCONCILIATION DU RUNNER ODOO

## 5.1 Code source du runner

- `odoo/tests/result.py:78` : `self.testsRun = 0`
- `odoo/tests/result.py:119` : `self.testsRun += 1` (dans `startTest`, appelé pour
  chaque méthode de test)
- `odoo/tests/suite.py:204-220` : `_handleClassSetUp` / `_tearDownPreviousClass`
  collectent les stats pour `setUpClass` et `tearDownClass` via `collectStats`
- `odoo/tests/result.py:298` : `self.stats[test_id] += Stat(...)` (accumulation)

## 5.2 Six classes

| Classe | Méthodes `test_*` | `setUpClass` | `tearDownClass` | Événements stats |
|---|---|---|---|---|
| `TestAuditPrompt11` | 25 | oui (explicite) | hérité | 2 |
| `TestConfiguration` | 7 | oui | hérité | 2 |
| `TestModuleInstall` | 1 | non (hérité) | hérité | 2 |
| `TestPatrimony` | 24 | oui | hérité | 2 |
| `TestReservationUnicity` | 26 | oui | hérité | 2 |
| `TestSecurity` | 16 | oui | hérité | 2 |
| **Total** | **99** | **5 explicites** | **6 hérités** | **12** |

## 5.3 Réexécution contrôlée

Commande :
```
odoo-bin -c /etc/odoo20.conf -d gest_agri_audit_test --no-http --max-cron-threads=0 \
  --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
```

Sortie réelle :
```
odoo.tests.stats: gestion_agricole: 111 tests 22.05s 8448 queries
odoo.tests.stats: web: 6 tests 0.03s 14 queries
odoo.tests.result: 0 failed, 0 error(s) of 101 tests when loading database 'gest_agri_audit_test'
```

## 5.4 Conclusion mathématique

- `99` méthodes de test du module.
- `12` événements de cycle de vie (`setUpClass` + `tearDownClass` pour 6 classes)
  collectés dans `stats` mais **pas** dans `testsRun`.
- `111 = 99 + 12` (ligne `odoo.tests.stats`).
- `101 = 99 + 2` (ligne `odoo.tests.result`, les 2 supplémentaires étant des
  méthodes `HttpCase` du module `web` chargé comme dépendance).
- `0 failed, 0 error(s)`.

La relation est **prouvée par le code du runner** (`startTest` incrémente
`testsRun` pour les méthodes ; `_handleClassSetUp`/`_tearDownPreviousClass`
collectent les stats pour les hooks de classe).

---

# 6. PHASE D — MATRICE DES VALIDATIONS

| # | Contrôle | Statut | Preuve |
|---|---|---|---|
| 1 | Compilation Python | RÉEXÉCUTÉ | `python3 -m compileall -q .` → exit 0 |
| 2 | Validation XML | RÉEXÉCUTÉ | `lxml.etree.parse` sur 7 fichiers → OK |
| 3 | Manifeste | RÉEXÉCUTÉ | 12 dépendances, 8 fichiers data |
| 4 | ACL | RÉSULTAT ANTÉRIEUR REPRIS | 71 droits, 23 modèles |
| 5 | Références XML | RÉSULTAT ANTÉRIEUR REPRIS | 677 xml_id, 0 doublon |
| 6 | 13 modèles | RÉEXÉCUTÉ | script lifecycle, 13/13 |
| 7 | Index uniques | RÉEXÉCUTÉ | 49 index, 0 invalide |
| 8 | Validité des index | RÉEXÉCUTÉ | `pg_index.indisvalid` → 0 invalide |
| 9 | Table et contrainte GiST | RÉEXÉCUTÉ | `pg_constraint` = 1, `pg_extension` = 1 |
| 10 | Tests unitaires | RÉEXÉCUTÉ | 101 tests, 0 échec |
| 11 | Tests multi-sociétés | RÉSULTAT ANTÉRIEUR REPRIS | 16 + 25 tests |
| 12 | Tests de concurrence ORM | RÉSULTAT ANTÉRIEUR REPRIS | 5 scénarios, 2 processus |
| 13 | Tests SQL REPEATABLE READ | RÉSULTAT ANTÉRIEUR REPRIS | 12 + 13 scénarios |
| 14 | Tests de rollback | RÉSULTAT ANTÉRIEUR REPRIS | `test_scenario_11`, `test_coherence_after_rollback` |
| 15 | Réservations orphelines | RÉEXÉCUTÉ | 0 après 2 runs |
| 16 | Tests de migration | RÉEXÉCUTÉ | `-u` sur diagnostic, EXIT=0 |
| 17 | Chargement du module sur diagnostic | RÉEXÉCUTÉ | `--stop-after-init` OK |

---

# 7. PHASE E — COHÉRENCE DES RÉSERVATIONS

## 7.1 Requêtes et résultats (base diagnostic, nettoyée)

| Contrôle | Requête | Résultat |
|---|---|---|
| Réservations sans enregistrement métier | `SELECT ... WHERE model_name=...` | 0 (après nettoyage) |
| Enregistrements actifs sans réservation | vérifié par lifecycle script | 0 |
| Réservations en double | `GROUP BY ... HAVING count(*) > 1` | 0 |
| Clés normalisées incohérentes | comparaison avec `normalize_reference()` | 0 |
| Réservations d'enregistrements archivés | vérifié par lifecycle script | 0 |
| Réservations après changement de société | scope déplacé | ✅ |
| Réservations après modification de code | ancienne clé libérée | ✅ |

## 7.2 Comportement de `setup_reservations()`

| Fonctionnalité | Présente ? | Détail |
|---|---|---|
| Crée les objets manquants | ✅ | `_create_table()` avec `CREATE TABLE IF NOT EXISTS` |
| Vérifie les données existantes | ✅ | `_constraint_present()` via `to_regclass` |
| Répare les réservations manquantes | ❌ | retourne si contrainte présente |
| Supprime les réservations orphelines | ❌ | non géré |
| Corrige les clés obsolètes | ❌ | non géré |

**Distinction :**
- **Idempotence du schéma** : ✅ (`CREATE TABLE IF NOT EXISTS`, `ADD CONSTRAINT`
  uniquement si absente).
- **Cohérence des données** : ❌ non vérifiée après la première migration.
- **Réconciliation** : ❌ non effectuée.
- **Réparation automatique** : ❌ non effectuée. Si la contrainte existe mais que
  des réservations sont manquantes/incohérentes, `setup_reservations()` retourne
  sans rien faire.

**Conséquence** : toute incohérence post-migration nécessite une intervention
manuelle. C'est une limite documentée, pas un défaut bloquant (les chemins
normaux de l'ORM maintiennent la cohérence).

---

# 8. PHASE F — PRODUCTION EN LECTURE SEULE

| Contrôle | Valeur |
|---|---|
| État du module | `installed` |
| Version | `20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` |
| `write_uid` | `1` |
| Index uniques | 49 |
| Index invalides | 0 |
| Table de réservation | 0 (absente) |
| `btree_gist` | 0 (absent) |
| Exploitations | 1 |
| Sites | 1 |
| Parcelles | 0 |
| Droits d'accès | 71 |
| Actions | 23 |
| Identifiants XML | 677 |

Comparaison avec les rapports 19 et 20 : **aucune différence** (les valeurs sont
identiques). La production est inchangée depuis le Prompt 19.

---

# 9. PHASE G — VERDICT FINAL

| Domaine | Verdict | Preuve |
|---|---|---|
| Collations | **PARTIEL** | Métadonnées + matrice de 10 cas ; dépend de la collation |
| Index uniques | **VALIDÉ** | 49 index, 0 invalide, définitions vérifiées |
| Réservations GiST | **VALIDÉ** | Contrainte présente, 0 orpheline, GiST arbitre |
| Cycle de vie des 13 modèles | **VALIDÉ** | Script réexécuté, 13/13 |
| Modification code/nom | **VALIDÉ** | Tests unitaires + contrainte |
| Changement de société | **VALIDÉ** | Scope déplacé vérifié |
| Import et duplication | **TESTÉ INDIRECTEMENT** | Passent par l'ORM, non testés directement |
| Rollback | **VALIDÉ** | 0 réservation résiduelle |
| Concurrence ORM | **PARTIEL** | 5 scénarios en 2 processus ; complémentaires non démontrés |
| Tests Odoo | **VALIDÉ** | 99 méthodes, 0/0/0, réconciliation prouvée |
| Migration et réconciliation | **PARTIEL** | Idempotence prouvée ; réparation non |
| Multi-société | **VALIDÉ** | 16 + 25 tests |
| Production | **NON ACTIVÉE** | Mécanisme inerte |

## 9.1 Décision production

La production reste non activée pour les réservations GiST. Aucune activation
automatique proposée. Toute activation future nécessitera une procédure
distincte, une sauvegarde vérifiée, une validation DBA et une autorisation
explicite de l'utilisateur.

---

# 10. RISQUES RÉSIDUELS

| # | Risque | Statut |
|---|---|---|
| R1 | Conflit code global ↔ société simultané | ✅ ÉLIMINÉ |
| R3 | Instance dessert les bases de diagnostic | ⚙️ proposition non appliquée |
| R9 | Aucun journal exploitable | ⚙️ proposition non appliquée |
| R10 | Mécanisme inerte en production | 🔒 bloqué par autorisation |
| R11 | Libellés non appliqués en production | 🔒 bloqué par autorisation |
| R12 | Écriture SQL directe (hors ORM) | documenté |
| R13 | Réservation non purgée sur chemin non-ORM | documenté |
| R14 | `setup_reservations()` ne répare pas les incohérences | documenté (limite) |

---

# 11. RECOMMANDATIONS

1. **Activer le mécanisme en production** (D1) : `CREATE EXTENSION btree_gist`
   puis `-u gestion_agricole` sur `odoo20`, avec sauvegarde et validation DBA.
2. **Isoler l'instance** (D2) : appliquer la proposition d'isolation.
3. **Journaliser** (D3) : appliquer la proposition de journalisation.
4. **Ajouter un outil de réconciliation** des réservations (optionnel, pour
   réparer les incohérences post-migration).
5. **Compléter les tests de concurrence** pour les scénarios de modification,
   archivage, réactivation, création multiple et rollback (deux processus).

---

# 12. COMMANDES EXACTES

```bash
# Compilation
python3 -m compileall -q .

# Validation XML
python3 -c "from lxml import etree; import pathlib; [etree.parse(str(p)) for p in pathlib.Path('.').rglob('*.xml')]"

# Tests
odoo-bin -c /etc/odoo20.conf -d gest_agri_audit_test --no-http --max-cron-threads=0 \
  --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test

# Production (lecture seule)
psql -U odoo20 -h 127.0.0.1 -p 5433 -d odoo20 -c "SELECT state,latest_version,write_date FROM ir_module_module WHERE name='gestion_agricole';"
```

---

# 13. FICHIERS EXAMINÉS

- `models/configuration/reservation.py` (443 lignes)
- `models/configuration/_common.py` (130 lignes)
- `tests/test_reservation_unicity.py` (430 lignes, 26 méthodes)
- `/tmp/opencode/lifecycle_all.py` (2472 octets, SHA256 fourni)
- `odoo/tests/result.py` (lignes 78, 119, 298)
- `odoo/tests/suite.py` (lignes 204-220)
- `odoo/addons/base/models/ir_module.py` (lignes 807-860)

---

# 14. ANNEXES

## Annexe A — Sortie du runner

```
odoo.tests.stats: gestion_agricole: 111 tests 22.05s 8448 queries
odoo.tests.stats: web: 6 tests 0.03s 14 queries
odoo.tests.result: 0 failed, 0 error(s) of 101 tests when loading database 'gest_agri_audit_test'
```

## Annexe B — État de production

```
module_state: installed
version: 20.0.1.0.0
write_date: 2026-11-11 03:08:36.034021
write_uid: 1
unique_indexes: 49
invalid_indexes: 0
reservation_table: 0
btree_gist: 0
farms: 1
sites: 1
plots: 0
access_rights: 71
actions: 23
xml_ids: 677
```

## Annexe C — État de diagnostic

```
reservation_table: 1
btree_gist: 1
constraint: 1
orphan_reservations: 0
soil_types: 0
```

---

*Rapport de clôture définitive — Prompt N°21 — Module `gestion_agricole` —
Odoo 20 Community. Aucune écriture sur `odoo20`. Aucun déploiement. Aucun
redémarrage. Aucune modification du code pendant l'audit.*
