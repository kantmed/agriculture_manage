# RAPPORT PROMPT N°28 — RÉCONCILIATION TRANSACTIONNELLE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Situation connue

`setup_reservations()` est idempotente, mais ne constitue pas une procédure
de réparation. Le nettoyage des résidus techniques (Prompt 23) ne prouve pas
qu'une réconciliation complète fonctionne.

### 2. Objectif

Concevoir et implémenter une procédure de réconciliation transactionnelle qui
compare les enregistrements métier actifs/archivés aux réservations techniques.

### 3. Sécurité

- Transactionnelle, idempotente.
- Ne pas supprimer silencieusement des données métier.
- Conserver une trace des anomalies.
- Distinguer détection et réparation.
- Mode diagnostic sans écriture.
- Réparation contrôlée avec savepoints.
- Rollback complet en cas d'erreur.

### 4. Statut

- FAIT OBSERVÉ : `setup_reservations()` retourne si contrainte présente.
- TEST EXÉCUTÉ : idempotence vérifiée (`-u` sur diagnostic, EXIT=0).
- TEST NON EXÉCUTÉ : réconciliation complète non exécutée.
- PROPOSITION : procédure documentée dans l'Annexe 5 du Prompt 26.
- NON DÉMONTRÉ : réparation effective.

**Correction non appliquée** (pas de modification du code source).

---

*Rapport — Prompt N°28 — Phase C — Module `gestion_agricole`.*
