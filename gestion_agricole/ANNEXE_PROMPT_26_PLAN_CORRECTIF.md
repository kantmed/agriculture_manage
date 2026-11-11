# ANNEXE 9 — PLAN CORRECTIF

## Corrections de code (proposées, non appliquées)

1. **Normalisation** : ajouter des colonnes `code_normalized` / `name_normalized`
   générées en Python, indexer en binaire. Fichier : `reservation.py`,
   `_common.py`. Risque : moyen. Tests : matrice de 10 cas.

2. **Réconciliation** : implémenter une procédure transactionnelle de
   réconciliation des réservations. Fichier : `reservation.py`. Risque : moyen.
   Tests : anomalies artificielles contrôlées.

3. **Concurrence** : compléter les 6 scénarios complémentaires en 2 processus.
   Fichier : `tests/test_reservation_unicity.py`. Risque : faible.

## Prérequis DBA

1. `CREATE EXTENSION btree_gist` sur `odoo20`.
2. Validation des privilèges.

## Configuration système

1. Isolation de l'instance (D2).
2. Journalisation (D3).

## Tests fonctionnels

1. Compléter les tests de concurrence.
2. Tester la réconciliation.
3. Vérifier l'idempotence de la migration après réparation.

## Opérations de déploiement

1. Sauvegarde vérifiée (test de restauration).
2. Contrôle des doublons historiques.
3. Fenêtre de maintenance.
4. Autorisation explicite de l'utilisateur.
