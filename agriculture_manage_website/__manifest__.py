{
    "name": "Agriculture Management - Website",
    "version": "20.0.1.0.0",
    "category": "Website",
    "summary": "Portail web et site pour la gestion agricole",
    "description": "Portail client et pages web pour la gestion agricole.",
    "author": "Agriculture Management",
    "license": "LGPL-3",
    "depends": [
        "website",
        "portal",
        "agriculture_manage",
    ],
    "data": [
        "security/groups.xml",
        "security/ir.access.csv",
        "views/portal_templates.xml",
        "views/website_templates.xml",
        "views/menu_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "agriculture_manage_website/static/src/css/website.css",
            "agriculture_manage_website/static/src/js/website.js",
        ],
    },
    "application": False,
    "installable": True,
}