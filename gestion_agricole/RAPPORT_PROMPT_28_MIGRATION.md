# RAPPORT PROMPT N°28 — MIGRATION ET RÉPARATION IDEMPOTENTES

## Module `gestion_agricole` — Odoo 20 Community

### 1. Comportement de setup_reservations()

| Situation | Comportement |
|---|---|
| Première installation | table créée, backfill, contrainte posée |
| Mise à jour | idem si table absente ; retour si contrainte présente |
| Chargement normal | aucune écriture |
| Extension absente | mécanisme inerte |
| Doublons historiques | ExclusionViolation → transaction annulée |
| Migration interrompue | savepoint annulé, données intactes |

### 2. Idempotence

✅ Vérifiée : `-u gestion_agricole` sur diagnostic, EXIT=0, 0 réservation
résiduelle, contrainte présente.

### 3. Distinction

- **Idempotence** : ✅ garantie (contrainte présente → retour).
- **Détection** : ✅ (contrainte absente → migration).
- **Réparation** : ❌ (pas de réparation automatique).
- **Validation** : ✅ (contrainte présente + 0 orpheline).

### 4. Limites

- `setup_reservations()` ne répare pas les incohérences.
- Retour immédiat si contrainte présente.
- Toute incohérence post-migration nécessite une intervention manuelle.

---

*Rapport — Prompt N°28 — Phase F — Module `gestion_agricole`.*
