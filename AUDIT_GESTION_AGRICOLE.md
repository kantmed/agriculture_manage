# Première passe — audit et corrections de la gestion agricole

## Périmètre

Module examiné : `agriculture_manage` (exploitations, sites, parcelles, infrastructures, référentiels et tableau de bord).

## Éléments déjà présents

- Modèles d'exploitations, de sites, de parcelles et d'infrastructures.
- Références automatiques pour les exploitations, sites et parcelles.
- Types d'activités et types d'irrigation chargés par données XML.
- Vues liste, formulaire, recherche et menus.
- Groupes de sécurité et droits d'accès.
- Tableau de bord et tests automatisés.

## Anomalie corrigée

Le KPI `total_area` du tableau de bord additionnait les surfaces des parcelles actives. Il affichait donc la superficie parcellaire enregistrée, et non la superficie totale déclarée des exploitations.

Correction :

- `total_area` = somme des `total_area` des exploitations actives de la société courante ;
- ajout de `farm_count` ;
- ajout de `allocated_area` (superficie parcellaire affectée, alignée sur le calcul de capacité des exploitations) ;
- ajout de `unallocated_area` ;
- les superficies cultivées et disponibles restent calculées à partir des parcelles actives par état.
- adaptation du test de tableau de bord pour vérifier les valeurs distinctes.

## Vérifications exécutées

- Compilation syntaxique Python (`compileall`) sur le dépôt : réussie.
- Analyse XML avec le parseur XML sur les fichiers du dépôt : réussie.

## Vérifications non exécutées

Les tests Odoo n'ont pas pu être lancés dans cet environnement, car le paquet Python `odoo` et une base Odoo 20 ne sont pas disponibles. Il faudra exécuter les tests dans l'instance cible avant mise en production.

## Suite recommandée

1. Exécuter les tests Odoo sur une base de test Odoo 20.
2. Vérifier les règles d'accès avec les trois profils agricoles et en multi-société.
3. Tester les créations, modifications, archivages et changements de rattachement exploitation/site/parcelle.
4. Compléter ensuite les vues et actions selon les usages métier réels, puis valider les liens avec les modules cultures, stock, élevage et maintenance.
