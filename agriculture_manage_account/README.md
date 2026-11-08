# Agriculture Management - Financial Accounts (Odoo 20)

Module technique : `agriculture_manage_account`  
Version : `20.0.1.0.0`  
Licence : LGPL-3

## Fonctionnalités

- Comptes financiers par société : caisse, banque ou autre, avec devise et journal Odoo facultatif.
- Recettes et dépenses agricoles classées par catégorie.
- Affectation facultative à une exploitation, une campagne, une parcelle, une opération, une récolte et un budget.
- Règlements complets ou partiels, avec suivi du montant réglé et du solde dû.
- Virements internes entre comptes de même société et de même devise.
- Consultation des créances et dettes non réglées.
- Analyses sous forme de graphiques et tableaux croisés dynamiques.
- Historique des modifications via le chatter.

## Dépendances

`agriculture_manage`, `agriculture_manage_crop`, `agriculture_manage_analysis`, `account`.

## Installation

1. Copier le dossier `agriculture_manage_account` dans le répertoire des addons personnalisés d'Odoo 20.
2. Redémarrer le serveur Odoo.
3. Actualiser la liste des applications.
4. Installer **Agriculture Management - Financial Accounts**.
5. Accéder à **Agriculture > Gestion financière**.

Mise à jour en ligne de commande :

```bash
./odoo-bin -c /chemin/odoo20.conf -d NOM_BASE -u agriculture_manage_account --stop-after-init
```

## Utilisation conseillée

1. Créer les comptes caisse et banque dans **Gestion financière > Comptes financiers**.
2. Créer une recette ou une dépense, choisir la société, le compte et, si nécessaire, l'affectation agricole.
3. Valider le mouvement.
4. Utiliser **Enregistrer un règlement** pour enregistrer un règlement total ou partiel.
5. Pour déplacer de l'argent entre deux comptes, créer un mouvement de type **Virement interne** puis le valider.

## Périmètre comptable

Cette version constitue un registre financier de gestion agricole et suit les soldes de trésorerie, règlements et montants dus. Le lien au journal comptable Odoo est facultatif et informatif : cette version ne génère pas automatiquement d'écritures dans le grand livre et ne remplace pas la comptabilité native Odoo.


## Comptabilité native (phase 4)

Les recettes et dépenses validées créent une facture client ou fournisseur native Odoo, à partir de l'article/service sélectionné. Les règlements se font ensuite depuis la facture avec le flux standard d'Odoo. Le mouvement agricole conserve le lien vers cette pièce et reprend son état de paiement. Les transferts internes restent du suivi agricole dans cette version. Voir `INTEGRATION_PHASE4_ACCOUNTING_INVOICES.md` à la racine de l'archive.


- Les factures fournisseurs peuvent être associées à un budget agricole. Les montants comptabilisés alimentent le réalisé budgétaire hors taxes, avec déduction des avoirs.
