{
    "name": "Agriculture Management - Projects",
    "version": "20.0.2.0.0",
    "category": "Agriculture",
    "summary": "Gestion des projets agricoles et de leurs opérations",
    "description": "Étend le module Projet natif Odoo pour gérer les projets agricoles indépendamment des campagnes et suivre leurs opérations de réalisation.",
    "author": "Agriculture Management",
    "license": "LGPL-3",
    "depends": [
        "project",
        "agriculture_manage",
        "agriculture_manage_crop",
        "agriculture_manage_stock",
    ],
    "data": [
        "views/project_project_views.xml",
        "views/project_task_views.xml",
        "views/agriculture_views.xml",
        "views/agriculture_operation_views.xml",
        "views/agriculture_project_menu.xml",
    ],
    "application": False,
    "installable": True,
}
