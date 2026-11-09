# Agriculture Management Website — 20.0.1.2.0

## Fonctionnalités

- Espace portail `/my/agriculture`.
- CRUD des exploitations agricoles : `/my/agriculture/farms`.
- CRUD des sites agricoles : `/my/agriculture/sites`.
- CRUD des parcelles : `/my/agriculture/plots`.
- Association facultative d'une parcelle à un site de la même exploitation.
- Filtrage des exploitations accessibles selon la société, le partenaire propriétaire et le responsable.

## Sécurité

Les routes de gestion des exploitations, sites et parcelles sont réservées aux utilisateurs connectés. Les recherches et modifications utilisent un périmètre basé sur les exploitations auxquelles l'utilisateur est rattaché. Les formulaires POST incluent le jeton CSRF d'Odoo.

## Routes principales

- `/my/agriculture`
- `/my/agriculture/farms`
- `/my/agriculture/sites`
- `/my/agriculture/plots`

## Déploiement

Mettre à jour le module `agriculture_manage_website` après sauvegarde de la base. Les contrôles statiques Python/XML ont été exécutés sur cette archive ; l'installation et les tests HTTP réels doivent encore être effectués sur l'instance Odoo 20 cible.
