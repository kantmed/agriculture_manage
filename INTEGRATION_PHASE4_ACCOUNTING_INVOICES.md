# Phase 4 — Recettes et dépenses avec Odoo Comptabilité

## Principe

Odoo Comptabilité devient le registre de référence des factures, avoirs et règlements. Les mouvements agricoles restent des fiches de suivi et portent un lien vers une pièce comptable native ; ils ne créent pas de seconde comptabilité.

## Recettes et dépenses manuelles

1. Créer un mouvement de type recette ou dépense.
2. Renseigner le partenaire, l'article/service, le montant, la devise et les dimensions agricoles.
3. Configurer sur l'article son compte de produit ou de charge et ses taxes.
4. Valider le mouvement : le module crée et comptabilise une facture client (`out_invoice`) ou une facture fournisseur (`in_invoice`).
5. Utiliser le bouton d'ouverture de la pièce pour enregistrer les paiements avec le bouton natif « Enregistrer un paiement » d'Odoo.
6. Le statut payé/partiel/non payé est repris depuis la pièce comptable native.

Les virements internes restent des mouvements de suivi dans cette phase ; ils ne génèrent pas de facture.

## Ventes agricoles

La commande client conserve ses dimensions exploitation/campagne/parcelle/récolte. À la création des factures depuis la commande, ces dimensions sont copiées sur les factures natives. Le bouton « Créer la recette agricole » ouvre la facture native ou la crée si elle n'existe pas ; il ne génère plus un mouvement financier parallèle.

## Analytique

La facture créée depuis un mouvement agricole reçoit une distribution analytique basée sur les comptes renseignés sur l'exploitation, la campagne et la parcelle. Les factures de vente conservent leurs dimensions agricoles ; les lignes de facture restent pilotées par les comptes et taxes des articles.

## Vérifications nécessaires

- Configurer les comptes de revenus/charges et taxes sur les articles.
- Vérifier les journaux de vente et d'achat, les comptes clients/fournisseurs et les droits comptables.
- Tester facture client, facture fournisseur, règlement partiel, règlement complet, avoir et annulation.
- Vérifier que les ventes depuis une commande ne créent pas de doublon de recette agricole.

Cette phase a passé les contrôles statiques Python/XML ; l'installation et les transactions réelles doivent être validées sur l'instance Odoo 20 cible.
