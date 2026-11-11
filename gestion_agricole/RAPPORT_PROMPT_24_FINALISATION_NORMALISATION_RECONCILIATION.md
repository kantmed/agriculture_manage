# RAPPORT PROMPT N°24 — FINALISATION DE LA NORMALISATION, RÉCONCILIATION ET PREUVES DE SÉCURISATION

## Module `gestion_agricole` — Odoo 20 Community

> Rapport principal. Les six annexes accompagnent ce rapport.

---

# 1. RÉSUMÉ EXÉCUTIF

| Point | Statut |
|---|---|
| Normalisation unique | ✅ règle proposée (Python `casefold()` référence ; SQL adapté via colonne normalisée) |
| Réconciliation des réservations | ✅ contrôle exhaustif documenté ; limite `setup_reservations()` confirmée |
| Couverture CRUD (13 modèles) | ✅ cycle de vie complet vérifié |
| Concurrence (5 scénarios ORM) | ✅ démontrés en 2 processus |
| Migration et idempotence | ✅ prouvées |
| Statistiques de tests | ✅ 99 méthodes, 0/0/0, réconciliation prouvée |
| Configurations proposées | ✅ 2 fichiers modèles créés |
| Production | ✅ non activée, aucune modification fonctionnelle |

---

# 2. ENVIRONNEMENT

| Élément | Valeur |
|---|---|
| Odoo | 20.0 |
| Python | 3.12.0 |
| PostgreSQL | 18.6, port 5433 |
| Isolation | `REPEATABLE READ` |
| Base de production | `odoo20` — lecture seule |
| Base de diagnostic | `gest_agri_audit_test` |
| Serveur Odoo | non redémarré, non modifié |

---

# 3. PHASE A — NORMALISATION UNIQUE

## 3.1 Code réel

- Python : `normalize_reference()` → `value.strip().casefold()` (`_common.py`).
- SQL : `LOWER(BTRIM(code))` et `LOWER(BTRIM(name))` (index uniques).
- Réservation : utilise `normalize_reference()` (Python).

## 3.2 Architecture retenue

**Option A recommandée** : normalisation applicative stockée. Une colonne
`code_normalized` / `name_normalized` générée en Python, indexée en binaire.
Garantit l'identité stricte entre Python et SQL, indépendamment de la
collation. La table de réservation utilise déjà ce principe (colonne
`normalized`).

Option B (fonction SQL équivalente à `casefold()`) : non viable (PostgreSQL
n'a pas de `casefold()` natif).

## 3.3 Matrice de tests

Voir Annexe 4 (requêtes SQL et preuves). Résultats confirmés :

| Cas | Python | SQL | Réservation | Index | Conclusion |
|---|---|---|---|---|---|
| `ABC`/`abc` | identique | identique | conflit | conflit | OK |
| tabs | Python plus strict | tabs conservés | conflit | pas de conflit | Python plus strict |
| `ß`/`ss` | Python plus strict | `ß` conservé | conflit | pas de conflit | Python plus strict |
| `ẞ`/`SS` | Python plus strict | `ß` conservé | conflit | pas de conflit | Python plus strict |
| `İ`/`I` | SQL plus strict | égal | pas de conflit | conflit | SQL plus strict |
| vide/espaces/NULL | identique | identique | ignoré | ignoré | OK |

**Aucun doublon ne passe.** L'intégrité est protégée dans les deux sens.

---

# 4. PHASE B — RÉCONCILIATION DES RÉSERVATIONS

## 4.1 Analyse

`setup_reservations()` : retourne immédiatement si contrainte présente.
Idempotence ✅. Cohérence ❌ (pas de réparation automatique). Réparation ❌.

## 4.2 Contrôle de cohérence

Requêtes disponibles (voir Annexe 4). Résultat sur base diagnostic nettoyée :
0 orpheline, 0 manquante, 0 doublon.

## 4.3 Réparation transactionnelle proposée

Procédure documentée dans l'Annexe 3. Utilise des savepoints, verrouille les
données, reconstruit les réservations manquantes, supprime les orphelines,
produit un journal d'audit. Idempotente.

## 4.4 Tests de réparation

Non exécutés dans ce prompt (pas de modification du code). La procédure est
documentée et prête pour validation.

---

# 5. PHASE C — COUVERTURE DES 13 MODÈLES

Cycle de vie complet vérifié (create→2, archive→0, reactivate→2, delete→0)
pour les 13 modèles. Détail dans l'Annexe 2.

---

# 6. PHASE D — CONCURRENCE ORM

5 scénarios démontrés en 2 processus. 6 scénarios complémentaires non
démontrés en 2 processus (tests unitaires + contrainte SQL). Détail dans
l'Annexe 3.

---

# 7. PHASE E — MIGRATION ET PREUVES D'IDEMPOTENCE

Idempotence prouvée (`-u` sur diagnostic, EXIT=0). Distinction idempotence /
cohérence / réconciliation / réparation documentée.

---

# 8. PHASE F — PREUVES ET STATISTIQUES

99 méthodes, 0 échec, 0 erreur, 0 ignoré. Réconciliation prouvée par le code
du runner (`result.py:119`, `suite.py:204-220`).

---

# 9. PHASE G — CONFIGURATIONS ET ANNEXES

Fichiers modèles créés :
- `/tmp/odoo20-production-proposed.conf` (SHA256: `8c534760...`)
- `/tmp/odoo20-test-proposed.conf` (SHA256: `09f838b2...`)

Contenu complet dans l'Annexe 6.

---

# 10. PHASE H — DÉCISION FINALE

| Décision | Statut |
|---|---|
| D1 — Activation GiST | SOUS CONDITIONS |
| D2 — Isolation | AUTORISABLE |
| D3 — Journalisation | AUTORISABLE |

L'autorisation appartient exclusivement à l'utilisateur.

---

# 11. LIVRABLES

1. `RAPPORT_PROMPT_24_FINALISATION_NORMALISATION_RECONCILIATION.md` (ce fichier)
2. `ANNEXE_PROMPT_24_MATRICE_13_MODELES.md`
3. `ANNEXE_PROMPT_24_CONCURRENCE_ORM.md`
4. `ANNEXE_PROMPT_24_RECONCILIATION_ET_MIGRATION.md`
5. `ANNEXE_PROMPT_24_REQUETES_SQL_ET_PREUVES.md`
6. `ANNEXE_PROMPT_24_CONFIGURATIONS_ET_DEPLOIEMENT.md`
7. `ANNEXE_PROMPT_24_SAUVEGARDE_RESTAURATION.md`

---

*Rapport principal — Prompt N°24 — Module `gestion_agricole` — Odoo 20 Community.*
