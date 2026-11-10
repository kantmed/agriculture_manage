# Gestion Agricole

Module Odoo 20 Community pour la gestion complète d'une exploitation agricole.

## État actuel — Prompt n°4

Le module contient à ce stade :

- 13 référentiels de configuration ;
- 10 modèles de patrimoine agricole (exploitations, sites, parcelles,
  bâtiments, infrastructures, ressources en eau et irrigation) ;
- les vues liste, formulaire et recherche, les actions et les menus ;
- une matrice de droits d'accès par groupes et par exploitation ;
- les tests automatisés de configuration, de patrimoine et de sécurité.

Les modèles de production végétale, d'élevage, de campagnes, de stocks,
d'achats/ventes et de comptabilité seront ajoutés dans les étapes suivantes.

## Architecture

- Un seul addon installable : `gestion_agricole`.
- Préfixe technique des modèles métier : `gest_agri`.
- Réutilisation des modèles natifs Odoo.
- Aucune comptabilité ou stock parallèle.
- Aucune modification des anciens modules agricoles.

## Dépendances

`base`, `mail`, `contacts`, `uom`, `product`, `stock`, `stock_account`,
`purchase`, `sale_management`, `account`, `analytic`, `maintenance`.

Aucune dépendance n'est créée vers `hr`, `fleet`, `project`, `website`,
`portal`, `report_xlsx`, `base_account_budget` ou `base_accounting_kit`.

## Référentiels de configuration

Chaque référentiel possède un nom, un code, une description, un état actif et
une société facultative. Un enregistrement sans société est global et réservé
à l'administration ; un enregistrement avec société est propre à cette société.

- Types d'exploitation (`gest_agri.farm.type`)
- Types de sol (`gest_agri.soil.type`)
- Types de culture (`gest_agri.crop.type`)
- Variétés de culture (`gest_agri.crop.variety`)
- Espèces animales (`gest_agri.livestock.species`)
- Races animales (`gest_agri.livestock.breed`)
- Types d'opération (`gest_agri.operation.type`)
- Types de traitement (`gest_agri.treatment.type`)
- Types d'engrais (`gest_agri.fertilizer.type`)
- Types d'irrigation (`gest_agri.irrigation.type`)
- Types d'équipement (`gest_agri.equipment.type`)
- Types de bâtiment (`gest_agri.building.type`)
- Types de production (`gest_agri.production.type`)

Les variétés sont rattachées à un type de culture et les races à une espèce.
L'unicité des codes est contrôlée par société, avec prise en compte des
référentiels globaux.

## Patrimoine agricole

- Exploitation (`gest_agri.farm`) : code unique par société, surface totale,
  surface affectée calculée, responsable, société, compte analytique.
- Droits d'accès (`gest_agri.farm.access`) : utilisateur, exploitation, rôle
  `user`, `manager` ou `admin`, unicité d'un accès actif par couple
  exploitation/utilisateur.
- Site (`gest_agri.site`) : rattachement obligatoire à une exploitation.
- Parcelle (`gest_agri.plot`) : surface, site, type de sol, irrigation, pH,
  pente et coordonnées.
- Bâtiment (`gest_agri.building`) : type, surface et capacité.
- Infrastructure (`gest_agri.infrastructure`) : type, longueur et surface.
- Source d'eau (`gest_agri.water.source`) : type, débit et profondeur.
- Réseau d'irrigation (`gest_agri.irrigation.network`) : source d'eau, type et
  débit.
- Secteur d'irrigation (`gest_agri.irrigation.sector`) : réseau, surface et
  parcelles desservies.
- Pompe d'irrigation (`gest_agri.irrigation.pump`) : réseau, puissance et débit.

La surface affectée d'une exploitation est la somme des surfaces de ses
parcelles. Elle ne peut jamais dépasser la surface totale.

## Sécurité

Trois groupes sont définis :

- **Utilisateur agricole** : lecture des référentiels et des exploitations
  auxquelles il a accès.
- **Responsable agricole** : création et modification des référentiels de sa
  société, des exploitations qu'il gère et de leur patrimoine.
- **Administrateur agricole** : administration complète dans le périmètre de
  ses sociétés.

L'isolation par exploitation est appliquée par les domaines d'accès Odoo, donc
au niveau du serveur et non seulement des menus ou des boutons. Les domaines
sont invalidés lorsque les responsables ou les droits d'accès changent.

Un utilisateur non administrateur ne peut pas modifier ses propres droits
d'accès.

## Vues et menus

Les menus sont regroupés sous :

- **Exploitations** : exploitations, sites, parcelles, bâtiments,
  infrastructures, droits d'accès ;
- **Irrigation** : sources d'eau, réseaux, secteurs, pompes ;
- **Configuration** : les 13 référentiels.

La fiche d'une exploitation donne accès directement à ses sites, parcelles,
bâtiments, infrastructures, sources d'eau, réseaux et droits d'accès.

## Tests

Les tests couvrent :

- la création des référentiels et l'unicité des codes ;
- la création des exploitations, sites et parcelles ;
- l'unicité des codes par exploitation ;
- le rejet d'un site appartenant à une autre exploitation ;
- les surfaces négatives et le dépassement de la surface totale ;
- le calcul de la surface affectée ;
- la cohérence de société ;
- la création des droits d'accès et l'isolation entre utilisateurs ;
- les permissions par rôle.

Ils sont destinés à être exécutés dans une base de test Odoo 20 disposant du
module installé.

## Installation

1. Ajouter le répertoire parent au chemin des addons Odoo.
2. Mettre à jour la liste des modules.
3. Installer `Gestion Agricole`.

Aucun module complémentaire facultatif n'est requis.
