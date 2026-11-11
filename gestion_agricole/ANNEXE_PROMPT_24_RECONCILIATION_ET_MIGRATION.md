# ANNEXE 5 — RÉCONCILIATION ET MIGRATION

## Idempotence

`setup_reservations()` retourne immédiatement si la contrainte d'exclusion existe.
Vérifié par `-u gestion_agricole` sur `gest_agri_audit_test` (EXIT=0, 0 réservation
résiduelle, contrainte présente).

## Cohérence

`setup_reservations()` ne vérifie pas la cohérence des données existantes.
Si la table existe avec la contrainte mais avec des réservations manquantes ou
incohérentes, elles ne sont pas réparées.

**Limite explicite** : idempotence ≠ cohérence ≠ réconciliation ≠ réparation.

## Migration

| Situation | Comportement |
|---|---|
| Première installation | table créée, backfill, contrainte posée |
| Mise à jour | idem si table absente ; retour si contrainte présente |
| Chargement normal | aucune écriture |
| Extension absente | mécanisme inerte |
| Doublons historiques | ExclusionViolation → transaction annulée |
| Migration interrompue | savepoint annulé, données intactes |

## Procédure de réconciliation proposée

1. Verrouiller les données (advisory lock ou transaction SERIALIZABLE).
2. Contrôler les conflits avant réparation.
3. Reconstruire les réservations manquantes.
4. Supprimer uniquement les réservations orphelines (identifiées par jointure).
5. Corriger les clés incohérentes.
6. Respecter les périmètres de société.
7. Utiliser des savepoints et transactions.
8. Produire un journal d'audit des changements.
9. Rollback complet en cas d'erreur.

**Non implémentée** (proposition documentaire).
