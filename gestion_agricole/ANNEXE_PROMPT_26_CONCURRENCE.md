# ANNEXE 5 — CONCURRENCE

## Scénarios démontrés en 2 processus (ORM réel)

| # | Scénario | Résultat |
|---|---|---|
| 1 | global → société | conflit (ValidationError) ✅ |
| 2 | société → global | conflit ✅ |
| 3 | même société | conflit ✅ |
| 4 | sociétés différentes | pas de conflit ✅ |
| 5 | deux globaux | conflit ✅ |

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

Ces scénarios ne sont pas assimilés à des preuves de concurrence ORM.

## Robustesse de la contrainte PostgreSQL

✅ Démontrée (12 scénarios SQL + 5 scénarios ORM) sous `REPEATABLE READ`.
