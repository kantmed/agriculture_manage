# Phase 1 — Opérations agricoles ↔ Stock (Odoo 20)

## Objectifs
- Unifier la création des sorties de stock dans `agriculture_manage_stock`.
- Empêcher le double mouvement créé auparavant par la validation de l'opération culturale.
- Relier chaque mouvement `stock.move` à sa ligne agricole.
- Prendre en charge plusieurs mouvements pour une ligne (transferts partiels / reliquats).
- Ne clôturer le travail que lorsque la quantité demandée a réellement été sortie.
- Reprendre la valorisation native des mouvements terminés pour l'analyse et le budget.

## Modules modifiés
- `agriculture_manage_crop` : `action_validate()` ne crée plus de transfert ; il ne fait que clôturer l'opération.
- `agriculture_manage_stock` : création des transferts internes, liens mouvement-ligne, contrôles de quantités, annulation des transferts non terminés et agrégation de valorisation.
- `agriculture_manage_analysis` : le coût d'analyse utilise la valeur agrégée stockée sur la ligne agricole lorsqu'elle est disponible.

## Flux utilisateur
1. Sur une opération en brouillon, cocher « Consommer du stock » pour chaque intrant concerné.
2. Choisir produit, quantité, unité et magasin source.
3. Cliquer sur « Préparer la sortie de stock ».
4. Dans Inventaire, réserver, renseigner les lots/séries et valider le transfert.
5. Si Odoo crée un reliquat, le valider également.
6. Valider l'opération agricole. La clôture est refusée si les quantités réalisées sont insuffisantes.

## Valorisation comptable
La valorisation automatisée reste pilotée par Odoo Stock / Stock Accounting. Le module agricole lit la valeur du mouvement valorisé pour les analyses ; il ne crée aucune écriture `account.move` supplémentaire pour une consommation déjà comptabilisée par Odoo.

## Mise à jour
Faire une sauvegarde de la base et des trois dossiers avant remplacement. Déployer les trois modules modifiés puis exécuter :

```bash
./odoo-bin -c /CHEMIN/odoo20.conf -d NOM_BASE \
  -u agriculture_manage_crop,agriculture_manage_stock,agriculture_manage_analysis \
  --stop-after-init
```

Redémarrer Odoo. Tester d'abord en préproduction avec un produit stockable, une catégorie en valorisation automatisée, un stock initial disponible, un entrepôt et une campagne/parcelle.

## Limites / tests serveur requis
Les contrôles syntaxiques Python/XML ne remplacent pas un test d'installation et un test transactionnel sur l'instance Odoo 20. Vérifier notamment la création d'un reliquat, le retour d'un intrant, les lots/séries, la valorisation automatisée et les comptes de stock de la catégorie de produit.
