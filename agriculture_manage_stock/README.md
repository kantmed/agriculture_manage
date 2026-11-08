# Agriculture Management - Stock

Addon Odoo 20 Community — version `20.0.1.2.0`.

## Flux opération agricole → stock

1. Une ligne d'opération est marquée « Consommer du stock », avec produit stockable, quantité, unité et magasin.
2. « Préparer la sortie de stock » crée un transfert interne Odoo du magasin vers l'emplacement virtuel de production. Les lignes sont regroupées par magasin.
3. L'utilisateur Inventaire réserve les quantités, renseigne les lots/séries si nécessaire, puis valide le transfert dans Odoo Stock.
4. Les transferts partiels et reliquats restent suivis par les liens entre lignes agricoles et mouvements Odoo. L'opération ne peut être clôturée que lorsque toutes les quantités demandées sont réellement sorties.
5. À la validation effective, la valeur des mouvements valorisés est agrégée sur la ligne agricole. L'analyse et le budget consomment cette valeur agrégée, sans relire ni recompter les mêmes écritures comptables.

## Garanties de cette version

- Une seule méthode crée les sorties liées aux opérations agricoles : le module Stock.
- La validation d'une opération ne crée plus un second transfert automatique.
- Un lien explicite `stock.move.agriculture_operation_line_id` permet de retrouver tous les mouvements d'une ligne, y compris les reliquats.
- Les transferts sont des documents natifs `stock.picking` / `stock.move`.
- Le module ne force pas la validation, la réservation ou la disponibilité : le flux standard Odoo Stock reste maître.
- L'annulation d'un travail annule ses transferts non terminés ; un travail avec transfert terminé ne peut pas être annulé directement.
- Le coût manuel `cost` est conservé ; l'analyse utilise la valorisation réelle lorsque celle-ci est disponible.

## Mise à jour

Sauvegarder la base et les dossiers des modules, remplacer les trois modules modifiés, puis mettre à jour :

```bash
./odoo-bin -c /CHEMIN/odoo20.conf -d NOM_BASE \
  -u agriculture_manage_crop,agriculture_manage_stock,agriculture_manage_analysis \
  --stop-after-init
```

Redémarrer ensuite Odoo et tester d'abord sur une base de préproduction. La valorisation automatique nécessite des catégories de produits configurées en valorisation automatisée, avec comptes de stock et journaux correctement paramétrés.

## Valorisation native (phase 2)

Le coût réel des intrants consommés est désormais synchronisé après la finalisation des mouvements de stock, à partir des couches `stock.valuation.layer` d'Odoo. Les retours au stock diminuent le coût net de l'opération. La méthode de coût, la valorisation automatisée et les comptes restent configurés dans les catégories de produits Odoo ; le module agricole ne crée pas de comptabilité parallèle.

## Comptabilité analytique native (phase 3)

Les exploitations, campagnes et parcelles peuvent être associées à des comptes analytiques Odoo. Les écritures de valorisation issues des mouvements de stock liés aux opérations agricoles reprennent ces dimensions sur les lignes de charges, sans modifier les écritures standard de valorisation.

Voir `INTEGRATION_PHASE3_ACCOUNTING_ANALYTICS.md` à la racine de l'application pour la configuration des plans analytiques et les contrôles à effectuer.
