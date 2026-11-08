# Agriculture Management – Odoo 20

## Budget agricole (version 20.0.1.2.0)

Cette version ajoute au module `agriculture_manage_analysis` :

- un budget par campagne culturale ;
- des prévisions par type d'opération et, facultativement, par parcelle ;
- le calcul des dépenses réelles à partir des opérations terminées et de leurs coûts analytiques ;
- la saisie des dépenses complémentaires de main-d'œuvre et autres dépenses ;
- le suivi du budget prévu, du réel, de l'écart, du restant et du taux de consommation ;
- un indicateur de dépassement, des filtres et un graphique comparatif ;
- les traductions françaises et arabes.

## Règles de calcul

- Seules les opérations au statut `done` sont prises en compte.
- Les dépenses complémentaires ne sont prises en compte que lorsqu'elles sont `posted`.
- Les dates de début et de fin du budget filtrent les opérations et dépenses réelles.
- La devise du budget est la devise de la société de la campagne.
- Une seule fiche budget est autorisée par campagne dans cette version.

## Installation / mise à jour

Copier les quatre répertoires de modules dans le chemin `addons` d'Odoo 20, puis mettre à jour la liste des applications et mettre à niveau `agriculture_manage_analysis`.

Dépendances : `agriculture_manage`, `agriculture_manage_crop`, `agriculture_manage_stock`, `stock_account`.

## Important

L'archive a fait l'objet de contrôles statiques (syntaxe Python, XML, structure ZIP). L'installation sur une base Odoo 20 réelle doit encore être effectuée pour valider les compatibilités runtime avec votre build Odoo 20.
