{
    "name": "Agriculture Management - Livestock",
    "version": "20.0.1.0.0",
    "category": "Agriculture",
    "summary": "Gestion du cheptel, des lots et des mouvements d'élevage",
    "description": "Socle de gestion des espèces, races, animaux, lots, emplacements, mouvements et pesées.",
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