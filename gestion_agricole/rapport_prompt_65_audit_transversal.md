# Prompt 65 — Audit transversal et planification

**Projet :** Gestion Agricole  
**Module :** `gestion_agricole` — Odoo 20 Community  
**Date de l’audit :** 12 novembre 2026  
**Périmètre de code principal :** `/tmp/opencode/dev/gestion_agricole/`  
**Comparaison :** `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/`

## 1. Méthode et limites

Audit statique en lecture seule des modèles Python, des vues et menus XML, des données de séquence, du manifeste, des contrôles d’accès, des tests et du cahier des charges. Les comptages ont été établis à partir des fichiers du module de développement. Les sources Odoo 20 ont été consultées en lecture seule pour interpréter le mécanisme `ir.access` utilisé par cette version.

Aucune base PostgreSQL n’a été interrogée, aucun service redémarré et aucune campagne de tests exécutée. Par conséquent, les conclusions décrivent le code et les déclarations présentes dans les fichiers, pas l’état d’une base installée ni le résultat d’une exécution actuelle. Les résultats historiques mentionnés dans les rapports antérieurs restent des déclarations lorsqu’aucun journal d’exécution n’est joint au dépôt.

Le dossier de développement et le module installé ont les mêmes contenus pour `models/`, `views/`, `tests/`, le manifeste et `security/ir.access.csv` (comparaison de fichiers, sans tenir compte des caches Python). Un rapport historique supplémentaire et des caches diffèrent ; aucun code métier divergent n’a été relevé dans ces répertoires comparés.

## 2. État général

Le module est un addon monolithique organisé en domaines par sous-répertoires et menus. Il comprend **66 modèles déclarés**, dont **7 classes d’extension** (cibles : `res.users`, `gest_agri.animal` et `gest_agri.animal.lot`). Parmi les extensions, deux ciblent des modèles agricoles déjà déclarés et une étend le modèle standard `res.users`.

Le code couvre un socle de patrimoine agricole, les campagnes et opérations végétales, l’irrigation, l’élevage, la santé, l’alimentation, la reproduction, la production animale, le matériel, le personnel et une saisie économique élémentaire. Les achats, les mouvements de stock, la vente, les livraisons et la comptabilité ne sont pas opérationnellement intégrés dans les modèles examinés, même si plusieurs dépendances Odoo correspondantes sont déclarées.

Comptages statiques des déclarations XML : **192 vues `ir.ui.view`**, **68 actions `ir.actions.act_window`** et **91 éléments `<menuitem>`**. Les vues de production animale seules en comptent 28 et 13 actions. Les nombres globaux diffèrent donc des nombres communiqués dans les rapports Prompt 64, qui portaient sur son périmètre fonctionnel.

## 3. Tableau récapitulatif des domaines

Les nombres ci-dessous comptent les modèles déclarés dans les fichiers du domaine. Les modèles partagés ou transversaux (configuration, patrimoine, extensions) sont indiqués dans la colonne relations et ne sont pas réattribués artificiellement à plusieurs lignes.

| Domaine | État dans le code | Modèles déclarés dans le périmètre | Principales capacités visibles | Vues / actions vérifiables | Sécurité / tests |
|---|---|---:|---|---|---|
| Socle agricole et référentiels | Développé | 13 référentiels de configuration, plus l’extension `res.users` | Référentiels de cultures, espèces, types, variétés, réservations et affectation des exploitations aux utilisateurs | `configuration_views.xml` : 39 / 13 | ACL présentes pour les référentiels ; tests `test_configuration.py`, `test_reservation_unicity.py`, `test_security.py` |
| Exploitations et sociétés | Développé | 1 (`gest_agri.farm`) + 1 (`gest_agri.farm.access`); extension standard `res.users` | Exploitation rattachée à une société, responsables et droits d’accès par exploitation | `farm_views.xml` : 6 / 2 | ACL par rôle et domaine ; `test_patrimony.py`, `test_security.py` |
| Sites et parcelles | Développé | 2 (`gest_agri.site`, `gest_agri.plot`) | Hiérarchie exploitation/site/parcelle, surfaces et références de sol/culture | Inclus dans `patrimony_views.xml` : 15 / 5 | ACL déclarées ; tests patrimoine et cycles culturaux |
| Bâtiments et infrastructures | Développé | 2 (`gest_agri.building`, `gest_agri.infrastructure`) | Inventaire rattaché à une exploitation et, le cas échéant, à un site | Inclus dans `patrimony_views.xml` : 15 / 5 | ACL déclarées ; `test_patrimony.py` |
| Production végétale | Partiellement à fonctionnellement développé | 4 modèles de cycle métier, avec 13 référentiels transversaux | Cycles, interventions, récoltes, campagnes et liens économiques côté végétal | `production_views.xml` 6 / 2, `production_intervention_views.xml` 3 / 1, `harvest_views.xml` 3 / 1 | ACL présentes ; tests campagne, cycle, intervention et récolte |
| Campagnes et cycles culturaux | Développé | 2 (`gest_agri.crop.campaign`, `gest_agri.crop.cycle`) | Campagne rattachée à l’exploitation ; cycle reliant campagne, parcelle et opérations | Inclus dans les vues production : 6 / 2 pour les fichiers dédiés | ACL et tests spécifiques présents |
| Interventions agricoles | Développé | 1 (`gest_agri.crop.intervention`) | Opération datée, type d’opération, campagne/cycle/parcelle et ressources de saisie | `production_intervention_views.xml` : 3 / 1 | ACL présentes ; `test_crop_intervention.py` |
| Récoltes | Développé | 1 (`gest_agri.crop.harvest`) | Récolte reliée à un cycle, une parcelle, une campagne et une unité | `harvest_views.xml` : 3 / 1 | ACL présentes ; `test_crop_harvest.py` |
| Élevage et cheptel | Développé | 2 (`gest_agri.animal`, `gest_agri.animal.lot`) | Suivi des animaux individuels et des lots ; modèles étendus par santé, reproduction et production | `livestock_views.xml` : 6 / 2 | ACL présentes mais doublons de lignes ; `test_livestock.py`, tests des domaines associés |
| Alimentation animale | Développé, avec réserve d’accès sur les lignes | 5 (`feed`, `feed.ration`, `feed.ration.line`, `feed.distribution`, `feed.distribution.line`) | Aliments, compositions de rations et distributions à l’animal ou au lot | `feeding_views.xml` : 9 / 3 | ACL sur 3 des 5 modèles seulement ; `test_feeding.py` |
| Santé animale | Développé | 6 | Dossiers sanitaires, maladies, traitements, vaccinations, interventions et consultations | `health_views.xml` : 20 / 7 | ACL présentes ; `test_health.py` |
| Reproduction animale | Développé | 5 | Événements, gestations, mises bas, nouveau-nés et mortalité | `reproduction_views.xml` : 16 / 5 | ACL présentes ; `test_reproduction.py`, `test_reproduction_audit.py` |
| Production animale | Développé selon le périmètre Prompt 64 | 10 nouveaux modèles | Lait/traite/qualité, œufs/qualité, viande, pesées et catégories d’œufs ; extensions animal et lot | `animal_production_views.xml` : 28 / 13 | ACL présentes ; `test_animal_production.py` contient 100 méthodes `test_` |
| Irrigation | Développé pour l’infrastructure et les opérations, sans intégration de consommation comptable | 1 opération dans `irrigation/`, plus 5 équipements hydrauliques dans `patrimony/` | Sources, réseaux, secteurs, pompes et opérations d’irrigation | `irrigation_views.xml` : 9 / 3 ; `irrigation_operation_views.xml` : 3 / 1 ; patrimoine partagé | ACL présentes ; `test_irrigation.py`, `test_patrimony.py` |
| Matériel agricole | Développé en modèles propres | 3 (`equipment`, `equipment.usage`, `equipment.maintenance`) | Parc, usage et maintenance gérés par le module agricole | `equipment_views.xml` : 9 / 3 | ACL présentes ; `test_equipment.py` |
| Personnel agricole | Développé en modèles propres | 4 (`worker`, `team`, `work.assignment`, `work.time`) | Travailleurs, équipes, affectations et temps de travail | `personnel_views.xml` : 12 / 4 | ACL présentes ; `test_personnel.py` |
| Économie agricole | Partiellement développé | 3 (`economic.category`, `economic.expense`, `economic.revenue`) | Saisie manuelle de charges/recettes et rattachements végétaux ; pas de calcul transversal de marges | `economy_views.xml` : 8 / 3 | ACL présentes ; `test_economy.py` |

**Interprétation des états :** « développé » signifie qu’un modèle et des vues/opérations sont présents ; cela ne certifie pas une recette de déploiement complète. « Partiellement développé » signale un écart important avec le cahier des charges, notamment l’absence d’intégrations ou de calculs attendus. Les fonctionnalités seulement annoncées dans le cahier des charges ne sont pas comptées comme réalisées.

## 4. Inventaire technique des modèles

Les 66 modèles `_name` trouvés dans les fichiers Python sont les suivants :

- **Configuration (13)** : `gest_agri.treatment.type`, `gest_agri.fertilizer.type`, `gest_agri.crop.type`, `gest_agri.building.type`, `gest_agri.livestock.species`, `gest_agri.crop.variety`, `gest_agri.farm.type`, `gest_agri.soil.type`, `gest_agri.operation.type`, `gest_agri.livestock.breed`, `gest_agri.production.type`, `gest_agri.equipment.type`, `gest_agri.irrigation.type`.
- **Patrimoine (10)** : `gest_agri.farm`, `gest_agri.farm.access`, `gest_agri.site`, `gest_agri.plot`, `gest_agri.building`, `gest_agri.infrastructure`, `gest_agri.water.source`, `gest_agri.irrigation.network`, `gest_agri.irrigation.sector`, `gest_agri.irrigation.pump`.
- **Production végétale (4)** : `gest_agri.crop.campaign`, `gest_agri.crop.cycle`, `gest_agri.crop.intervention`, `gest_agri.crop.harvest`.
- **Élevage (2)** : `gest_agri.animal`, `gest_agri.animal.lot`.
- **Alimentation (5)** : `gest_agri.feed`, `gest_agri.feed.ration`, `gest_agri.feed.ration.line`, `gest_agri.feed.distribution`, `gest_agri.feed.distribution.line`.
- **Santé (6)** : `gest_agri.animal.disease`, `gest_agri.animal.health`, `gest_agri.vaccination`, `gest_agri.animal.treatment`, `gest_agri.sanitary.intervention`, `gest_agri.veterinary.consultation`.
- **Reproduction (5)** : `gest_agri.animal.reproduction`, `gest_agri.animal.gestation`, `gest_agri.animal.birth`, `gest_agri.animal.birth.newborn`, `gest_agri.animal.mortality`.
- **Production animale (10)** : `gest_agri.milk.production`, `gest_agri.milk.quality`, `gest_agri.egg.production`, `gest_agri.egg.production.line`, `gest_agri.egg.quality`, `gest_agri.egg.category`, `gest_agri.milking.session`, `gest_agri.milking.session.line`, `gest_agri.meat.production`, `gest_agri.animal.weight`.
- **Irrigation (1)** : `gest_agri.irrigation.operation`.
- **Matériel (3)** : `gest_agri.equipment`, `gest_agri.equipment.usage`, `gest_agri.equipment.maintenance`.
- **Personnel (4)** : `gest_agri.worker`, `gest_agri.team`, `gest_agri.work.assignment`, `gest_agri.work.time`.
- **Économie (3)** : `gest_agri.economic.category`, `gest_agri.economic.expense`, `gest_agri.economic.revenue`.

Sept classes portent `_inherit` : extension de `res.users`, extension de `gest_agri.animal` par les domaines reproduction, santé et production animale, et extension de `gest_agri.animal.lot` par ces trois mêmes domaines. Il y a donc **deux modèles métier étendus** et **un modèle Odoo standard étendu**.

## 5. Relations entre domaines

| Flux demandé | Constat dans les champs et méthodes du code |
|---|---|
| Exploitation → site → parcelle | Présent. Les sites et parcelles portent une exploitation ; la parcelle peut être rattachée à un site. Les vérifications doivent tenir compte du fait que certaines relations vers des documents agricoles sont facultatives. |
| Parcelle → campagne → cycle → intervention → récolte | Présent, avec rattachements directs en plus des liens via le cycle. Cycle, intervention et récolte relient plusieurs de ces entités ; des contrôles de cohérence existent, mais ils ne sont pas uniformément exprimés comme contraintes sur toutes les écritures. |
| Exploitation → cheptel → animal → reproduction | Présent : animaux et lots se rattachent à l’exploitation ; reproduction relie animaux, gestations et mises bas. Les vues/actions de consultation sont déclarées. |
| Animal → santé → traitements/vaccinations | Présent par liens d’animal, lot et dossiers. Les données sanitaires utilisent aussi `res.partner` pour les vétérinaires. |
| Animal → alimentation → rations/distributions | Présent pour aliment, ration, lignes de ration, distribution et lignes de distribution. Les deux modèles de lignes n’ont pas de ligne d’accès dans `ir.access.csv`, anomalie prioritaire à valider/corriger dans une mission de correction séparée. |
| Animal → production laitière/viande/œufs | Présent avec des extensions `gest_agri.animal` et `gest_agri.animal.lot` et des liens vers les nouveaux enregistrements de production. |
| Exploitation → irrigation → réseaux/secteurs/opérations | Présent pour les objets d’infrastructure et les opérations. Les pompes référencent un équipement agricole interne ; l’intégration avec les mouvements de stock, la comptabilité analytique ou une mesure automatique de consommation n’est pas observée. |
| Exploitation → matériel → usages/maintenance | Présent dans les modèles agricoles internes. La maintenance n’est pas reliée au modèle natif `maintenance.equipment` dans le code repéré. |
| Exploitation → personnel → affectations → temps | Présent. Les affectations peuvent être reliées à parcelle, cycle et intervention ; le personnel est un modèle maison relié éventuellement à `res.partner` et `res.users`, pas à `hr.employee`. |
| Production agricole/animale → économie | Charges et recettes sont rattachables aux cycles et opérations végétales ; les revenus référencent une récolte. Les liens directs aux productions animales et aux modèles Odoo de facturation/comptabilité ne sont pas présents. Aucun calcul consolidé de coût complet ou de marge n’a été identifié. |

Les liens directs et indirects sont donc réels, mais leur présence ne garantit ni validation de toute cohérence inter-société, ni alimentation automatique des coûts. Les champs de société dérivés de l’exploitation sont courants et plusieurs modèles activent `_check_company_auto`; un contrôle systématique champ par champ reste nécessaire avant d’étendre les flux commerciaux.

## 6. Intégrations Odoo déclarées et réellement observées

Le manifeste déclare `base`, `mail`, `contacts`, `uom`, `product`, `stock`, `stock_account`, `purchase`, `sale_management`, `account`, `analytic` et `maintenance`. Il ne déclare pas `hr`.

| Dépendance | Utilisation concrète repérée | Évaluation |
|---|---|---|
| `base` | `res.company`, `res.users`, séquences, groupes, accès, monnaie et modèles ORM standards | Utilisée comme socle. |
| `mail` | Plusieurs modèles utilisent `mail.thread` ; exploitation utilise aussi `mail.activity.mixin` | Intégration effective pour le chatter sur les modèles concernés. |
| `contacts` | Liens à `res.partner` pour contacts, fournisseurs, clients et vétérinaires | Usage de contacts effectif, sans flux transactionnel natif. |
| `uom` | Liens vers `uom.uom` sur quantités, productions et rations | Références d’unités utilisées ; aucune conclusion d’homogénéité fonctionnelle complète sans tests. |
| `product` | Dépendance au manifeste ; pas de champ ou appel opérationnel vers `product.product` / `product.template` trouvé dans les modèles métier | Pas d’intégration fonctionnelle démontrée. Les types d’intrants sont des référentiels maison. |
| `stock`, `stock_account` | Dépendances au manifeste ; pas de flux `stock.move`, `stock.picking`, quantités de stock ou lot Odoo trouvé dans les modèles métier | Pas d’intégration de mouvements/traçabilité opérationnelle démontrée. |
| `purchase` | Dépendance au manifeste ; aucune relation/code de commande fournisseur trouvé | Pas de processus d’achat opérationnel démontré. |
| `sale_management` | Dépendance au manifeste ; aucune relation/code de commande client ou livraison trouvé | Pas de processus de vente opérationnel démontré. |
| `account` | Dépendance au manifeste ; aucun lien `account.move`/ligne comptable observé | Les charges/recettes restent des objets agricoles manuels, sans intégration comptable démontrée. |
| `analytic` | Dépendance au manifeste ; aucun compte ou ligne analytique relié trouvé | Aucune imputation analytique démontrée. |
| `maintenance` | Dépendance au manifeste ; le module possède ses propres modèles `gest_agri.equipment.maintenance` et `gest_agri.equipment` | Pas de lien natif démontré avec `maintenance.equipment` ou ses demandes. |
| `hr` | Absente du manifeste et aucune relation `hr.employee` repérée | Intégration RH absente ; le personnel est un référentiel agricole séparé. |

Aucune dépendance circulaire interne n’est déclarée : un seul addon porte ces domaines et le manifeste dépend des modules standards. Cette observation statique ne remplace pas l’analyse du graphe réel de modules installés. Le fait que `sale_management`, `purchase`, `stock` ou `account` figurent au manifeste ne suffit pas à qualifier leur intégration d’opérationnelle.

## 7. Sécurité transversale

### Groupes et mécanisme

`security/security.xml` définit trois groupes : `group_gest_agri_user`, `group_gest_agri_manager` et `group_gest_agri_admin`, avec héritage progressif des groupes et inclusion de `base.group_user` au niveau utilisateur agricole. La sécurité d’Odoo 20 est fournie ici par des enregistrements `ir.access` avec une opération et un domaine (et non par les colonnes historiques `perm_read` etc.). Le fichier contient **200 lignes de données** couvrant **64 modèles distincts**.

Les domaines observés appliquent généralement : accès de l’utilisateur à ses exploitations, accès du responsable aux exploitations gérées, et restriction de l’administrateur aux sociétés actives ; les référentiels partagés peuvent être visibles lorsque `company_id` est vide. L’extension `res.users` calcule les exploitations accessibles et gérées avec `compute_sudo=True`; quelques recherches utilisent explicitement `sudo()` pour vérifier l’unicité ou calculer l’accès. Ces usages sont sensibles et demandent une revue ciblée des domaines, mais aucun contournement n’a été exécuté dans cet audit.

### Anomalies de couverture

1. `gest_agri.feed.ration.line` et `gest_agri.feed.distribution.line` sont déclarés comme modèles avec leurs propres droits ORM, mais ne sont présents dans aucune ligne de `security/ir.access.csv`. Dans le mécanisme Odoo 20, aucun droit explicite n’est alors accordé par ces lignes : les opérations via les lignes de relation peuvent échouer pour les groupes métier. À confirmer par un scénario de test de sécurité dédié avant utilisation.
2. Les lignes d’accès des modèles `gest_agri.animal` et `gest_agri.animal.lot` apparaissent deux fois avec les mêmes identifiants externes. Ceci donne six lignes CSV pour chacun de ces modèles et doit être nettoyé/validé afin d’éviter un chargement répétitif ambigu.
3. Les modèles de lignes des rations/distributions n’ont pas de règle d’accès enfant explicite qui exprime l’héritage du domaine de l’exploitation par le parent. L’ajout éventuel doit être conçu avec les mêmes groupes et contraintes de société.
4. Des validations de cohérence visibles dans certains `create()` ne sont pas toutes doublées par des contraintes applicables aux `write()`. Une revue sécurité/intégrité doit contrôler les changements de liens après création, notamment exploitation/campagne/cycle/intervention.
5. Plusieurs modèles protègent leurs transitions par méthodes d’action et verrouillent certaines écritures/suppressions après validation ; cette pratique n’est pas démontrée de façon uniforme pour les 66 modèles. Les suppressions restent possibles sur certains objets selon leurs états et `ondelete`.

Aucun `ir.rule` XML séparé n’est défini dans `security.xml`; les domaines sont portés par `ir.access.csv`. La protection par exploitation ne doit pas être considérée uniforme sans compléter la vérification des relations enfants et des opérations par lot.

## 8. Qualité technique transversale

- **Organisation/imports :** organisation par domaines sous `models/`; les modules métier sont importés depuis `models/__init__.py`, y compris production animale et extension `res_users`. Les 79 fichiers présents sous `models/` comprennent des modules d’initialisation et des modèles ; les 66 déclarations ont été extraites des classes.
- **Manifeste :** version `20.0.1.0.0`, addon installable/application, liste des vues et séquences explicite. Les dépendances Odoo de vente/achat/stock/comptabilité sont plus larges que les intégrations actuellement trouvées.
- **XML :** 17 fichiers sous `views/`, contenant 192 enregistrements de vue et 68 actions fenêtre selon le champ `model` des records. Les fichiers de production animale comptent 28 vues et 13 actions ; les vues de configuration sont particulièrement nombreuses (39 vues et 13 actions). Les XML de données de séquence sont chargés depuis le manifeste.
- **Références externes :** les références de groupes et de séquences sont abondantes ; aucun test d’installation ni validation en base n’a été relancé. La résolution effective de tous les XML IDs n’est donc pas certifiée par le présent audit.
- **Relations/sociétés :** `_check_company_auto` et `check_company=True` sont utilisés, mais pas systématiquement sur toutes les relations. Les modèles économiques illustrent des liens à `plot_id`, `campaign_id`, `cycle_id`, `intervention_id` (ou `harvest_id`) sans `check_company=True`; certaines cohérences sont vérifiées explicitement, mais il faut confirmer la couverture lors des mises à jour et imports.
- **Calculs :** calculs stockés et dépendances `@api.depends` sont présents dans différents domaines. Une revue de toutes les dépendances de calcul et de l’usage de `compute_sudo` n’a pas été menée sur chaque champ ; aucune affirmation de complétude n’est faite.
- **États :** les documents opérationnels comportent plusieurs workflows (par exemple brouillon/terminé/annulé pour les sessions de traite ; Prompt 64 rapporte `draft → done → cancelled`). Les états et garde-fous diffèrent selon le domaine. Les verrouillages de modification après validation et les réversibilités doivent faire l’objet d’une matrice transversale dédiée.
- **Suppressions :** le code combine `cascade`, `restrict` et `set null`; leur effet métier sur les documents validés n’est pas uniforme. Les enregistrements archivables utilisent aussi `active`.
- **Contraintes :** contraintes SQL et Python sont présentes dans certains modèles, mais aucune preuve d’une couverture uniforme ou d’une vérification d’installation en base n’a été produite.
- **Rapports/tableaux de bord :** aucun ensemble de rapports de gestion ou tableau de bord transversal n’a été identifié dans les dossiers fonctionnels consultés ; `report/` ne contient qu’un fichier d’initialisation.
- **Wizards :** le répertoire `wizard/` ne contient qu’un fichier d’initialisation, sans assistant métier implémenté.

## 9. État des tests

### Présence dans le code

Le dossier `tests/` contient **21 fichiers `test_*.py`** et **761 définitions de méthodes `test_`** repérées textuellement. Répartition des méthodes statiques :

| Fichier | Méthodes `test_` |
|---|---:|
| `test_animal_production.py` | 100 |
| `test_audit_prompt11.py` | 25 |
| `test_configuration.py` | 8 |
| `test_crop_campaign.py` | 25 |
| `test_crop_cycle.py` | 36 |
| `test_crop_cycle_campaign.py` | 29 |
| `test_crop_harvest.py` | 42 |
| `test_crop_intervention.py` | 39 |
| `test_economy.py` | 37 |
| `test_equipment.py` | 35 |
| `test_feeding.py` | 38 |
| `test_health.py` | 60 |
| `test_irrigation.py` | 23 |
| `test_livestock.py` | 36 |
| `test_module_install.py` | 1 |
| `test_patrimony.py` | 39 |
| `test_personnel.py` | 35 |
| `test_reproduction.py` | 63 |
| `test_reproduction_audit.py` | 41 |
| `test_reservation_unicity.py` | 26 |
| `test_security.py` | 23 |

Ce comptage textuel ne garantit pas la découverte ou l’exécution de chacune de ces méthodes par le runner Odoo.

### Exécution et chiffres antérieurs

Aucun journal d’exécution récent n’a été trouvé parmi les fichiers de code audités et aucun test n’a été relancé. Les rapports Prompt 64 indiquent **100 tests nouveaux**, **237 tests de régression** et **337 au total**, sans échec/erreur ; cette mission ne peut pas en confirmer la provenance ni la réussite actuelle. L’écart entre ces chiffres rapportés et les 761 définitions présentes dans le code doit être expliqué par périmètre, sélection du runner ou évolution de la suite avant d’utiliser ces nombres comme indicateur global.

- **Présents dans le code :** 21 fichiers, 761 définitions `test_`.
- **Effectivement exécutés et prouvés ici :** aucun.
- **Réussis/échoués/ignorés lors de cette mission :** non applicable, aucune exécution.
- **Couverture à renforcer :** accès des lignes alimentation, intégrations Odoo natives, flux multi-société multi-exploitation, cohérence après `write()`, calcul de coût/marge, vente/achat/stock et suppression des documents validés.

## 10. Anomalies et écarts à traiter

| Priorité | Constat vérifié | Impact / suite recommandée |
|---|---|---|
| P1 | Aucune entrée `ir.access` pour `gest_agri.feed.ration.line` et `gest_agri.feed.distribution.line` | Vérifier les opérations du formulaire One2many et ajouter des droits/domaine cohérents dans une mission de correction distincte. |
| P1 | Trois entrées `ir.access` de l’animal et trois du lot sont dupliquées sous les mêmes identifiants externes | Valider le chargement puis dédupliquer les lignes. |
| P1 | Les contrôles d’accès des lignes enfants ne démontrent pas l’isolation par exploitation/société héritée du parent | Tester les accès directs et via relation pour utilisateur, responsable et administrateur. |
| P1 | Intégrations `purchase`, `stock`, `sale_management`, `account`, `analytic`, `product`, `stock_account` déclarées, mais aucun flux transactionnel métier trouvé | Ne pas présenter ces modules comme opérationnels ; construire des flux natifs avant d’automatiser coûts/marges. |
| P1 | Le cahier des charges exige coûts issus des données réelles, mais économie est une saisie manuelle et ne couvre pas les produits animaux | Définir les sources, règles d’imputation et liens au stock/comptabilité avant le calcul de marges. |
| P2 | Pas de lien `hr.employee` et `hr` absent du manifeste | Décider si le personnel agricole reste autonome ou se rattache au RH Odoo. |
| P2 | Matériel et maintenance utilisent des modèles propres malgré la dépendance `maintenance` | Décider de la frontière métier et du lien aux équipements natifs pour éviter une double gestion. |
| P2 | Plusieurs contrôles de cohérence sont dans `create()` ou sur un sous-ensemble de champs ; couverture de `write()` non uniforme | Ajouter des tests de mutation et homogénéiser les contraintes à la prochaine mission technique. |
| P2 | Vues et actions totalisent 192/68, différents des métriques ciblées Prompt 64 (28/13) | Utiliser un périmètre de comptage explicite dans les prochains rapports. |
| P2 | Rapports annoncent 337 tests réussis, tandis que le code contient 761 méthodes `test_` | Réconcilier le filtre d’exécution, les logs et les méthodes présentes avant toute communication de couverture globale. |
| P3 | Décisions de cadrage toujours ouvertes : gestion des stocks, intégration comptable, traçabilité des lots, rotations, certifications, subventions et langue des rapports | Décider celles qui conditionnent l’approvisionnement et la commercialisation. |

## 11. Feuille de route priorisée

1. **Réparer/valider les contrôles d’accès et cohérences transversales** : traiter les deux modèles enfants sans accès, dédupliquer les identifiants d’accès, couvrir l’héritage des domaines et vérifier les `write()` inter-sociétés. Ce travail de sécurisation doit précéder un usage multi-utilisateur élargi.
2. **Approvisionnements et intrants liés au stock Odoo** : relier intrants agricoles, achats, réceptions et mouvements de stock aux exploitations/campagnes/interventions ; définir lots et unités. C’est le socle de données réelles nécessaire aux coûts.
3. **Commercialisation et logistique** : relier récoltes et productions animales aux lots, ventes, livraisons et traçabilité de sortie, après décision du modèle de lots.
4. **Économie agricole intégrée** : relier charges et produits issus des achats, stocks et ventes aux activités, avec analytique/comptabilité selon les décisions de cadrage. Calculer les coûts et marges végétaux et animaux seulement après disponibilité des données sources.
5. **Tableaux de bord et indicateurs** : construire des indicateurs après stabilisation des définitions, des données transactionnelles et des règles de calcul.
6. **Personnel/RH et matériel/maintenance** : décider d’abord si les référentiels maison se synchronisent avec `hr.employee` et `maintenance.equipment`, puis réaliser l’intégration souhaitée.

Cet ordre suit les dépendances de données : approvisionner et tracer les intrants/productions avant d’en déduire des coûts comparables ; consolider ensuite ventes et comptabilité ; présenter enfin des indicateurs fiables.

## 12. Proposition détaillée du Prompt 66

### Domaine proposé

**Approvisionnements et intrants agricoles reliés aux achats et au stock Odoo.**

### Justification

Le cahier des charges couvre les intrants, la gestion des stocks et la traçabilité des lots ; il annonce que les coûts doivent provenir des données réelles. Le code possède des catégories/types agricoles et des interventions, mais ne relie pas de produits, commandes d’achat, réceptions ou mouvements de stock aux activités. Les dépendances `product`, `purchase`, `stock` et `stock_account` sont déjà déclarées sans usage transactionnel observé. Ce domaine comble un prérequis direct aux coûts par campagne, parcelle et cycle.

### Objectifs fonctionnels

- Identifier les intrants agricoles au moyen des produits Odoo existants et de catégories agricoles.
- Suivre la demande d’approvisionnement jusqu’à l’achat et la réception Odoo.
- Localiser les stocks par société et emplacement, puis tracer les lots lorsque le flux standard le permet.
- Enregistrer la consommation d’intrants par exploitation, campagne, parcelle, cycle et intervention.
- Conserver quantité, unité, coût source et références aux documents Odoo sans créer un stock parallèle.
- Définir les cas de retour, annulation, correction et transfert avant validation.

### Modèles existants à réutiliser

`gest_agri.farm`, `gest_agri.site`, `gest_agri.plot`, `gest_agri.crop.campaign`, `gest_agri.crop.cycle`, `gest_agri.crop.intervention`, `gest_agri.fertilizer.type`, `gest_agri.operation.type`, `gest_agri.economic.expense` et les modèles natifs `product.product`, `purchase.order`/lignes, `stock.picking`, `stock.move`, `stock.lot` selon la disponibilité Odoo installée.

### Nouveaux modèles possibles

À décider pendant la conception, sans préjuger de l’implémentation :

- Un référentiel de liaison/type d’intrant si les catégories Odoo ne suffisent pas.
- Une demande ou plan d’approvisionnement agricole reliée à campagne/intervention.
- Un document de consommation agricole, relié aux mouvements de stock correspondants et aux axes d’imputation.

Éviter de répliquer les objets de commande, de livraison ou de stock déjà fournis par Odoo.

### Relations

Exploitation/société → demande d’approvisionnement → produit → commande d’achat → réception/mouvement de stock → lot/emplacement → consommation reliée à campagne, parcelle, cycle et intervention. Les coûts doivent provenir de la valorisation ou du document d’achat selon une règle métier décidée, et non d’une duplication manuelle non réconciliée.

### Vues et menus envisagés

Menu « Intrants » avec listes/formulaires de demandes et consommations, filtres par société/exploitation/campagne, liens intelligents vers commande et mouvement de stock, et vues de suivi des consommations. Ne pas concevoir de menus Odoo standards en doublon ; s’appuyer sur leurs formulaires natifs.

### Sécurité

Trois groupes existants à conserver. Filtrer chaque document agricole par sociétés actives et exploitations affectées/gérées ; contrôler également les mouvements et produits liés sans contourner les droits natifs par `sudo()`. Ajouter les accès des éventuelles lignes enfants et des tests négatifs d’accès croisé entre deux sociétés/exploitations.

### Intégrations Odoo nécessaires

`product`, `purchase`, `stock`, `stock_account` ; éventuellement `account` et `analytic` uniquement si l’imputation comptable/analytique est comprise dans le périmètre confirmé. Les versions et modules réellement installés doivent être vérifiés dans l’environnement de test.

### Contraintes métier à trancher

- Unité d’achat, unité de stockage et conversion.
- Lots obligatoires ou facultatifs selon type d’intrant.
- Politique de valorisation des consommations.
- Consommation négative, retour et annulation d’un mouvement déjà validé.
- Affectation multi-exploitation et transferts entre emplacements.
- Date de rattachement au cycle et à la campagne.
- Produits de traitement/fertilisants potentiellement soumis à traçabilité spécifique.
- Règles de multi-société et propriété des produits/référentiels partagés.

### Tests à prévoir

Installation/chargement du module et des données ; création d’une demande et liaison à l’achat ; réception partielle/complète ; entrée et sortie de stock avec lot ; consommation reliée à une intervention ; conversion d’unités ; annulation/retour ; cohérence campagne/parcelle/exploitation ; accès de chaque groupe et isolation entre sociétés ; absence de double écriture ; rapprochement des quantités et coûts sources.

### Dépendances et prérequis

Décider les points ouverts du cahier des charges sur gestion standard des stocks, traçabilité des lots et intégration comptable ; confirmer les modules Odoo installés ; définir les emplacements et règles de propriété des produits ; résoudre les anomalies P1 de sécurité ; fixer les règles de coût à transmettre au futur domaine économie.

**Décision proposée :** engager le Prompt 66 sur les approvisionnements et intrants agricoles connectés au stock/achats Odoo, après validation de ces prérequis. Aucun développement Prompt 66 n’a été commencé dans cet audit.

## 13. Rapports antérieurs repérés

L’inventaire du dossier contient `rapport_prompt_56_materiel.md`, `rapport_prompt_57_personnel.md`, `rapport_prompt_58_irrigation.md`, `rapport_prompt_59_economie.md`, `rapport_prompt_60_elevage_cheptel.md`, `rapport_prompt_61_alimentation.md`, `rapport_prompt_62_sante_animale.md`, `rapport_prompt_63_reproduction.md`, `rapport_prompt_64_production_animale.md`, `rapport_prompt_64_bis_audit.md` et `rapport_prompt_64_ter_cloture.md`. Le relevé confirme leur présence, mais ils n’ont pas tous été relus intégralement dans cette mission. La conclusion du rapport TER a été consultée pour identifier ses chiffres annoncés. Les états et nombres de ce rapport sont recalculés depuis les sources lorsque possible ; les déclarations de réussite de tests restent historiques faute de journaux d’exécution examinés ici.

## 14. Fichiers et répertoires examinés

Audit des contenus sous `models/` (79 fichiers), `views/` (17), `data/` (11), `security/` (2), `tests/` (22 fichiers dont `__init__.py`), `cahier_des_charges/` (10), ainsi que `__manifest__.py`, `__init__.py`, l’inventaire des rapports Prompt 56–64 (voir section 13) et les sources Odoo 20 `odoo/addons/base/models/ir_access.py`. Comparaison de parité de code des dossiers `models/`, `views/`, `tests/`, du manifeste et du fichier `security/ir.access.csv` entre le dossier de développement et le module installé.

## 15. Conclusion

Le projet a une couverture métier large pour les opérations agricoles de terrain et les domaines animaux. La profondeur fonctionnelle est inégale : les flux de production et de suivi sont modélisés, tandis que les transactions d’achat, de stock, de vente et de comptabilité annoncées ne sont pas intégrées dans le code examiné. L’économie reste une saisie de charges/recettes, insuffisante pour affirmer que les coûts et marges calculés répondent au cahier des charges.

La priorité proposée est **Approvisionnements et intrants agricoles reliés aux achats et au stock Odoo**. Elle fournit les données de consommation et de coût nécessaires à la prochaine phase économique, tout en avançant la traçabilité attendue. Les contrôles d’accès des lignes alimentation et les doublons d’accès sont des anomalies transversales à régler avant ou au début d’une phase d’implémentation.
