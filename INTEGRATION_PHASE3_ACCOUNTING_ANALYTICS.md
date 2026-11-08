# Phase 3 — Comptabilité analytique native Odoo 20

## Objectif

Rattacher les coûts issus de la valorisation automatique du stock aux comptes analytiques natifs Odoo, sans créer de journal comptable parallèle ni modifier les écritures de valorisation standard.

## Ce qui est livré

- Un compte analytique Odoo facultatif peut être associé à chaque exploitation, campagne et parcelle.
- Les comptes analytiques sont contrôlés par société.
- Lorsqu'une écriture de valorisation est liée à un mouvement de stock d'une opération agricole, la distribution analytique est ajoutée aux lignes de charges correspondantes.
- La ligne de valorisation de l'actif de stock n'est pas ventilée : cela évite de doubler le coût analytique avec la ligne d'équilibrage.
- La validation et la création des écritures restent gérées par `stock_account` et `account` d'Odoo.

## Configuration nécessaire

1. Activer la comptabilité analytique dans Comptabilité > Configuration > Paramètres.
2. Créer trois plans analytiques distincts dans Odoo : Exploitations, Campagnes, Parcelles.
3. Créer les comptes analytiques correspondants dans chaque plan.
4. Ouvrir chaque exploitation, campagne et parcelle et renseigner son compte analytique dans l'onglet « Comptabilité analytique ».
5. Vérifier qu'une catégorie de produit en valorisation automatisée utilise un compte de charge adapté pour la consommation vers l'emplacement de production.

Les comptes analytiques sont facultatifs : si une dimension n'est pas renseignée, elle n'est pas ajoutée à la distribution.

## Limites et validation requise

- Cette phase traite les écritures de valorisation de stock liées aux opérations agricoles. Elle ne transforme pas encore les anciens mouvements financiers personnalisés en factures, paiements ou écritures comptables natives.
- La distribution est portée par la ligne de charge de l'écriture native. Le comportement précis dépend des comptes configurés dans les catégories de produits et les emplacements.
- Les tests d'installation et les tests transactionnels doivent être exécutés sur l'instance Odoo 20 cible. Les vérifications locales ne remplacent pas un test réel avec valorisation automatisée.
