# Agriculture Management - Maintenance (20.0.1.0.0)

## Objectif

Extension de l'application Maintenance standard d'Odoo pour rattacher les équipements et interventions aux exploitations, sites et infrastructures d'Agriculture Management.

## Fonctionnalités

- Rattachement d'un équipement à une exploitation, un site et une infrastructure.
- Contrôles de cohérence entre exploitation, site et infrastructure.
- Réutilisation des demandes de maintenance préventive et corrective natives d'Odoo.
- Localisation automatique des demandes à partir de l'équipement.
- Saisie d'un coût direct par intervention dans la devise de l'exploitation.
- Accès rapide aux équipements et interventions depuis la fiche d'infrastructure.
- Menus agricoles dédiés : Maintenance / Équipements et Interventions.

## Dépendances

- `maintenance` (application standard Odoo Community)
- `agriculture_manage`

## Installation

Ajouter `agriculture_manage_maintenance` au chemin des addons, mettre à jour la liste des applications, installer le module puis attribuer les groupes agricoles adaptés.

## Limites de cette version

Le coût d'intervention est une donnée de suivi opérationnel. Il ne génère pas automatiquement de facture, d'écriture comptable ni de mouvement de stock. L'intégration des pièces consommées, achats et écritures analytiques sera une étape ultérieure.


## Correctif 20.0.1.2.0

La vue de recherche des équipements a été simplifiée aux champs standards `name` et `serial_no` afin d éviter les éléments de recherche avancée à l origine de l échec de validation observé sur Odoo 20. Les filtres de regroupement seront réintroduits après validation sur l instance cible.
