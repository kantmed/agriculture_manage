# Agriculture Management - Projects (Odoo 20 Community)

Extension du module natif Odoo `project` pour rattacher les projets et tâches aux dimensions agricoles.

## Dépendances

- `project`
- `agriculture_manage`
- `agriculture_manage_crop`
- `agriculture_manage_analysis`

## Fonctionnalités

- rattachement d'un projet à une exploitation et à une campagne ;
- rattachement d'un projet à plusieurs parcelles ;
- liaison facultative au budget de la campagne ;
- classification des projets agricoles ;
- estimation d'investissement purement informative ;
- rattachement de chaque tâche à une parcelle du projet ;
- création d'un projet depuis une campagne ;
- contrôles de cohérence exploitation/campagne/parcelle/budget.

La planification, les tâches, jalons, dépendances, étapes, chatter et notifications restent natifs Odoo Project.

## Installation

1. Vérifier que l'application native `project` est installée.
2. Copier le dossier `agriculture_manage_project` dans un répertoire `addons` chargé par Odoo.
3. Mettre à jour la liste des applications.
4. Installer `Agriculture Management - Projects`.

Le module n'ajoute aucun moteur comptable ni amortissement.
