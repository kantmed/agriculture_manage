# Phase 5 — Budgets agricoles et comptabilité native Odoo 20

## Objectif

Le budget agricole compare le prévisionnel aux coûts réellement constatés. Les opérations agricoles validées restent la source du coût des travaux et consommations. Les dépenses complémentaires sont désormais reprises depuis les factures fournisseurs natives Odoo, et non depuis un registre manuel parallèle.

## Fonctionnement

- Une facture fournisseur peut être associée à un budget via le champ **Budget agricole** sur la facture.
- Lorsqu'une dépense est créée depuis **Mouvements financiers**, le budget sélectionné est transmis automatiquement à la facture fournisseur créée.
- Seules les factures fournisseurs et avoirs fournisseurs **comptabilisés** sont pris en compte. Les factures brouillon et annulées sont exclues.
- Le montant retenu est la somme hors taxes des lignes comptables de produits/services, en devise de la société. Les avoirs diminuent le réalisé.
- Les produits stockables sont exclus des factures d'achat : leur coût est intégré au budget au moment de leur consommation dans une opération agricole, afin d'éviter un double comptage entre achat et consommation.
- Les factures déjà rattachées à une opération agricole sont exclues du supplément budgétaire afin d'éviter de compter deux fois les coûts déjà issus des opérations/valorisations de stock.
- Les lignes de budget « Main-d'œuvre » reprennent les mouvements financiers de catégorie `labor`; les autres factures liées au budget alimentent « Autres dépenses ».
- Le total réalisé additionne le coût des opérations agricoles et les factures fournisseurs complémentaires.

## Utilisation

1. Créer et confirmer un budget pour une campagne.
2. Créer un mouvement financier de type **Dépense**.
3. Sélectionner exploitation, campagne, parcelle si applicable, budget, fournisseur et article/service.
4. Valider le mouvement : Odoo crée et comptabilise la facture fournisseur native.
5. Consulter le budget : le total des dépenses comptabilisées et les écarts sont recalculés.
6. Les paiements restent gérés depuis la facture native Odoo.

## Données historiques

Les anciennes lignes de « Dépenses complémentaires » sont conservées à titre d'historique, mais ne sont plus considérées comme des dépenses réelles comptables. La validation de ces lignes manuelles est bloquée : saisir les nouvelles dépenses via les mouvements financiers et les factures fournisseurs.

## Limites / vérifications nécessaires

- Cette phase ne crée pas de contrôle bloquant en cas de dépassement : elle signale le dépassement dans le budget.
- Les montants sont hors taxes et exprimés en devise de la société.
- Les tests transactionnels doivent être exécutés sur une base de test Odoo 20 Community avant déploiement en production.
