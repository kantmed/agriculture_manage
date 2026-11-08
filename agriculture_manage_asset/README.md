# Agriculture Management - Assets (Odoo 20 Community)

Module facultatif d'intégration agricole du moteur d'immobilisations fourni par `base_accounting_kit`.

## Périmètre de la version 20.0.1.0.0

- Aucun changement direct dans `base_accounting_kit`.
- Niveau d'affectation facultatif : non affectée, société/groupe, exploitation ou site.
- Réutilisation de `agriculture.farm`, `agriculture.farm.site` et des comptes analytiques des exploitations.
- Affectation d'une immobilisation de site à son exploitation propriétaire.
- Répartition en pourcentage des coûts d'une immobilisation partagée entre plusieurs exploitations (total obligatoire de 100 % lorsqu'une répartition est renseignée).
- Création depuis une ligne de facture fournisseur avec reprise de l'affectation agricole et lien anti-doublon.
- Conversion de la valeur de la ligne de facture vers la devise de la société avant création de l'immobilisation.
- Ventilation analytique des lignes de charges d'amortissement.
- Désactivation du regroupement des écritures d'amortissement dès qu'une catégorie contient des immobilisations agricoles, afin de ne pas mélanger des affectations analytiques différentes.

## Hypothèse de rattachement groupe

Dans les modèles livrés, une exploitation dépend d'une `res.company`. En l'absence d'un modèle autonome de groupe agricole, le niveau « Groupe / société » utilise donc la société Odoo comme périmètre commun. Si plusieurs sociétés juridiques doivent appartenir à un même groupe, un modèle de groupe distinct sera nécessaire dans une version ultérieure.

## Dépendances

- `base_accounting_kit` (moteur comptable et immobilisations)
- les modules agricoles de base, analytique et projets listés dans le manifeste.

## Installation

Installer les dépendances, copier les huit dossiers d'addons dans le chemin addons, mettre à jour la liste des applications puis installer `agriculture_manage_asset`.

Mise à jour en ligne de commande :

```bash
./odoo-bin -c /chemin/odoo.conf -d NOM_BASE -u agriculture_manage_asset --stop-after-init
```

Le test final doit être effectué sur la base de test Odoo 20 après vérification des dépendances Python et des modules du kit comptable.

## Version 20.0.1.0.3 – corrections après contrôle

- Ne charge plus le framework de tests pendant le démarrage normal d'Odoo.
- Remplace les anciennes contraintes `_sql_constraints` par `models.Constraint`.
- Ajoute le compte analytique sur le modèle d'exploitation existant `agriculture.farm` et son champ dans le formulaire existant.
- Corrige la validation des écritures d'amortissement pour ne poster que les écritures dont l'immobilisation est en confirmation automatique.
- Corrige l'affichage des pourcentages : les valeurs sont stockées de 0 à 100, sans multiplication visuelle par 100.

Le niveau « Groupe / société » reste limité aux exploitations appartenant à la même société Odoo. La gestion d'un groupe multi-sociétés nécessite un modèle de groupe explicite, qui n'est pas ajouté ici.


## Version 20.0.1.0.6 – immobilisation unique issue d'un projet

- Un projet d'investissement achevé peut générer une seule fiche d'immobilisation. Une contrainte SQL interdit la création d'une deuxième immobilisation pour le même projet.
- La fiche créée reprend le modèle d'immobilisation, le coût final validé, la société, l'exploitation éventuelle et le mode de réalisation (sous-traitance ou réalisation interne). Elle reste en brouillon pour contrôle comptable avant validation et démarrage des amortissements.
- Les lignes de factures fournisseurs rattachées à un projet sont traitées comme des coûts du projet et ne génèrent plus chacune une immobilisation indépendante. Les acquisitions directes sans projet conservent le mécanisme existant de création depuis la facture.
- Le formulaire Projet présente séparément les totaux des factures fournisseurs comptabilisées et les coûts saisis sur les opérations. Le coût final immobilisable est saisi après rapprochement : ces deux indicateurs ne sont volontairement pas additionnés automatiquement afin d'éviter un double comptage (par exemple achat de stock puis consommation dans une opération).
- La création de l'immobilisation ne poste pas une nouvelle écriture de capitalisation : elle crée la fiche dans le moteur `base_accounting_kit`. Le traitement comptable de la valeur d'entrée doit être rapproché avec les écritures de construction/immobilisation en cours de la société avant validation en production.
