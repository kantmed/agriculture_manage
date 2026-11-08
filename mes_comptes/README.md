# Mes Comptes — Odoo 19 — Version 1.4

Module de gestion financière personnelle pour Odoo 19 Community.

## Fonctionnalités
- Comptes personnels en devises différentes (devise activée dans Odoo).
- **Partage de comptes** : un compte peut être attribué à plusieurs utilisateurs (champ *Utilisateurs partagés*). Les opérations, virements et dettes liées à ces comptes sont visibles par tous les utilisateurs partagés.
- Recettes et dépenses dans la devise du compte.
- Virements entre comptes, y compris entre devises, avec taux de change historique Odoo à la date du virement et possibilité de saisie manuelle.
- Dettes / créances et règlements générant une opération financière dans la même devise.
- Budgets par catégorie, période et devise.
- Tableau de bord OWL avec soldes, activité du mois comparée au mois précédent, évolution sur 12 mois et comparaison annuelle, sans additionner des devises différentes.
- Rapport financier PDF par période, avec synthèse par devise, détail des opérations, virements et règlements de dettes.
- Exports Excel des opérations, comptes, budgets, virements, dettes et règlements : ouvrez la liste correspondante, sélectionnez les lignes puis utilisez **Imprimer**.
- Historique des taux de change Odoo consultable par devise, société et date.
- Sécurité par utilisateur pour les données financières ; les catégories sont des référentiels partagés.

## Interface français / arabe
Le module fournit des catalogues de traduction `i18n/fr.po` et `i18n/ar.po`. L'interface standard (menus, formulaires, champs et libellés du tableau de bord OWL) suit la langue choisie pour l'utilisateur dans ses préférences Odoo. Pour utiliser l'arabe, installez/activez la langue arabe dans les paramètres de langues d'Odoo, puis choisissez-la dans les préférences de l'utilisateur. Odoo applique la direction droite-à-gauche (RTL) pour les langues configurées en RTL ; le tableau de bord inclut également des ajustements d'alignement.

Après remplacement du module, mettez-le à jour (`-u mes_comptes`) et assurez-vous que la langue arabe est installée dans la base. Les traductions couvrent les libellés principaux de l'application ; les libellés ajoutés ultérieurement devront être traduits dans les catalogues PO.

## Multi-devises
Activez les devises nécessaires dans Comptabilité > Configuration > Devises (les intitulés peuvent varier selon la configuration Odoo). Choisissez ensuite la devise de chaque compte.
Les taux historiques utilisent les cours configurés dans Odoo (`res.currency.rate`) et le cours le plus récent à la date du virement. Le menu **Historique des taux** affiche les cours disponibles. Sur un virement entre devises, le taux est proposé automatiquement ; activez **Taux manuel** pour le remplacer par le taux réellement convenu. Exemple : 1 EUR = 145 DZD, le taux manuel à saisir est 145.
Le module ne convertit jamais automatiquement tous les soldes vers une devise unique : les soldes sont présentés séparément afin d'éviter une addition financière incorrecte.

## Partage de comptes
Chaque compte possède un propriétaire (`Utilisateur`) et une liste d'utilisateurs partagés (`Utilisateurs partagés`). Les règles de sécurité Odoo (ir.rule) permettent d'accéder à :
- Les comptes dont on est le propriétaire ou qui sont dans la liste de partage.
- Les opérations, virements, dettes et budgets liés à ces comptes.

## Installation sur Odoo 19 Community
1. Décompresser l'archive.
2. Copier le dossier `mes_comptes` dans un répertoire d'addons personnalisé.
3. Ajouter ce répertoire à `addons_path` et rendre l'addon OCA `report_xlsx` disponible.
4. Redémarrer Odoo 19.
5. Mettre à jour la liste des applications et installer **Mes Comptes** (Odoo installe `report_xlsx` comme dépendance).
6. Attribuer le groupe **Mes Comptes / Utilisateur** à l'utilisateur concerné.

Commande possible :
```bash
./odoo-bin -d ma_base -u mes_comptes --stop-after-init
```

## Limites et tests avant production
Les taux historiques doivent être renseignés dans Odoo ; aucune synchronisation bancaire ni récupération automatique depuis un fournisseur externe n'est incluse. Avant production, tester les règles multi-utilisateurs, les partages de comptes, les annulations, les transferts avec taux automatique ou manuel, les arrondis monétaires, l'impression PDF et les exports Excel sur une base Odoo 19 de test.
