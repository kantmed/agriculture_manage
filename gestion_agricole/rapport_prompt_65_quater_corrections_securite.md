# Prompt 65 QUATER — corrections ciblées des failles P1

**Module :** `gestion_agricole` — Odoo 20 Community  
**Date :** 12 novembre 2026  
**Conclusion :** correction ciblée de l’isolation par exploitation implémentée selon l’arbitrage Option A; sécurisation globale **NON VALIDÉE** tant que les tests Odoo ne peuvent pas être exécutés et que les anciennes rations ne sont pas affectées à une exploitation.

## 1. Résumé exécutif

Le code a été corrigé pour les déplacements inter-exploitations des animaux et lots, les transitions d’état animal/lot et la réaffectation des dossiers sanitaires. Les contrôles s’appliquent côté ORM, y compris aux écritures multiples et relations vers site/lot. Dix tests ciblés supplémentaires ont été écrits. Les quatre fichiers concernés ont été synchronisés et comparés entre développement et installation.

L’utilisateur a arbitré Option A : chaque ration est propre à une exploitation. Le modèle, les lignes, les ACL et les relations de distribution ont été adaptés à cette règle. Le champ ferme reste facultatif au niveau SQL pour rendre la mise à niveau compatible avec les anciennes données; les nouvelles créations l’exigent. Les enregistrements historiques sans ferme restent réservés aux administrateurs jusqu’à leur affectation.

PostgreSQL ne répond pas sur son port configuré (`127.0.0.1:5433`). Aucun test Odoo ni mise à jour de module n’a été lancé. La syntaxe Python a été contrôlée par AST; ce contrôle statique ne vaut pas exécution fonctionnelle.

## 2. Périmètre réellement modifié

Fichiers modifiés et synchronisés :

- `models/livestock/animal.py`, `models/livestock/animal_lot.py`, `models/health/health_record.py`
- `models/feeding/ration.py`, `models/feeding/distribution.py`
- `security/ir.access.csv`, `views/feeding_views.xml`
- `tests/test_security.py`, `tests/test_feeding.py`

Le défaut P2 d’annulation d’une distribution terminée reste hors de cette correction.

Le fichier de consignes joint à cette mission s’achève au milieu du scénario 6 de la section 5.3. Le présent compte rendu se limite aux demandes explicitement disponibles et à l’objectif clairement annoncé.

## 3. Analyse métier des rations

### 3.1 Éléments du cahier des charges

Les fichiers du cahier des charges établissent le multi-société, le multi-exploitation, la traçabilité et le principe général « les référentiels alimentent les opérations ». Ils ne mentionnent pas les rations, leur propriété, leur partage entre exploitations, ni la confidentialité de leur composition.

Le code montre une ration avec `company_id`, sans `farm_id`; une composition One2many; et une distribution par exploitation qui peut référencer une ration. Ces éléments évoquent une définition réutilisable par société, mais ne constituent pas une décision métier suffisante. Ils ne disent pas si les compositions sont confidentielles entre exploitations.

### 3.2 Comparaison des architectures

| Critère | Option A — ration propre à une exploitation | Option B — définition partagée, utilisation par exploitation |
|---|---|---|
| Partage entre exploitations | Aucun partage direct; duplications possibles | Une formule sert plusieurs exploitations |
| Isolation des données | Domaine simple sur `ration.farm_id`; lignes héritent de la ferme | La définition est visible selon une politique partagée; opérations et consommations doivent rester isolées |
| Simplicité des ACL | Simple pour ration et lignes | Plus complexe : distinguer lecture de la formule et accès aux usages par ferme |
| Relations avec les lots | La ration doit appartenir à la ferme des lots/distributions qui l’utilisent | Lot/distribution utilise une ration commune; la consommation reste rattachée à la ferme |
| Relations avec les distributions | Cohérence directe ration/distribution sur la ferme | La relation de distribution porte la ferme opérationnelle; la ration reste un référentiel transversal |
| Évolutivité | Adaptée aux recettes propres aux exploitations; peut dupliquer les formules | Adaptée aux références communes, mais nécessite une politique de visibilité et éventuellement un modèle d’affectation/usage |
| Compatibilité avec le cahier des charges | Non déterminable | L’indication générale « référentiels alimentent les opérations » est compatible, sans trancher la confidentialité |

### 3.3 Décision

L’utilisateur a choisi **Option A** : une ration appartient à une exploitation. Le code applique cette décision :

- Le champ `farm_id` identifie l’exploitation de la ration et sa société est synchronisée/contrôlée.
- Les lignes héritent de `farm_id`; les domaines utilisateur et responsable filtrent sur les exploitations accessibles/gérées. Les droits administrateur restent limités aux sociétés activées.
- Une distribution ne peut référencer une ration que si elle appartient à sa ferme.
- Les rations historiques non affectées restent lisibles/administrables par les administrateurs, mais invisibles aux utilisateurs et responsables; elles doivent être affectées avant de redevenir disponibles.

## 4. Correction des animaux

Dans `models/livestock/animal.py`, `write()` contrôle désormais, lors de toute modification de `farm_id`, `site_id` ou `lot_id`, les valeurs relationnelles effectives. La ferme cible doit accorder `write` à l’utilisateur. Site et lot doivent être lisibles par l’utilisateur et appartenir à la ferme effective; les contraintes existantes restent en place. `lot_id` utilise aussi `check_company=True`.

Le contrôle est exécuté pour chaque animal du recordset avant délégation à `super().write()`. Un changement vers une autre ferme de même société est refusé si l’utilisateur ne la gère pas; le domaine de la ferme cible prend aussi en compte les sociétés activées et les ACL du rôle. Un changement vers une ferme gérée reste autorisé si les relations site/lot restent cohérentes.

Les écritures d’état ne se fient plus à `gest_agri_animal_state_transition` fourni dans le contexte. Les actions métier valident la transition avec `_check_allowed()` puis passent par `_apply_state()`, qui appelle l’implémentation parent ORM sans revenir dans le garde public. Les vérifications ACL ORM restent appliquées par l’ORM.

## 5. Correction des lots

Dans `models/livestock/animal_lot.py`, l’écriture d’une ferme ou d’un site vérifie l’accès `write` à la ferme cible et l’accès `read` au site. Le site doit appartenir à la ferme cible. Un lot ayant des animaux membres ne peut pas être déplacé si leurs fermes effectives ne correspondent pas à la destination.

Les transitions ne font plus confiance à `gest_agri_animal_lot_state_transition` dans le contexte. Les actions gardent leur validation de transition et `_apply_state()` passe directement par l’ORM parent après validation.

## 6. Correction des dossiers sanitaires

Le modèle réel porte le nom `gest_agri.animal.health` (la consigne nomme `gest_agri.health.record`). Dans `models/health/health_record.py`, `animal_id` et `site_id` ont `check_company=True`. Les créations tiennent compte des valeurs fournies et des valeurs par défaut, puis vérifient le droit `write` sur l’animal cible et le droit `read` sur le site. Les écritures contrôlent les relations effectives de chaque dossier; un site incohérent avec la ferme de l’animal est refusé.

Cela protège la réaffectation vers un animal d’une exploitation non gérée aussi bien que la création directe d’un dossier sur cet animal. Les contrôles d’espèce, de site, de dates et de workflow existants sont conservés.

## 7. Tests ajoutés

Dix tests ciblés relatifs aux corrections animales/sanitaires et un scénario d’isolation inter-fermes des rations/lignes sont présents dans `tests/test_security.py`. Un scénario de cohérence ferme-ration est ajouté à `tests/test_feeding.py` :

- modification autorisée d’un animal et déplacement vers une ferme gérée;
- refus d’un déplacement animal vers une ferme non gérée de même société;
- refus d’un déplacement groupé vers une ferme non gérée;
- refus vers une société non autorisée;
- refus d’un déplacement de lot vers une ferme non gérée;
- déplacement autorisé d’un lot vide vers une ferme gérée;
- refus de déplacer un lot en laissant ses animaux dans l’ancienne ferme;
- refus d’une transition d’état animal par contexte forgé;
- refus d’une transition d’état lot par contexte forgé;
- refus de créer un dossier sanitaire pour un animal non géré;
- refus d’accès utilisateur à une ration et une ligne d’une autre ferme de la même société, et refus d’écriture responsable hors ferme;
- refus d’utiliser dans une distribution une ration d’une autre ferme.

Le test déjà présent de réaffectation d’un dossier sanitaire vers l’animal non géré est conservé et doit maintenant recevoir `AccessError`.

Les scénarios d’écriture autorisée sont exécutés sous le rôle responsable, car l’ACL actuelle du groupe utilisateur agricole est en lecture seule. Le comptage statique actuel donne 41 méthodes `test_` dans `TestSecurity` et 39 dans `TestFeeding`. Ces nombres décrivent les méthodes définies, pas les tests exécutés.

## 8. Validation technique et limites d’exécution

Les fichiers Python modifiés ont été analysés avec l’AST Python sans erreur; le XML a été analysé et le CSV des ACL a été contrôlé syntaxiquement. Les neuf fichiers source/test concernés ont été comparés par `cmp`; ils sont identiques entre développement et installation.

Diagnostic passif effectué : `pg_isready -h 127.0.0.1 -p 5433` a retourné `127.0.0.1:5433 - pas de réponse`, code 2. Aucune tentative de connexion applicative, aucun test Odoo, aucune mise à jour de module et aucun accès à une autre base n’ont eu lieu.

Les tests écrits ne sont donc **pas exécutés**. Aucun résultat de test n’est déclaré réussi. Les opérations de déplacement, les transitions légales par action métier et le comportement des règles ORM doivent être confirmés quand PostgreSQL est disponible.

## 9. Synchronisation

Les quatre fichiers mentionnés à la section 2 ont été copiés individuellement de la copie dev vers l’installation. `cmp` confirme leur identité. Aucun autre fichier source n’a été synchronisé pendant cette mission.

## 10. Anomalies restantes

| Priorité | Anomalie | État | Suite nécessaire |
|---|---|---|---|
| P1 | Ration et lignes accessibles à l’échelle de la société plutôt que de l’exploitation | Correction statique selon Option A; exécution non vérifiée | Exécuter les tests; affecter les anciennes rations sans ferme |
| P1 | Accès d’écriture à la ferme cible lors des changements animal/lot | Correctif statique ajouté, non testé sur Odoo | Exécuter tests de rôle, ferme de même société, autre société et recordsets multiples |
| P1 | Drapeaux de contexte pour états animal/lot | Remplacés par passage interne après `_check_allowed()` | Tester actions légales et écritures directes forgées |
| P1 | Réaffectation des dossiers santé | Contrôle d’accès cible ajouté | Tester create/write inter-ferme et accès site |
| P2 | Annulation d’une distribution `done` | Non modifiée, hors périmètre P1 annoncé | Traiter dans la mission séparée prévue |
| Validation | PostgreSQL inaccessible | Tests et mise à jour non exécutés | Attendre le retour du service; ne pas contourner cette indisponibilité |

## 11. Décision

**NON VALIDÉ pour la clôture globale.** L’arbitrage Option A est appliqué au code et les corrections sont synchronisées. Aucun test Odoo n’a été exécuté, car PostgreSQL ne répond pas sur `127.0.0.1:5433`. Les données historiques de ration doivent être affectées explicitement à une exploitation par un administrateur avant accès courant.

Suite requise : restaurer la disponibilité de PostgreSQL selon l’exploitation normale, lancer les tests ciblés sur `odoo20`, conserver les résultats réels, puis affecter les rations historiques sans `farm_id`.
