{
    "name": "Agriculture Management - Sales",
    "version": "20.0.1.1.0",
    "category": "Agriculture",
    "summary": "Commercialisation des récoltes et ventes agricoles",
    "description": "Intégration des commandes, livraisons et factures clients aux campagnes et récoltes agricoles, avec liaison à la gestion financière agricole.",
    "author": "Agriculture Management",
    "license": "LGPL-3",
    "depends": [
        "agriculture_manage",
        "agriculture_manage_crop",
        "agriculture_manage_stock",
        "agriculture_manage_account",
        "agriculture_manage_livestock",
        "sale_stock",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/harvest_views.xml",
        "views/agriculture_sales_menu.xml",
    ],
    "application": False,
    "installable": True,
}
