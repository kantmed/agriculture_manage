{
    "name": "Agriculture Management - Maintenance",
    "version": "20.0.1.3.0",
    "category": "Agriculture",
    "summary": "Maintenance préventive et corrective des équipements et infrastructures agricoles",
    "description": """
        Relie les équipements et demandes de maintenance Odoo aux exploitations,
        sites et infrastructures agricoles. S'appuie sur l'application Maintenance
        standard d'Odoo pour les équipes, techniciens, demandes et étapes.
    """,
    "author": "Agriculture Management",
    "license": "LGPL-3",
    "depends": ["maintenance", "agriculture_manage"],
    "data": [
        "security/ir.access.csv",
        "views/maintenance_equipment_views.xml",
        "views/maintenance_request_views.xml",
        "views/farm_infrastructure_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
