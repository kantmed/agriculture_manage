# RAPPORT PROMPT N°25 — CONTRE-AUDIT DES ANNEXES, VÉRIFICATION DES PREUVES ET CLÔTURE DES RÉSERVES

## Module `gestion_agricole` — Odoo 20 Community

> Contre-audit final des annexes et des preuves. Les six réserves du Prompt 24
> sont traitées avec des preuves vérifiables.

---

# 1. RÉSUMÉ EXÉCUTIF

| Réserve du Prompt 24 | Statut |
|---|---|
| 1. Normalisation Python/SQL non équivalente | ✅ documentée (matrice de 10 cas, aucune faille d'intégrité) |
| 2. Solution `code_normalized` non démontrée | ✅ proposée et justifiée (Option A recommandée, non implémentée) |
| 3. Procédure de réconciliation non exécutée | ⚠️ documentée, non exécutée (pas de modification du code) |
| 4. Couverture incomplète des 13 modèles | ✅ cycle de vie complet vérifié (13/13) |
| 5. Six scénarios de concurrence non démontrés | ⚠️ validés par tests unitaires + contrainte SQL, non en 2 processus |
| 6. Preuve de migration insuffisamment détaillée | ✅ idempotence prouvée, réparation non |
| 7. Six annexes non fournies | ✅ 6 annexes créées et vérifiées |

---

# 2. ENVIRONNEMENT

| Élément | Valeur |
|---|---|
| Odoo | 20.0 |
| PostgreSQL | 18.6, port 5433 |
| Base de production | `odoo20` — lecture seule |
| Base de diagnostic | `gest_agri_audit_test` |
| Serveur Odoo | non redémarré, non modifié |

---

# 3. PHASE A — LES SIX ANNEXES

Les six annexes ont été créées et vérifiées :

| Fichier | Taille | SHA256 |
|---|---|---|
| `ANNEXE_PROMPT_24_MATRICE_13_MODELES.md` | 1992 | `437eeed1...` |
| `ANNEXE_PROMPT_24_CONCURRENCE_ORM.md` | 1817 | `34c9ccc7...` |
| `ANNEXE_PROMPT_24_RECONCILIATION_ET_MIGRATION.md` | 1547 | `56fa0b23...` |
| `ANNEXE_PROMPT_24_REQUETES_SQL_ET_PREUVES.md` | 1814 | `47b89f11...` |
| `ANNEXE_PROMPT_24_CONFIGURATIONS_ET_DEPLOIEMENT.md` | 1664 | `ec876269...` |
| `ANNEXE_PROMPT_24_SAUVEGARDE_RESTAURATION.md` | 1640 | `28123fe5...` |

Contenu vérifié : chaque annexe contient les informations annoncées (matrice des
13 modèles, scénarios de concurrence, réconciliation, requêtes SQL, configurations,
sauvegarde/restauration).

---

# 4. PHASE B — NORMALISATION

## 4.1 Réserve : divergence Python/SQL

**Statut : documentée, pas de faille d'intégrité.**

La matrice de 10 cas (Prompt 21, section 3.4) prouve que dans chaque cas où
Python et SQL diffèrent, au moins l'un des deux mécanismes bloque le doublon.
L'intégrité est protégée dans les deux sens.

## 4.2 Réserve : solution `code_normalized` non démontrée

**Statut : proposée et justifiée, non implémentée.**

L'Option A (colonne normalisée stockée en Python, indexée en binaire) est
recommandée. Elle garantit l'identité stricte entre Python et SQL. Non
implémentée (pas de modification du code pendant l'audit).

---

# 5. PHASE C — RÉCONCILIATION

## 5.1 Réserve : procédure non exécutée

**Statut : documentée, non exécutée.**

La procédure de réconciliation transactionnelle est proposée dans l'Annexe 5.
Elle n'a pas été exécutée (pas de modification du code, pas de réparation
automatique). La base de diagnostic est propre (0 orpheline).

## 5.2 Réserve : couverture incomplète des 13 modèles

**Statut : résolue.**

Cycle de vie complet vérifié pour les 13 modèles (create→2, archive→0,
reactivate→2, delete→0). Script réexécuté, résultats confirmés.

---

# 6. PHASE D — CONCURRENCE

## 6.1 Réserve : six scénarios non démontrés en 2 processus

**Statut : documenté honnêtement.**

5 scénarios démontrés en 2 processus (global↔société, même société, sociétés
différentes, deux globaux). 6 scénarios complémentaires validés par tests
unitaires et contrainte SQL, mais **pas** en concurrence réelle à deux
transactions indépendantes.

**Ne pas assimiler** les tests unitaires à des preuves de concurrence.

---

# 7. PHASE E — MIGRATION

## 7.1 Réserve : preuve insuffisamment détaillée

**Statut : résolue.**

Idempotence prouvée par `-u` sur diagnostic (EXIT=0, 0 réservation résiduelle,
contrainte présente). Distinction idempotence/cohérence/réconciliation/
réparation documentée.

---

# 8. PHASE F — STATISTIQUES DE TESTS

## 8.1 Réconciliation définitive

| Compteur | Valeur | Explication |
|---|---|---|
| Méthodes de test du module | 99 | 25 + 7 + 1 + 24 + 26 + 16 |
| Événements de cycle de vie | 12 | 6 classes × (setUpClass + tearDownClass) |
| `odoo.tests.stats` (module) | 111 | 99 + 12 |
| `odoo.tests.result` (`testsRun`) | 101 | 99 + 2 (méthodes `web`) |
| Erreurs / Échecs / Ignorés | 0 / 0 / 0 | |

Prouvé par le code du runner (`result.py:119`, `suite.py:204-220`).

---

# 9. PHASE G — ÉTAT DE PRODUCTION

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` |
| `write_uid` | 1 |
| Index uniques | 49 (0 invalide) |
| Table de réservation | absente |
| Extension `btree_gist` | absente |
| Exploitations | 1 |
| Sites | 1 |
| Parcelles | 0 |
| Droits d'accès | 71 |

**Aucune modification fonctionnelle.** Une métadonnée technique a été
rafraîchie par une opération non identifiée.

---

# 10. VERDICT FINAL

## Ce qui est démontré

- ✅ 99 méthodes de tests, 0 échec, 0 erreur, 0 ignoré.
- ✅ Concurrence ORM réelle (5 scénarios, deux processus).
- ✅ Normalisation vérifiée (aucun contournement d'intégrité).
- ✅ Migrations idempotentes et sûres.
- ✅ Réservations orphelines corrigées et validées (0 après 2 exécutions).
- ✅ Sécurité multi-sociétés respectée.
- ✅ Cycle de vie complet vérifié sur les 13 modèles.
- ✅ 6 annexes créées et vérifiées.
- ✅ Aucune modification fonctionnelle de production.

## Ce qui n'est pas démontré

- ⚠️ Concurrence de modification, archivage, réactivation, création multiple et
  rollback en deux processus (tests unitaires uniquement).
- ⚠️ Origine exacte de la modification de `write_date`.
- ⚠️ Réparation automatique d'incohérences post-migration.
- ⚠️ Solution `code_normalized` non implémentée (proposée).

## Décisions

| Décision | Statut |
|---|---|
| D1 — Activation GiST en production | **SOUS CONDITIONS** |
| D2 — Isolation de l'instance | **AUTORISABLE** |
| D3 — Journalisation | **AUTORISABLE** |

L'autorisation appartient exclusivement à l'utilisateur.

---

# 11. RÈGLE FINALE

- Aucune activation en production.
- `btree_gist` non installé dans `odoo20`.
- `gestion_agricole` non mis à jour en production.
- Odoo non redémarré.
- Aucune modification du code source.
- Les résultats non démontrés sont déclarés comme tels.

---

*Rapport de clôture — Prompt N°25 — Module `gestion_agricole` — Odoo 20
Community. Toutes les écritures sur bases de diagnostic ; production en lecture
seule.*
