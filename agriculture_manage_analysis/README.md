# Agriculture Management - Analysis & Profitability
Version 19.0.1.1.0

## Tableau de bord général
- Comparaison des coûts des travaux, des recettes et des marges brutes.
- Analyse par exploitation et par culture.
- Vue pivot avec surface, coût total, recettes, marge brute, coût/ha et marge/ha.
- Filtres par campagne active/terminée et marge positive/négative.
- Analyses détaillées par campagne et par parcelle conservées.

## Mise à jour
```bash
./odoo-bin -c /mnt/srv/share/odoo19/odoo/odoo.conf -d odoo1900 -u agriculture_manage_analysis --stop-after-init
```

Les montants sont exprimés dans la devise de la société liée à chaque campagne.
Filtrer séparément les sociétés utilisant des devises différentes avant de comparer les montants.


## Budgets et comptabilité native

Depuis la phase 5, les dépenses réelles complémentaires sont calculées à partir des factures fournisseurs Odoo comptabilisées et associées au budget. Les anciennes lignes de dépenses manuelles sont conservées à titre d'historique mais ne remplacent pas une pièce comptable. Voir `INTEGRATION_PHASE5_BUDGET_ACCOUNTING.md` à la racine de l'archive.
