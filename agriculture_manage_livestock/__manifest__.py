{
    "name": "Agriculture Management - Livestock",
    "version": "20.0.1.1.0",
    "category": "Agriculture",
    "summary": "Gestion du cheptel, de la reproduction, des lots et des mouvements d'élevage",
    "description": "Gestion des espèces, races, animaux, lots, emplacements, mouvements, pesées et cycles de reproduction.",
    "author": "Agriculture Management",
    "license": "LGPL-3",
    "depends": ["agriculture_manage", "agriculture_manage_stock", "mail", "uom"],
    "data": [
        "security/ir.access.csv",
        "data/livestock_sequence.xml",
        "data/livestock_species_data.xml",
        "views/livestock_views.xml",
        "views/livestock_menus.xml"
    ],
    "application": True,
    "installable": True
}