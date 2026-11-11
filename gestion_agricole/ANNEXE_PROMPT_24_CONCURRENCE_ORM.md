# ANNEXE 3 — CONCURRENCE ORM ET RÉCONCILIATION

## Scénarios démontrés en 2 processus (ORM réel)

| # | Scénario | Transaction A | Transaction B | Résultat |
|---|---|---|---|---|
| 1 | global → société | global créé (commit) | société même code → ValidationError | conflit ✅ |
| 2 | société → global | société créée (commit) | global même code → ValidationError | conflit ✅ |
| 3 | même société | société 2 créée (commit) | société 2 même code → ValidationError | conflit ✅ |
| 4 | sociétés différentes | société 1 créée (commit) | société 2 même code → SUCCESS | pas de conflit ✅ |
| 5 | deux globaux | global créé (commit) | global même code → ValidationError | conflit ✅ |

Preuve : journal PostgreSQL du processus B montre `ExclusionViolation` converti
en `ValidationError` français.

## Scénarios non démontrés en 2 processus

| Scénario | Preuve disponible | Preuve manquante |
|---|---|---|
| Modification simultanée du code | test unitaire ORM + contrainte SQL | concurrence 2 processus |
| Changement de société | test unitaire ORM + contrainte SQL | concurrence 2 processus |
| Archivage | test unitaire ORM + contrainte SQL | concurrence 2 processus |
| Réactivation | test unitaire ORM + contrainte SQL | concurrence 2 processus |
| Création multiple | test unitaire ORM (intra-transaction) | concurrence 2 processus |
| Rollback après réservation | test unitaire ORM | concurrence 2 processus |

## Réconciliation et migration

- Idempotence : ✅ (`setup_reservations()` retourne si contrainte présente)
- Cohérence : ❌ (pas de réparation automatique)
- Réconciliation : ❌ (pas effectuée)
- Réparation automatique : ❌ (absente)

Distinction : idempotence ≠ cohérence ≠ réconciliation ≠ réparation.
