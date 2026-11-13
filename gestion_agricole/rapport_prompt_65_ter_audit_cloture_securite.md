# Prompt 65 TER — audit de clôture et validation de la sécurité

**Module :** `gestion_agricole` — Odoo 20 Community  
**Date :** 12 novembre 2026  
**Base autorisée :** `odoo20` (aucune connexion applicative tentée dans cet audit)  
**Conclusion :** **NON VALIDÉ**

## 1. Résumé exécutif

L’identité des quatre fichiers annoncés entre développement et installation est confirmée par `cmp`. Les contrôles statiques confirment 200 entrées ACL, 66 modèles, 200 identifiants uniques, aucun doublon exact et aucun doublon du tuple modèle/groupe/opérations/domaine.

La clôture ne peut pas être validée. Trois défauts de sécurité importants sont prouvés statiquement :

1. Les ACL des lignes de ration ne filtrent que par société. Le modèle ration n’a pas de champ exploitation; un utilisateur agricole peut lire toutes les lignes de ration de sa société. Le scénario R1/A1 contre R2/A2 n’est pas représentable dans le schéma actuel, ce qui ne répond pas à l’exigence d’isolation.
2. Les domaines ACL d’écriture sont vérifiés sur l’enregistrement avant mutation. Les modèles animal et lot ne vérifient pas le droit sur l’exploitation cible dans leur write(); un responsable peut déplacer un enregistrement vers une autre exploitation de la même société.
3. Les méthodes write() d’animal et lot font confiance à des drapeaux de contexte contrôlables pour les transitions d’état et ne rappellent pas _check_allowed(). Un responsable peut contourner les transitions métier, par exemple réactiver un animal vendu/mort/retiré ou un lot clôturé.

Le workflow distribution a un défaut fonctionnel distinct : action_cancel() annonce autoriser done → cancelled, mais le verrou terminal de write() refuse le changement d’état avant d’examiner le contexte. L’annulation depuis done échoue.

Un autre défaut transversal apparaît dans le test `test_manager_cannot_reassign_health_record_to_unmanaged_animal` : le dossier de santé ne vérifie pas l’accès au nouvel animal pendant `write()`. Le code santé n’est pas corrigé dans le périmètre du Prompt 65 TER. Le contexte de travail précédent rapporte l’échec réel d’un essai isolé de ce scénario (« AccessError not raised »); aucun log brut n’est disponible ici pour le rejouer.

Aucune mise à jour de module ni aucun test nécessitant PostgreSQL n’a été exécuté. PostgreSQL est injoignable sur le port configuré. Les constats ci-dessus reposent sur le code source et le fonctionnement du moteur Odoo 20 local, pas sur une nouvelle exécution fonctionnelle.

## 2. Périmètre réellement audité

Lecture seule des quatre fichiers demandés dans les copies développement et installation :

- `security/ir.access.csv`
- `models/feeding/ration.py`
- `models/feeding/distribution.py`
- `tests/test_security.py`

Inspection de contexte limitée à `security/security.xml`, `models/livestock/animal.py`, `models/livestock/animal_lot.py`, `models/health/health_record.py`, `tests/test_feeding.py` et au moteur d’accès Odoo 20 local (`odoo/addons/base/models/ir_access.py`, `odoo/orm/models.py`, `odoo/orm/fields_relational.py`). Aucun autre module n’a été modifié. Aucun accès à une base n’a été effectué.

## 3. Méthodologie et limites

- Comparaison binaire des quatre fichiers dev/installation avec `cmp`.
- Diff Git dans le module installé pour identifier les quatre fichiers source modifiés.
- Analyse des lignes et méthodes Python, des domaines ACL et de la hiérarchie des groupes.
- Analyse du code Odoo 20 pour la composition des domaines d’accès, la recherche, `check_access()`, `create()`, `write()` et les relations One2many.
- Comptage statique par `csv.DictReader` et AST Python. Pas de `py_compile`, qui écrirait des fichiers bytecode.
- Diagnostic passif unique du port PostgreSQL configuré avec `pg_isready`.

Les constats de vulnérabilité sont des conclusions statiques du flux ORM. Aucun test de ce tour n’a exécuté le code sur une base.

## 4. Vérification des quatre fichiers synchronisés

Les quatre `cmp` ont retourné le code 0 : versions identiques entre `/tmp/opencode/dev/gestion_agricole/` et `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/`.

| Fichier | Identique dev/installation | Différence annoncée par le diff Git installé |
|---|---:|---|
| `security/ir.access.csv` | Oui | 6 lignes redondantes animal/lot retirées, 6 ACL lignes d’alimentation ajoutées; solde 0 ligne |
| `models/feeding/ration.py` | Oui | société dérivée, `check_company`, contrôles parent/aliment; +29/-2 lignes dans le diff |
| `models/feeding/distribution.py` | Oui | contrôles relationnels et d’accès, ACL indirectes et verrouillage des lignes; +90/-5 lignes dans le diff |
| `tests/test_security.py` | Oui | fixture et 8 méthodes de test ajoutées; +252/-1 lignes dans le diff |

Le diff Git du module installé signale exactement ces quatre fichiers suivis modifiés. Il y a aussi deux rapports Markdown non suivis dans le répertoire installé (`rapport_prompt_65_audit_transversal.md` et `rapport_prompt_65_bis_securite.md`); ils ne sont pas des modifications Python/XML/CSV du module. La copie `/tmp/opencode/dev/gestion_agricole` n’est pas un dépôt Git, donc son historique de modifications ne peut pas être reconstruit par `git status`.

## 5. Audit détaillé des six ACL ajoutées

| ID externe | Modèle | Groupe | Lire | Écrire | Créer | Supprimer | Domaine |
|---|---|---|---:|---:|---:|---:|---|
| `gest_agri_feed_ration_line_user_read` | `gest_agri.feed.ration.line` | `group_gest_agri_user` | Oui | Non | Non | Non | `[('company_id', 'in', company_ids)]` |
| `gest_agri_feed_ration_line_manager_create_update` | `gest_agri.feed.ration.line` | `group_gest_agri_manager` | Non dans cette ligne | Oui | Oui | Non | `[('company_id', 'in', company_ids)]` |
| `gest_agri_feed_ration_line_admin_crud` | `gest_agri.feed.ration.line` | `group_gest_agri_admin` | Oui | Oui | Oui | Oui | `[('company_id', 'in', company_ids)]` |
| `gest_agri_feed_distribution_line_user_read` | `gest_agri.feed.distribution.line` | `group_gest_agri_user` | Oui | Non | Non | Non | `[('farm_id', 'in', user.gest_agri_farm_ids.ids)]` |
| `gest_agri_feed_distribution_line_manager_create_update` | `gest_agri.feed.distribution.line` | `group_gest_agri_manager` | Non dans cette ligne | Oui | Oui | Non | `[('farm_id', 'in', user.gest_agri_managed_farm_ids.ids)]` |
| `gest_agri_feed_distribution_line_admin_crud` | `gest_agri.feed.distribution.line` | `group_gest_agri_admin` | Oui | Oui | Oui | Oui | `[('company_id', 'in', company_ids)]` |

Le moteur Odoo 20 local confirme que `ir.access` est le modèle d’accès à domaines. `Model._access_domain()` (`odoo/orm/models.py`, lignes 3603–3647) collecte les accès des groupes de l’utilisateur : domaines des permissions avec un OU, restrictions globales avec un ET. `ir.access._eval_context()` expose `company_ids` à partir des sociétés activées (`ir_access.py`, environ ligne 270). Le contrôle s’applique aux recherches, aux lectures directes et aux opérations ORM (`Model.check_access()`, environ lignes 3443–3461; domaine injecté dans `_search()`, environ lignes 4888–4890). Les accès One2many vérifient également l’accès au comodel (`fields_relational.py`, environ ligne 1592).

Les droits des groupes sont cumulatifs : dans `security/security.xml`, admin implique manager, qui implique user. Les domaines identiques de ration line s’unissent sans restriction supplémentaire. Un responsable obtient lecture via le groupe user et création/modification via manager; un admin reçoit les quatre opérations via admin.

## 6. Audit des domaines et des doublons

Les domaines distribution line sont bien liés à l’exploitation pour utilisateur et responsable. Le domaine admin est lié aux sociétés activées, ce qui constitue un accès société complète pour l’administrateur agricole. Les domaines ration line, en revanche, ne comportent que `company_id`; c’est insuffisant pour l’isolation demandée entre fermes d’une même société.

Résultats de comptage sur le CSV installé :

- 200 lignes de données (201 lignes physiques avec l’en-tête).
- 66 valeurs `model_id` distinctes.
- 200 identifiants externes uniques.
- 0 ligne entièrement répétée.
- 0 répétition du tuple modèle/groupe/opération/domaine.
- Les six droits animal/lot gardent chacun un droit utilisateur, responsable et admin. Les six copies redondantes ne subsistent plus.
- Chaque modèle enfant alimentation possède exactement trois ACL.

Le nombre reste à 200 car les six lignes redondantes supprimées ont été remplacées par six ACL, et le nombre de modèles passe de 64 à 66 en ajoutant les deux modèles enfants. L’ancienne inspection ORM des enregistrements chargés n’est pas reproductible sans PostgreSQL dans cette mission; aucune assertion sur l’état actuel en base n’est faite.

## 7. Analyse prioritaire : lignes de ration et fermes d’une même société

**Résultat : vulnérabilité de confidentialité confirmée par le domaine; isolation par exploitation non démontrée et impossible à exprimer avec le schéma actuel.**

La ligne 130 de `security/ir.access.csv` autorise la lecture à tout utilisateur agricole lorsque `company_id` appartient à `company_ids`. Les lignes 131–132 font de même pour les opérations manager/admin. Dans `models/feeding/ration.py`, le parent `gest_agri.feed.ration` possède `company_id` mais aucun champ `farm_id` (lignes 7–18); le child dérive son `company_id` de la ration (lignes 61–68), sans exploitation.

Ainsi, un utilisateur U autorisé à A1 et actif dans Société A satisfait le domaine pour toutes les lignes dont la société est A, quelle que soit l’exploitation à laquelle le métier associerait conceptuellement la ration. Il peut les obtenir via `env['gest_agri.feed.ration.line'].search(...)`, puis les lire par `browse(id).read(...)`; la lecture de `line_ids` applique le domaine du modèle enfant, qui est le même domaine société. La lecture directe du parent ration est également autorisée par son ACL société (CSV lignes 127–129). Les contrôles de `create()`/`write()` des lignes ne protègent pas la lecture et vérifient eux-mêmes les droits parent par société.

Nuance de schéma : R1 « appartenant à A1 » et R2 « appartenant à A2 » ne sont pas des enregistrements distinguables actuellement, car le modèle ration ne porte pas cette affectation. Deux rations de la même société restent toutefois toutes deux lisibles par U. L’exigence explicite de ne pas autoriser l’accès sur la seule société n’est donc pas satisfaite.

**Anomalie P1** — `security/ir.access.csv:130–132`, `models/feeding/ration.py:7–18, 55–68`. Conséquence : divulgation des lignes/compositions de ration d’autres fermes de la même société. Correction recommandée, à instruire dans une mission de correction distincte : définir si une ration est partagée par société ou attribuée à une exploitation; si l’isolation par ferme est requise, ajouter une relation métier exploitable (ferme sur ration ou relation d’affectation) puis bâtir et tester le domaine enfant sur cette relation. Un domaine d’action/vue ou le seul contrôle parent à la création ne suffit pas.

## 8. Analyse de l’isolation des lignes de distribution

**Résultat : isolation par ferme démontrée statiquement pour la sélection et les écritures usuelles du parent; non testée fonctionnellement dans ce tour.**

Le parent `gest_agri.feed.distribution` possède `farm_id` obligatoire et `company_id` related à la ferme (distribution.py:19–25). La ligne dérive les deux champs du parent (lignes 190–200). Les ACL utilisateur/responsable utilisent leurs fermes accessibles/gérées (CSV:136–137); le contrôle de création vérifie l’accès `write` au parent et l’état brouillon (distribution.py:210–218). Une écriture de `distribution_id` vérifie l’accès au nouveau parent et l’état avant écriture (220–232). Les ACL Odoo 20 s’appliquent également à `search()` et `read()` directs. Les tests présents couvrent `search()` et `browse().read()` sur deux fermes de même société, ainsi que le refus de changement de parent par un responsable (test_security.py:676–709).

Réserve admin : le domaine admin est société (`CSV:138`), donc un admin agricole ayant cette société active peut accéder aux lignes de toutes ses fermes. C’est un choix de privilège société, pas une isolation par ferme pour ce groupe.

## 9. Audit des contrôles Python et relations

### Lignes de ration

`create()` itère correctement sur `vals_list`, vérifie le droit d’écriture du parent et la lecture de l’aliment; `super().create()` applique ensuite le droit create et son domaine. `write()` vérifie le parent cible (ou le parent courant) et l’aliment cible (ou actuel), puis délègue à l’ORM. Pas de `sudo()` ni de `with_user()` dans les fichiers audités. `_check_company_auto` et `check_company=True` protègent la cohérence société des liens, mais ne fournissent aucune isolation ferme. Le parent n’a aucune notion de ferme.

La ligne ne surcharge pas `unlink()`; la sécurité repose sur l’ACL child et les mécanismes ORM normaux. User ne peut pas supprimer; manager ne peut pas supprimer; admin peut supprimer dans les sociétés activées. Il n’y a pas de workflow de ration à verrouiller.

### Lignes/distributions

`create()` traite les valeurs multiples, valide le XOR animal/lot, les cohérences de ferme/site/espèce et les droits des références. `write()` calcule les références effectives et refait ces contrôles quand un champ relationnel protégé change. Les Many2one de distribution vers ferme/site/animal/lot/ration et ceux de la ligne vers distribution/aliment utilisent `check_company=True`; le parent et la ligne activent `_check_company_auto`. Les relations restent cependant soumises aux contrôles applicatifs indiqués, puisque `check_company` ne vérifie pas les droits d’exploitation.

La création et l’écriture des lignes vérifient le parent en écriture; création, écriture et suppression vérifient l’état parent brouillon. Les suppressions de ligne multiples passent par le recordset complet (`mapped('distribution_id')`) et refusent si l’un des parents n’est pas brouillon. La suppression du parent vérifie que tous les parents sont en brouillon avant `super().unlink()`; les lignes sont en cascade. Les distributions terminées ou annulées ne peuvent pas être supprimées par le chemin ORM normal.

Aucun `sudo()`/`with_user()` n’apparaît dans les deux modèles alimentation. `with_context()` sert de marqueur de transition dans le modèle distribution; son interaction avec le verrou terminal est analysée à la section 10.

### Contournement des transitions animal/lot

Les méthodes animal.write() et animal_lot.write() ne vérifient que la présence d’un drapeau de contexte (animal.py:99–104; animal_lot.py:82–87). Les méthodes action_*() appellent _check_allowed(), mais write() ne fait pas cette validation lorsque le contexte gest_agri_animal_state_transition ou gest_agri_animal_lot_state_transition est présent. Ces valeurs peuvent être fournies dans le contexte d’un appel ORM. Un responsable autorisé à écrire le record peut donc forger le contexte et demander une transition interdite par les actions, par exemple d’un animal vendu/mort/retiré vers actif ou d’un lot clôturé vers actif.

**Anomalie P1** — models/livestock/animal.py:99–104 et models/livestock/animal_lot.py:82–90. Conséquence : contournement des workflows métier et réactivation d’enregistrements terminaux. Correction recommandée : ne pas utiliser un drapeau de contexte client comme seule preuve d’autorisation; centraliser et valider chaque transition côté serveur, puis tester les transitions illégales forgées.

### Défaut de validation du domaine après mutation (animal et lot)

Odoo 20 vérifie `self.check_access('write')` au début du `write()` ORM (`odoo/orm/models.py:3849`). L’implémentation standard poursuit la mutation puis vérifie `_check_company_auto`; elle ne refait pas le domaine d’accès sur les nouvelles valeurs après la mutation. Les domaines ACL écriture de animal et lot sont basés sur `farm_id` (CSV:119,122). Le `write()` animal (animal.py:99–104) ne contrôle que l’état; le `write()` lot (animal_lot.py:82–87) ne contrôle que l’état. Leurs contraintes d’exploitation vérifient seulement cohérence site/lot, pas le droit de l’utilisateur sur la ferme cible.

Un responsable peut donc modifier un animal ou lot initialement dans une ferme gérée pour remplacer `farm_id` par une autre ferme non gérée de la même société, si les autres relations satisfont leurs contraintes. Le contrôle initial passe sur l’ancienne ferme; la contrainte société accepte les deux fermes de la même société; aucun contrôle post-écriture du domaine ne bloque le déplacement.

**Anomalie P1** — `security/ir.access.csv:119,122`, `models/livestock/animal.py:99–104`, `models/livestock/animal_lot.py:82–87`. Conséquence : intégrité inter-fermes contournable par écriture directe. Correction recommandée dans une mission dédiée : vérifier explicitement l’accès `write` à la ferme cible dans les méthodes `write()` et tester le déplacement par un responsable.

### Dossiers de santé : défaut connexe constaté

`test_security.py:822–831` contient un test qui tente de réaffecter un dossier sanitaire d’un animal d’une ferme gérée à un animal d’une ferme non gérée et attend `AccessError`. Or `models/health/health_record.py:16–18,65–70` définit la relation sans `check_company=True`, n’a pas de contrôle d’accès à l’animal cible dans `write()` et ne contrôle dans cette méthode que l’état. Les domaines ACL de santé sont calculés via le farm related de l’animal. Au regard du même fonctionnement ORM pré-écriture, la mutation vers l’animal d’une autre ferme peut passer.

Le contexte historique de la mission précédente indique que ce test ciblé avait effectivement échoué par absence d’`AccessError`, puis qu’un correctif temporaire avait été exploré. Le fichier santé installé est aujourd’hui sans ce correctif, et il n’est pas dans les quatre fichiers audités/synchronisés par 65 BIS. **Anomalie P1, hors correction autorisée dans cette mission.** Correction recommandée : contrôle d’accès à la cible dans `write()` et garde de cohérence au changement de `animal_id`; exécuter le test dédié dans une mission autorisant les modèles santé.

## 10. Verrouillage des distributions terminées

États définis : draft, done, cancelled (distribution.py:47–50). action_done() permet seulement draft → done; action_cancel() annonce permettre draft|done → cancelled (163–175). Une distribution done/cancelled ne peut pas modifier ses relations protégées; seuls notes et active sont permis. Le unlink() parent n’accepte que draft (127–137,177–180). Les lignes vérifient côté serveur que le parent est draft sur create/write/unlink (210–242). Les scénarios d’écriture et de suppression de ligne done sont présents dans test_security.py:727–733; le test de suppression parent done et les tests de workflow figurent dans test_feeding.py:220–245.

**Défaut fonctionnel P2** — distribution.py:132–137 et 167–169. action_cancel() autorise explicitement done → cancelled, puis _apply_state() appelle write({'state':'cancelled'}). Mais le garde du début de write() refuse toute écriture autre que notes/active dès que l’état courant est done/cancelled, avant le contrôle de contexte. Ainsi l’annulation d’une distribution done échoue. Le contexte gest_agri_feed_distribution_state_transition ne permet pas de sortir de cet état; aucun contournement du verrouillage des lignes par cette clé n’est démontré. Une transition directe draft→done ou draft→cancelled avec cette clé saute l’entrée par action, mais ces transitions sont déjà prévues par les actions et aucun effet additionnel contourné n’a été identifié.

Correction recommandée dans une mission autorisée : faire reconnaître la transition interne validée par le garde terminal tout en continuant à interdire les autres mutations, puis tester done → cancelled, le refus de toute réouverture, les lignes cancelled et les écritures directes avec contexte.

## 11. Audit des droits animal et lot

Les trois ACL par modèle sont présentes et non dupliquées. User a lecture sur les fermes accessibles; manager a create/update sur ses fermes gérées et hérite de la lecture utilisateur; admin a CRUD sur ses sociétés activées. L’union Odoo des accès de groupe ne crée pas de droit global supplémentaire pour user/manager dans les opérations farm-scoped; admin a délibérément un domaine company-wide.

Les tests présents contrôlent lecture/accès direct animal et lot entre fermes (test_security.py:760–777) et refus sur société non autorisée (779–820). Ils ne testent pas le déplacement `farm_id` par manager : voir le défaut P1 de la section 9. Aucune analyse exhaustive des relations One2many de tous les modèles animaux n’est revendiquée.

## 12. Réconciliation des comptages

| Élément | Nombre constaté | Méthode | Explication |
|---|---:|---|---|
| Lignes ACL | 200 données (201 physiques avec en-tête) | CSV | Six retraits compensés par six ajouts |
| Modèles couverts | 66 | Valeurs `model_id` distinctes | 64 annoncés au départ + les deux modèles enfants |
| Identifiants externes uniques | 200 | `Counter(id)` | Aucun doublon |
| Méthodes `test_` dans `test_security.py` | 31 | AST | 23 initiales + 8 méthodes ajoutées, dont un test santé hors périmètre strict alimentation |
| Méthodes `test_` dans `test_feeding.py` | 38 | AST | Correspond au chiffre Prompt 65 de méthodes présentes |
| Classes de tests | 1 + 1 | AST | `TestSecurity`, `TestFeeding` |
| Tests historiques déclarés exécutés | 30 + 37 | Rapport 65 BIS | Déclaration historique seulement |
| Tests avec logs bruts disponibles dans le périmètre | 0 | Recherche des artefacts/logs et fichiers disponibles | Les rapports précédents répètent les décomptes, sans livrer les logs d’exécution |

Les 31 et 38 sont des méthodes présentes aujourd’hui, pas des tests prouvés exécutés. Le chiffre de 30 dans le rapport 65 BIS ne correspond pas au nombre actuel de méthodes `test_` de `TestSecurity`; il précède vraisemblablement l’ajout du test santé final, mais les artefacts bruts ne permettent pas de dater exactement chaque exécution. Le chiffre de 37 pour `TestFeeding` ne peut pas être réconcilié avec 38 méthodes présentes à partir des éléments disponibles. Ne pas traiter les décomptes 30/37 comme validation de la version actuelle.

## 13. Analyse de couverture des tests présents

| Risque/scénario | Présent | Évaluation statique |
|---|---|---|
| Trois groupes métier | Oui, tests lignes ration/distribution | Partiel : user, manager, admin testés, mais pas chaque opération pour chaque rôle |
| Lecture ration directe/search en société | Oui, search utilisateur même société; read société étrangère refusé | Insuffisant : aucun refus entre deux fermes de la même société |
| `browse().read()` ration | Seulement sur autre société | Insuffisant pour frontière ferme intra-société |
| Relations parent/One2many ration | Non | Non couvert |
| Création ration line | Oui, user refusé, manager/admin autorisés | Pertinent |
| Modification ration line | Oui, user refusé, manager autorisé | Pertinent, mais aucun parent ferme non autorisé n’existe dans le schéma |
| Suppression ration line | Admin autorisé | Pas de refus explicite pour user/manager, bien que ACL le prévoie |
| Création/lecture distribution line | Oui, comparaison ferme A/B même société | Pertinent |
| Modification/suppression distribution line | Oui, changement de parent interdit; lock done testé | Partiel, pas de suppression par manager hors ferme en test séparé |
| Changements de parent/ferme | Distribution parent et ligne testés | Pertinent; aucun test farm move animal/lot |
| Société incompatible | Oui via aliment/ration et distribution | Pertinent pour `check_company`, pas pour ferme |
| Distribution done | Écriture et suppression de ligne refusées | Pertinent; annulation depuis done non testée et rejetée par le garde |
| Distribution cancelled | Pas de test du verrou de ligne ni de parent | Non couvert |
| Animal/lot read inter-ferme | Oui | Pertinent en lecture directe |
| Animal/lot read inter-société | Oui | Pertinent pour les utilisateurs multi-sociétés testés |
| Animal/lot write déplacement inter-ferme | Non | Lacune; défaut statique identifié |
| Réaffectation santé vers animal non géré | Test présent | Il attend un refus, mais le code actuel ne le vérifie pas; l’essai ciblé antérieur avait signalé l’absence d’exception |
| Transition par contexte forgé | Non | Lacune; contournement statique identifié |

## 14. État de PostgreSQL

Configuration lue sans modification : `db_host = 127.0.0.1`, `db_port = 5433`, utilisateur `odoo20`. Diagnostic passif exécuté :

`pg_isready -h 127.0.0.1 -p 5433`

Résultat exact : `127.0.0.1:5433 - pas de réponse`, code de sortie 2. Aucune tentative de connexion Odoo ou à une base, aucun redémarrage, aucune réparation et aucune modification de configuration n’ont été effectués. Toutes les vérifications nécessitant PostgreSQL ont été arrêtées.

## 15. Commandes de validation ultérieure préparées, non exécutées

Mise à jour à réserver à une mission ultérieure autorisée :

`/etc/odoo20-venv/bin/python /mnt/srv/share/odoo20/odoo/odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init -u gestion_agricole`

Tests ciblés à réserver à une mission ultérieure autorisée :

`/etc/odoo20-venv/bin/python /mnt/srv/share/odoo20/odoo/odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test`

Aucune de ces commandes n’a été exécutée dans le cadre de 65 TER.

## 16. Risques résiduels et anomalies classées

| Priorité | Fichier/méthode | Constat | Preuve/conséquence | Correction recommandée |
|---|---|---|---|---|
| P1 | `security/ir.access.csv:130–132`; `models/feeding/ration.py:7–18,55–68` | Ration line seulement limitée par société; ration sans ferme | Un user limité à A1 lit les lignes de la même société relatives à d’autres fermes; le modèle ne représente pas l’affectation A1/A2 | Modéliser l’affectation ferme puis filtrer les lignes par relation ferme, ou formaliser explicitement la portée société si l’exigence de confidentialité change |
| P1 | `models/livestock/animal.py:99–104`; `models/livestock/animal_lot.py:82–87` | Pas de contrôle de l’exploitation cible dans `write()` | Le domaine Odoo est vérifié avant mutation; un manager peut déplacer un enregistrement vers une ferme non gérée de la même société | Contrôle serveur explicite sur la cible et tests d’écriture inter-ferme |
| P1 | models/livestock/animal.py:99–104; models/livestock/animal_lot.py:82–90 | Drapeaux de transition animal/lot contrôlables par contexte | write() saute _check_allowed(); des états terminaux peuvent être réactivés | Valider les transitions côté serveur sans faire confiance au contexte RPC |
| P2 | models/feeding/distribution.py:132–137,167–169 | Annulation d’une distribution done refusée par le garde terminal | L’action annonce done → cancelled, puis write() rejette le changement d’état | Aligner le garde terminal sur les transitions autorisées et tester l’annulation |
| P1 hors périmètre correctif | `models/health/health_record.py:16–18,65–70`; `tests/test_security.py:822–831` | Réaffectation d’un dossier à un animal non géré non protégée | Test présent; code write ne contrôle que le statut; tentative ciblée précédente rapportée comme ayant échoué | Contrôle d’accès à la cible et garde de relation dans une mission autorisant les modèles santé |
| Réserve d’exécution | Base `odoo20` | PostgreSQL indisponible | Aucun rechargement ou test de la version actuelle possible | Après disponibilité de la base, lancer les commandes préparées et conserver les logs bruts |

Aucun de ces constats n’a été corrigé pendant cette mission en lecture seule.

## 17. Décision finale et conditions avant le prochain développement

# **NON VALIDÉ**

Cette conclusion est motivée par la fuite intra-société des lignes de ration, le déplacement inter-ferme possible par `write()` sur animal/lot et le contournement des transitions par contexte. Le défaut de réaffectation du dossier santé est également constaté hors du périmètre de correction autorisé. Les tests fonctionnels actuels ne peuvent pas être confirmés puisque PostgreSQL est inaccessible.

Avant de poursuivre le prochain développement fonctionnel :

1. Décider et implémenter le modèle d’affectation des rations aux exploitations, puis limiter les lignes et les accès directs à cette portée.
2. Ajouter une vérification de droit sur la ferme cible lors des écritures animal et lot.
3. Vérifier côté serveur les transitions d’état animal/lot au lieu de faire confiance aux drapeaux de contexte; tester les transitions hors workflow.
4. Rendre possible done → cancelled pour la distribution tout en gardant les lignes immuables en état done/cancelled; tester la transition et les écritures directes.
5. Autoriser une correction du modèle de santé et faire passer le test déjà présent de réaffectation inter-ferme.
6. Quand PostgreSQL est disponible, mettre à jour uniquement `gestion_agricole` sur `odoo20`, exécuter les tests ciblés, conserver les logs, puis vérifier les mêmes scénarios directs (`search`, `browse().read()`, relations parent/enfant) pour trois rôles et deux fermes d’une même société.
