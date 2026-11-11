# -*- coding: utf-8 -*-
{
    "name": "Gestion Agricole",
    "version": "20.0.1.0.0",
    "category": "Industries",
    "summary": "Gestion complète d'une exploitation agricole sous Odoo 20 Community",
    "description": """
Gestion Agricole
================

Application ERP agricole pour Odoo 20 Community.

Fonctionnalités prévues :
- Exploitations, sites et parcelles.
- Production végétale annuelle et pérenne.
- Élevage avec identification individuelle et troupeaux.
- Irrigation et ressources hydrauliques.
- Stocks et traçabilité.
- Matériel et maintenance.
- Personnel agricole.
- Achats et ventes.
- Gestion économique et comptabilité analytique.

Architecture :
- Un seul addon installable.
- Préfixe technique des modèles : gest_agri.
- Réutilisation des modèles natifs Odoo.
- Aucune comptabilité ou stock parallèle.
- Aucun changement des anciens modules agricoles.
""",
    "author": "Kantmoh",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "contacts",
        "uom",
        "product",
        "stock",
        "stock_account",
        "purchase",
        "sale_management",
        "account",
        "analytic",
        "maintenance",
    ],
    "data": [
        "security/security.xml",
        "security/ir.access.csv",
        "data/sequences.xml",
        "views/menu_views.xml",
        "views/configuration_views.xml",
        "views/patrimony_views.xml",
        "views/irrigation_views.xml",
        "views/production_views.xml",
        "views/farm_views.xml",
    ],
    "assets": {},
    "installable": True,
    "application": True,
    "auto_install": False,
}