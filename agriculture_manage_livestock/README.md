# Agriculture Manage Livestock — Odoo 20 Community

## Version 1.0.0
Socle initial : espèces, races, animaux individuels, lots collectifs ou individuels,
emplacements, mouvements de cheptel et pesées.

### Réutilisation des modules existants
Le module réutilise `agriculture.farm`, `agriculture.farm.site` et les groupes
`agriculture_manage.group_farm_user`, `group_farm_manager`, `group_farm_admin`.
Il ne modifie pas `agriculture.farm.operation`.

### Installation
Copier le dossier dans le chemin d'addons personnalisé, redémarrer Odoo,
mettre à jour la liste des applications puis installer Agriculture Management - Livestock.

Commande indicative :
`./odoo-bin -c /chemin/odoo.conf -d odoo20 -i agriculture_manage_livestock --stop-after-init`

### Limites de la version 1.0
Les opérations sanitaires, reproduction, alimentation, production et apiculture
détaillée seront livrées dans les versions suivantes. Les mouvements de stock,
les ventes et la comptabilité ne sont pas encore automatisés. Le transfert
d'animaux entre exploitations n'est pas inclus. Les mouvements appliqués ne
s'annulent pas : un mouvement correctif doit être saisi.

### Contrôles effectués
Syntaxe Python et structure XML contrôlées. Une installation et des tests
fonctionnels sur une base de test Odoo 20 restent indispensables.
