# Agriculture Management - Sales (Odoo 20)

Extension des ventes Odoo pour relier la commercialisation aux campagnes et récoltes agricoles.

## Fonctionnalités
- Utilise les commandes clients natives `sale.order` et les lignes natives Odoo.
- Lie chaque commande à une campagne, une récolte validée et, facultativement, une parcelle.
- Conserve le workflow natif Odoo : confirmation, livraison via `sale_stock`, facturation et paiement via `account`.
- Ajoute un accès aux clients et commandes agricoles sous Agriculture > Commercialisation.
- Permet de créer manuellement une recette dans `agriculture_manage_account`, liée à la commande. Cette recette reste en brouillon et son règlement doit être enregistré dans la gestion financière ; aucune écriture financière n'est créée automatiquement afin d'éviter les doublons avec la comptabilité native.
- Ajoute un accès aux commandes liées depuis la fiche de récolte.

## Dépendances
`agriculture_manage`, `agriculture_manage_crop`, `agriculture_manage_stock`, `agriculture_manage_account`, `sale_stock`.

## Droits
Le menu Commercialisation est réservé au groupe natif Vendeur (`sales_team.group_sale_salesman`). Les droits sur les commandes, livraisons, factures et paiements restent ceux d'Odoo.

## Installation
Ajouter le dossier `agriculture_manage_sales` au `addons_path`, mettre à jour la liste des applications, puis installer le module. Pour une installation en ligne de commande :

```bash
./odoo-bin -c /CHEMIN/odoo20.conf -d NOM_BASE -i agriculture_manage_sales --stop-after-init
```
