# Rapport Prompt 65 BIS — sécurisation transversale de `gestion_agricole`

Date : 12 novembre 2026  
Base autorisée : `odoo20`  
Périmètre : ACL, lignes de ration et de distribution, déduplication animal/lot et tests directement associés.

## 1. Résumé exécutif

Les deux modèles enfants de l’alimentation n’avaient pas d’ACL propres. Trois droits ont été ajoutés pour chacun selon les groupes existants. Les contrôles des modèles enfants empêchent l’accès direct non autorisé au parent, le rattachement à une société incompatible et la modification des lignes d’une distribution terminée. Six entrées ACL redondantes animal/lot ont été supprimées du CSV après vérification de leur identité exacte.

Les contrôles statiques sont passés. Des tests ciblés avaient précédemment réussi sur la base autorisée (30 tests `TestSecurity`, 37 tests `TestFeeding`, zéro échec/erreur selon les logs d’exécution disponibles). La relance finale demandée dans ce tour n’a pas démarré : PostgreSQL est actuellement injoignable sur les ports configurés. Décision : **VALIDÉ AVEC RÉSERVES**, en raison de cette impossibilité de répéter les tests après la synchronisation.

## 2. État initial des ACL

Le CSV initial contenait 200 lignes d’accès couvrant 66 modèles. Il ne contenait aucune ACL pour `gest_agri.feed.ration.line` et `gest_agri.feed.distribution.line`. Les groupes métier sont `group_gest_agri_user`, `group_gest_agri_manager` et `group_gest_agri_admin`, conformément à la hiérarchie existante.

La séparation d’accès est fondée sur `farm_id` pour les données liées à une exploitation et sur `company_id in company_ids` pour les données multi-sociétés. Les référentiels partagés existants n’ont pas été rendus obligatoirement liés à une société.

## 3. Analyse des doublons

Le CSV contenait deux copies textuellement identiques de chacune des trois ACL animal et des trois ACL lot : lecture utilisateur, création/modification responsable et CRUD administrateur. Elles étaient identiques par identifiant, modèle, groupe, opérations et domaine. Les répétitions sont donc redondantes, sans différence de droit à préserver.

L’inspection ORM antérieure sur `odoo20` avait trouvé un enregistrement chargé par identifiant d’accès, malgré les répétitions dans le CSV. Le CSV corrigé ne contient plus ces six lignes redondantes. Aucun autre doublon d’identifiant externe ou de tuple modèle/groupe/opérations/domaine n’est détecté statiquement.

## 4. Analyse des deux modèles enfants

`gest_agri.feed.ration.line` dépend de `gest_agri.feed.ration`. Son `company_id` est désormais un champ related stocké et readonly depuis la ration. Le champ parent et le lien vers l’aliment utilisent `check_company=True`; `_check_company_auto` est activé. Les créations et écritures contrôlent le droit d’écriture sur la ration et le droit de lecture sur l’aliment.

`gest_agri.feed.distribution.line` dépend de `gest_agri.feed.distribution`. Ses champs `farm_id` et `company_id` sont related stockés et readonly depuis la distribution. Le lien au parent et à l’aliment utilise `check_company=True`; `_check_company_auto` est activé. Création, écriture et suppression vérifient le droit sur le parent. Les lignes d’une distribution non brouillon sont verrouillées. Le modèle parent contrôle le droit sur l’exploitation et les enregistrements référencés, et revérifie la cohérence des relations lors des écritures.

Les règles ACL des lignes filtrent les utilisateurs sur leurs exploitations accessibles, les responsables sur leurs exploitations gérées, et les administrateurs sur leurs sociétés autorisées. Les vues ne sont pas utilisées comme mécanisme de sécurité.

## 5. Vérification de l’isolation par exploitation

Pour les lignes de ration, l’accès passe par la société de la ration. Pour les lignes de distribution, `farm_id` dérive de la distribution et les ACL filtrent cette exploitation. Les contrôles Python empêchent de changer directement le parent vers une exploitation non autorisée. Les scénarios de lecture inter-exploitation et de mutation du parent sont couverts par les tests ajoutés.

L’isolation animal/lot a été vérifiée par test direct et indirect dans la suite sécurité. Les modèles santé, reproduction et production ont été examinés pendant l’audit, mais n’ont pas été modifiés : le périmètre de correction Python autorisé par le Prompt 65 BIS se limite aux modèles enfants et à leurs contrôles ciblés.

## 6. Vérification de l’isolation par société

Les lignes de ration héritent de la société de leur ration; les lignes de distribution héritent de la société de leur distribution. `check_company=True` et `_check_company_auto` protègent les liens vers la société correspondante. Les ACL limitent les lignes à `company_ids` ou au domaine d’exploitation selon le modèle. Des scénarios de société incompatible sont présents dans les tests.

Les tests déjà exécutés couvrent aussi l’isolation animal/lot entre sociétés. Les référentiels partagés et les règles multi-sociétés globales d’Odoo restent inchangés.

## 7. Corrections Python éventuelles

Fichiers Python modifiés dans le périmètre autorisé :

- `models/feeding/ration.py` : société dérivée, cohérence multi-société, vérification d’accès au parent et à l’aliment.
- `models/feeding/distribution.py` : cohérence des références et de l’exploitation, accès aux références, droits du parent et verrouillage des lignes hors brouillon.
- `tests/test_security.py` : scénarios ciblés des lignes, de l’isolation et des permissions animal/lot.

Aucun modèle santé, reproduction ou production n’est modifié dans la version synchronisée.

## 8. Corrections XML/CSV

Seul `security/ir.access.csv` a changé; aucun XML ni fichier de règles `security.xml` n’a nécessité de modification. Six lignes animal/lot dupliquées ont été retirées. Six ACL ont été ajoutées : trois par modèle enfant, avec droits progressifs pour utilisateur, responsable et administrateur.

Contrôle statique final : 200 lignes CSV, 66 modèles, zéro identifiant externe dupliqué, zéro clé ACL dupliquée, trois ACL pour chaque modèle enfant.

## 9. Tests ajoutés

Les nouveaux tests couvrent les permissions par rôle, lecture dans l’exploitation autorisée, refus de lecture et d’écriture croisée, création et modification des lignes, refus de déplacer une ligne vers une autre distribution, accès animal/lot par exploitation et société, incompatibilité de société et verrouillage d’une distribution terminée.

## 10. Commandes exécutées

La relance ciblée a été tentée avec l’interpréteur et la configuration indiqués par le Prompt :

`/etc/odoo20-venv/bin/python /mnt/srv/share/odoo20/odoo/odoo-bin --addons-path=/tmp/opencode/dev,/mnt/srv/share/odoo20/odoo/addons,/mnt/srv/share/odoo20/addons/kantmoh --config=/etc/odoo20.conf -d odoo20 --http-port=0 --gevent-port=0 --stop-after-init -u gestion_agricole --test-enable --test-tags /gestion_agricole:TestSecurity,/gestion_agricole:TestFeeding`

Résultat de cette tentative : échec avant démarrage du serveur Odoo, `psycopg2.OperationalError`. `pg_isready` ne reçoit aucune réponse de `127.0.0.1:5433` (port de la configuration) ni de `127.0.0.1:5432`. Aucun service n’a été redémarré et aucune configuration système n’a été modifiée.

Les contrôles statiques ont analysé les 105 fichiers Python (AST valide) et les 29 XML (parse XML valide). Le CSV a été relu et contrôlé par script Python.

## 11. Résultats réels des tests

Les logs d’exécution précédemment obtenus sur `odoo20` indiquaient : `TestSecurity` : 30 tests, zéro échec et zéro erreur; `TestFeeding` : 37 tests, zéro échec et zéro erreur. Ils précèdent la relance finale de ce rapport. La relance finale n’a fourni aucun résultat de test : la connexion PostgreSQL a échoué avant le chargement du module. Aucun résultat n’est déduit de cette tentative.

## 12. Vérification des régressions

La suite ciblée `TestFeeding` avait passé sans échec lors de l’exécution antérieure. La suite sécurité ciblée avait également passé. Aucun résultat actuel ne permet de revendiquer une nouvelle exécution de régression après synchronisation; la limitation est consignée ci-dessus.

## 13. État de synchronisation

Les seuls fichiers synchronisés vers l’installation sont :

- `security/ir.access.csv`
- `models/feeding/ration.py`
- `models/feeding/distribution.py`
- `tests/test_security.py`

Chaque fichier a été comparé avec `cmp` entre développement et installation; les quatre comparaisons ont réussi. Aucun autre module n’a été modifié.

## 14. Anomalies restantes

- Les tests doivent être relancés sur `odoo20` dès que le point PostgreSQL prévu par `/etc/odoo20.conf` est disponible.
- L’inventaire transversal des relations santé, reproduction et production n’a pas donné lieu à des corrections hors du périmètre autorisé. Aucune absence de vulnérabilité sur ces modèles n’est revendiquée par ce rapport.
- Les modifications synchronisées n’ont pas pu être rechargées par une mise à jour de module pendant la dernière tentative, car la base était inaccessible.

## 15. Décision de validation

**VALIDÉ AVEC RÉSERVES.** Les corrections ACL et Python autorisées sont enregistrées, statiquement validées et synchronisées. Les tests ciblés ont réussi lors d’une exécution antérieure documentée, mais leur répétition finale et le rechargement final du module restent conditionnés au rétablissement de la connexion à la base `odoo20`. Aucun service ou autre base n’a été touché.
