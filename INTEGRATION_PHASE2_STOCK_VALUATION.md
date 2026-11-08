# Phase 2 — Valorisation native du stock agricole (Odoo 20 Community)

## Objectif

Utiliser les couches de valorisation natives d'Odoo (`stock.valuation.layer`) comme source prioritaire du coût des intrants consommés dans les opérations agricoles. Aucun journal comptable ni aucune écriture manuelle parallèle n'est créé par le module agricole.

## Changements

- La synchronisation du coût est déclenchée après la finalisation réelle des mouvements `stock.move`, une fois que `stock_account` a pu générer les couches de valorisation. Cela couvre également les validations passant par les assistants de transfert immédiat et de reliquat.
- Le coût net est calculé à partir des valeurs des couches de valorisation : une sortie vers l'emplacement de production augmente le coût agricole et un retour vers le stock le diminue.
- Les quantités des couches sont converties de l'unité du produit vers l'unité de la ligne agricole.
- Une ligne peut agréger plusieurs mouvements et plusieurs couches de valorisation (transfert partiel, reliquat, retour ou ajustement).
- Le lien entre le mouvement de stock et la ligne agricole est contrôlé : produit et société doivent correspondre.
- Le nombre de couches de valorisation est consultable sur la ligne d'opération.
- Le coût d'analyse continue d'utiliser la valeur stock réellement calculée dès qu'elle est disponible ; sinon, il conserve le coût saisi manuellement.

## Configuration Odoo requise

1. Activer les fonctionnalités de valorisation du stock dans Odoo.
2. Pour les catégories de produits concernées, choisir la méthode de coût adaptée (coût standard, FIFO ou coût moyen/AVCO).
3. Choisir la valorisation automatisée (`Automated`) si les écritures comptables doivent être générées automatiquement par Odoo.
4. Vérifier les comptes de valorisation, stock entrant et stock sortant sur les catégories de produits et le journal de stock de la société.
5. Vérifier que les produits consommés sont des produits stockables et qu'ils appartiennent à une catégorie correctement configurée.

Le module ne force pas une méthode de coût ou une valorisation automatisée : ces choix ont des conséquences comptables et doivent être validés par l'administrateur/comptable de la base.

## Limites et contrôles

- La valorisation automatisée dépend de la configuration native `stock_account` et des comptes des catégories de produits.
- Le code n'a pas été exécuté sur la base Odoo du serveur. Les tests de transaction doivent être effectués après sauvegarde de la base et mise à jour des modules.
- Les transferts historiques déjà terminés avant cette mise à jour ne sont pas recalculés automatiquement ; une migration contrôlée pourra être prévue séparément.
