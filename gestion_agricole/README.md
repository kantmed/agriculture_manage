# Gestion Agricole

Module Odoo 20 Community pour la gestion complète d'une exploitation agricole.

## Objectif

Fournir un ERP agricole multi-sociétés et multi-exploitations, couvrant :
- la production végétale,
- l'élevage,
- l'irrigation,
- le matériel,
- le personnel,
- les stocks et la traçabilité,
- les achats et ventes,
- la gestion économique.

## Architecture

- Un seul addon installable : `gestion_agricole`.
- Préfixe technique des modèles métier : `gest_agri`.
- Réutilisation des modèles natifs Odoo.
- Aucune comptabilité ou stock parallèle.
- Aucune modification des anciens modules agricoles.

## Dépendances

base, mail, contacts, uom, product, stock, stock_account, purchase, sale_management, account, analytic, maintenance.

## Organisation

- models/ : modèles métier (à implémenter par étapes).
- views/ : vues et menus.
- security/ : groupes et droits d'accès.
- data/ : données et séquences.
- tests/ : tests automatisés.

## Consigne

Ne pas modifier les anciens modules agricoles. Ce module est le seul socle de développement futur.
