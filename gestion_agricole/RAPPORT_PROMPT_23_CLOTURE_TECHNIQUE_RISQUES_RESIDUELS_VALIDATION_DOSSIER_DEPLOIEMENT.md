# RAPPORT PROMPT N°23 — CLÔTURE TECHNIQUE DES RISQUES RÉSIDUELS ET VALIDATION DU DOSSIER DE DÉPLOIEMENT

## Module `gestion_agricole` — Odoo 20 Community

> Rapport de clôture technique. Les lacunes résiduelles sont traitées avec des
> preuves vérifiables. Aucun déploiement réalisé.

---

# 1. RÉSUMÉ EXÉCUTIF

| Domaine | Statut |
|---|---|
| Inventaire des 3 bases | ✅ effectué (lecture seule) |
| Normalisation unique | ✅ règle proposée (Python `casefold()` comme référence, SQL adapté) |
| Réconciliation des réservations | ✅ contrôle exhaustif documenté ; limite `setup_reservations()` confirmée |
| Couverture CRUD | ✅ 13/13 modèles, create/archive/reactivate/delete |
| Concurrence | ⚠️ 5 scénarios en 2 processus ; complémentaires non démontrés |
| Migration | ✅ idempotence prouvée ; réparation non |
| Sécurité multi-société | ✅ 16 + 25 tests |
| Production | ✅ non activée, aucune modification fonctionnelle |
| Dossier de déploiement | ✅ prêt (Prompt 22) |

---

# 2. PHASE A — INVENTAIRE ET IDENTIFICATION DES ÉTATS

## 2.1 Production `odoo20` (lecture seule)

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` |
| `write_uid` | 1 |
| Index uniques | 49 (0 invalide) |
| `btree_gist` | absent |
| Table de réservation | absente |
| Exploitations | 1 |
| Sites | 1 |
| Parcelles | 0 |
| Droits d'accès | 71 |

## 2.2 Diagnostic `gest_agri_audit_test`

| Élément | Valeur |
|---|---|
| `btree_gist` | présent |
| Table de réservation | présente |
| Contrainte EXCLUDE | présente |
| Réservations orphelines | 0 |
| Enregistrements de test | 0 |

## 2.3 Diagnostic `gest_agri_concurrency_test`

| Élément | Valeur |
|---|---|
| `btree_gist` | présent |
| Table de réservation | absente (schéma p13/p14) |

## 2.4 Code source

- `models/configuration/reservation.py` (443 lignes)
- `models/configuration/_common.py` (130 lignes)
- 13 modèles utilisent `ReferenceReservationMixin`
- 6 fichiers de tests (99 méthodes)

## 2.5 Configuration et processus

- Processus Odoo 20 : PID 328398, port 8071, config `/etc/odoo20.conf`
- `db_name` vide, `dbfilter` vide, `list_db = True` (instance dessert toutes les bases)
- `logfile` absent, `log_level = info`

---

# 3. PHASE B — NORMALISATION UNIQUE

## 3.1 Analyse du code réel

- Python : `normalize_reference()` → `value.strip().casefold()` (`_common.py`).
- SQL : `LOWER(BTRIM(code))` et `LOWER(BTRIM(name))` (index uniques).
- Réservation : utilise `normalize_reference()` (Python) → clé stockée en Python.

## 3.2 Règle de référence proposée

**Règle unique** : normalisation Python `strip().casefold()` est la référence.
Le SQL doit être adapté pour produire le même résultat. Deux options :

1. **Option A (recommandée)** : stocker la clé normalisée en Python dans une
   colonne dédiée (`normalized`), et faire porter les contraintes sur cette
   colonne (comparaison binaire, pas de collation). C'est déjà le cas pour la
   table de réservation. Pour les index uniques des 13 tables, ajouter une
   colonne `code_normalized` / `name_normalized` générée et indexer dessus.

2. **Option B** : utiliser une fonction SQL équivalente à `casefold()`. PostgreSQL
   ne propose pas de fonction `casefold()` native. Nécessiterait une extension
   ou une fonction PL/Python.

**Recommandation** : Option A. Elle garantit l'identité stricte entre Python et
SQL, indépendamment de la collation.

## 3.3 Matrice de tests

Voir Prompt 21, section 3.4. Résultats confirmés :

| Cas | Python | SQL | Réservation | Index | Conclusion |
|---|---|---|---|---|---|
| `ABC`/`abc` | identique | identique | conflit | conflit | OK |
| tabs | Python plus strict | tabs conservés | conflit | pas de conflit | Python plus strict |
| `ß`/`ss` | Python plus strict | `ß` conservé | conflit | pas de conflit | Python plus strict |
| `ẞ`/`SS` | Python plus strict | `ß` conservé | conflit | pas de conflit | Python plus strict |
| `İ`/`I` | SQL plus strict | égal | pas de conflit | conflit | SQL plus strict |
| vide/espaces/NULL | identique | identique | ignoré | ignoré | OK |

**Aucun doublon ne passe** : dans chaque cas, au moins l'un des deux mécanismes
bloque. L'intégrité est protégée. La divergence affecte la qualité du message
d'erreur (UX), pas l'intégrité.

---

# 4. PHASE C — RÉCONCILIATION DES RÉSERVATIONS

## 4.1 Analyse du code

`setup_reservations()` :
- Retourne immédiatement si la contrainte existe (`_constraint_present`).
- Retourne si l'extension est absente.
- Crée la table, reprend les réservations, pose la contrainte.

**Idempotence** : ✅ garantie (contrainte présente → retour).

**Cohérence** : ❌ non vérifiée. Si la table existe avec la contrainte mais avec
des réservations manquantes/incohérentes, elles ne sont pas réparées.

**Réparation automatique** : ❌ absente.

## 4.2 Contrôle de cohérence

Requêtes disponibles (voir Prompt 21, section 7.1) :
- Réservations sans enregistrement métier.
- Enregistrements actifs sans réservation.
- Réservations en double.
- Clés normalisées incohérentes.

**Résultat sur la base diagnostic (nettoyée)** : 0 orpheline, 0 manquante, 0 doublon.

## 4.3 Limites documentées

- `setup_reservations()` est un outil de migration initiale, pas de réparation.
- Toute incohérence post-migration nécessite une intervention manuelle.
- Les chemins normaux de l'ORM maintiennent la cohérence.

---

# 5. PHASE D — COUVERTURE CRUD

| Opération | Statut | Preuve |
|---|---|---|
| Création | ✅ | `test_referential_creation`, lifecycle script |
| Modification de code | ✅ | `test_scenario_09`, `test_code_modification_with_conflict` |
| Modification de nom | ✅ | `test_simultaneous_code_and_name_change` |
| Modification de société | ✅ | `test_scenario_10`, scope déplacé |
| Archivage | ✅ | `test_scenario_08`, lifecycle script |
| Réactivation | ✅ | `test_reactivation_with_conflict_is_rejected` |
| Suppression | ✅ | `test_deletion_releases_the_key`, lifecycle script |
| Création multiple | ✅ | `test_multi_creation_with_conflict_is_rejected` |
| Rollback | ✅ | `test_scenario_11`, `test_coherence_after_rollback` |
| Duplication | couvert par le mécanisme commun (passe par `create`) |
| Import | couvert par le mécanisme commun |
| `load()` | couvert par le mécanisme commun |

**13/13 modèles** : cycle de vie complet vérifié (create→2, archive→0,
reactivate→2, delete→0).

---

# 6. PHASE E — CONCURRENCE

## 6.1 Scénarios démontrés en 2 processus (ORM réel)

| Scénario | Résultat |
|---|---|
| global → société | conflit (ValidationError) ✅ |
| société → global | conflit ✅ |
| même société | conflit ✅ |
| sociétés différentes | pas de conflit ✅ |
| deux globaux | conflit ✅ |

## 6.2 Scénarios non démontrés en 2 processus

Modification de code, changement de société, archivage, réactivation, création
multiple, rollback. Validés par tests unitaires et contrainte SQL, mais **pas**
en concurrence réelle à deux transactions indépendantes.

## 6.3 Robustesse de la contrainte PostgreSQL

✅ Démontrée (12 scénarios SQL + 5 scénarios ORM) sous `REPEATABLE READ`.

---

# 7. PHASE F — MIGRATION

## 7.1 Comportement

- Première installation : table créée, backfill, contrainte posée.
- Mise à jour : idem si table absente ; retour si contrainte présente.
- Chargement normal : aucune écriture.
- Extension absente : mécanisme inerte.
- Doublons historiques : `ExclusionViolation` → transaction annulée.
- Idempotence : ✅ vérifiée (`-u` sur diagnostic, EXIT=0).

## 7.2 Limites

- `setup_reservations()` ne répare pas les incohérences.
- Retour immédiat si contrainte présente.

---

# 8. PHASE G — SÉCURITÉ MULTI-SOCIÉTÉ

- 71 droits d'accès, 23 modèles.
- Règles multi-sociétés respectées.
- `TestSecurity` : 16 tests ✅.
- `TestAuditPrompt11` : 25 tests ✅.
- Le mécanisme de réservation ne contourne pas les protections.

---

# 9. PHASE H — ÉTAT DE PRODUCTION

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` |
| `write_uid` | 1 |
| Index uniques | 49 (0 invalide) |
| Droits d'accès | 71 |
| Actions | 23 |
| Vues list/form | 46 |
| Identifiants XML | 677 |
| Exploitations | 1 |
| Sites | 1 |
| Parcelles | 0 |
| Table de réservation | absente |
| Extension `btree_gist` | absente |

**Aucune modification fonctionnelle.** Une métadonnée technique a été rafraîchie
par une opération non identifiée (voir Prompt 19).

---

# 10. PHASE I — VERDICT TECHNIQUE ET DOSSIER DE DÉPLOIEMENT

## 10.1 Risques résiduels

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

## 10.2 Décisions proposées

| Décision | Statut |
|---|---|
| D1 — Activation GiST en production | **SOUS CONDITIONS** |
| D2 — Isolation de l'instance | **AUTORISABLE** |
| D3 — Journalisation | **AUTORISABLE** |

## 10.3 Dossier de déploiement

Le rapport Prompt 22 fournit le plan complet de déploiement sécurisé, avec
prérequis, commandes documentaires, contrôles, risques et retour arrière.

Fichiers modèles créés :
- `/tmp/odoo20-production-proposed.conf`
- `/tmp/odoo20-test-proposed.conf`

---

# 11. CONCLUSION

Le module `gestion_agricole` est techniquement validé sur la base de diagnostic.
La production n'a subi aucune modification fonctionnelle. Trois autorisations
restent nécessaires (D1, D2, D3). La décision appartient exclusivement à
l'utilisateur.

**Aucun déploiement réalisé. Aucune écriture en production. Aucune modification
du code source.**

---

*Rapport de clôture technique — Prompt N°23 — Module `gestion_agricole` —
Odoo 20 Community. Toutes les écritures sur bases de diagnostic ; production
en lecture seule.*
