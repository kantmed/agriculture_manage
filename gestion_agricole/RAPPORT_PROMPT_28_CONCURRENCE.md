# RAPPORT PROMPT N°28 — CONCURRENCE RÉELLE À DEUX PROCESSUS

## Module `gestion_agricole` — Odoo 20 Community

### 1. Contrainte fondamentale

Odoo 20 utilise `REPEATABLE READ`. Un verrou consultatif suivi d'une recherche
ORM ne garantit pas l'unicité concurrente. La contrainte PostgreSQL est
l'arbitre final.

### 2. Matrice des 10 scénarios

| # | Scénario | Statut | Preuve |
|---|---|---|---|
| 1 | Deux créations avec même code global | ✅ démontré | 2 processus, journal PostgreSQL |
| 2 | Deux créations avec même nom global | ✅ démontré | 2 processus |
| 3 | Deux créations même code même société | ✅ démontré | 2 processus |
| 4 | Deux créations sociétés différentes | ✅ démontré | 2 processus, pas de conflit |
| 5 | Création globale contre création société | ✅ démontré | 2 processus |
| 6 | Création société contre création globale | ✅ démontré | 2 processus |
| 7 | Modification simultanée de code | ⚠️ non démontré en 2 processus | tests unitaires + contrainte SQL |
| 8 | Modification simultanée de nom | ⚠️ non démontré en 2 processus | tests unitaires + contrainte SQL |
| 9 | Archivage contre création | ⚠️ non démontré en 2 processus | tests unitaires + contrainte SQL |
| 10 | Réactivation contre création | ⚠️ non démontré en 2 processus | tests unitaires + contrainte SQL |

### 3. Conditions de validité

- Deux processus indépendants ✅ (scénarios 1-6)
- Deux connexions PostgreSQL distinctes ✅
- Transactions réelles ✅
- Niveau d'isolation Odoo ✅
- Synchronisation déterministe ✅
- Données temporaires identifiables ✅
- Nettoyage précis et vérifié ✅

### 4. Statut

- TEST EXÉCUTÉ : scénarios 1-6 (2 processus)
- TEST NON EXÉCUTÉ : scénarios 7-10 (2 processus)
- NON DÉMONTRÉ : scénarios 7-10 en concurrence réelle

---

*Rapport — Prompt N°28 — Phase D — Module `gestion_agricole`.*
