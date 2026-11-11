# ANNEXE 3 — RÉCONCILIATION

## Distinction

| Opération | Exécutée ? | Détail |
|---|---|---|
| Nettoyage des résidus de tests | ✅ | `_cleanup_reservations()` via psycopg2 autocommit |
| Vérification de cohérence | ✅ | Requêtes SQL sur base nettoyée (0 orpheline) |
| Réconciliation complète | ❌ | Non exécutée |
| Réparation effective | ❌ | Non exécutée |

Le nettoyage des résidus de tests n'est pas une réconciliation.

## Contrôle de cohérence

Requêtes disponibles (voir Annexe 5). Résultat sur base diagnostic nettoyée :
0 orpheline, 0 manquante, 0 doublon.

## Procédure de réconciliation proposée

1. Verrouiller les données (advisory lock).
2. Contrôler les conflits avant réparation.
3. Reconstruire les réservations manquantes.
4. Supprimer uniquement les réservations orphelines.
5. Corriger les clés incohérentes.
6. Respecter les périmètres de société.
7. Utiliser des savepoints et transactions.
8. Produire un journal d'audit.
9. Rollback complet en cas d'erreur.

Non implémentée (proposition documentaire).

## Limite de setup_reservations()

Retourne immédiatement si contrainte présente. Idempotence ✅, cohérence ❌.
