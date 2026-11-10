# RAPPORT D'AUDIT FINAL PROMPT N°5 — MODULE GESTION_AGRICOLE

*Audit strictement en lecture seule. Aucune modification de fichier, base de données ou serveur n'a été effectuée.*

---

## A. VERDICT GÉNÉRAL

**NON VALIDÉ — CORRECTIONS NÉCESSAIRES**

Le module présente des anomalies significatives qui l'empêchent d'être considéré comme installable ou pleinement sécurisé sans modifications supplémentaires. Bien que certaines corrections techniques aient été apportées, elles ne résolvent pas tous les défauts identifiés et certains mécanismes de sécurité restent incomplets ou potentiellement vulnérables.

**Raison principale :** L'ordre de chargement XML et la résolution des External IDs, bien que corrigés en surface, masquent des problématiques plus profondes dans la structure des références et la cohérence des dépendances entre fichiers. De plus, les mécanismes de sécurité (contrôles farm_id, invariant parcelle/secteur, isolation multi-société) présentent des lacunes qui ne garantissent pas une protection complète dans des scénarios réels.

---

## B. TABLEAU DES ANOMALIES

| # | Gravité | Fichier | Lignes | Comportement Observé | Risque Réel | Justification Technique | Correction Recommandée |
|---|---------|---------|--------|---------------------|-------------|------------------------|----------------------|
| A1 | P0 | `__manifest__.py` | Ligne 52-62 | Ordre `data` : `patrimony_views.xml` et `irrigation_views.xml` avant `farm_views.xml` | FAIBLE (déjà corrigé) | L'ordre a été réorganisé lors du Prompt N°4 ter. Vérification confirmée : les fichiers dépendants chargent avant ceux qui les utilisent. | Conserver l'ordre actuel. |
| A2 | P0 | `views/farm_views.xml` | Ligne 5, 75, 213 | Action `action_gest_agri_farm_access` déplacée en tête du fichier | FAIBLE (déjà corrigé) | L'enregistrement a été déplacé juste après le commentaire `<!-- Exploitations agricoles -->`. Tous les boutons `%(... )d` référencent maintenant une action existante. | Conserver la position actuelle. |
| A3 | P0 | `views/farm_views.xml` | Ligne 23+ | Structure XML validée mais dépendances inter-fichiers non vérifiées | MOYEN | Le XML est syntaxiquement valide, mais la résolution des External IDs dépend du chargement préalable de `patrimony_views.xml` et `irrigation_views.xml`. L'ordre dans le manifeste est correct, mais tout défaut dans ces fichiers bloquerait toujours l'installation. | Vérifier l'intégrité de `patrimony_views.xml` et `irrigation_views.xml`. |
| A4 | P1 | `models/patrimony/farm.py` | Méthode `write()` | Vérification farm_id et company_id avant modification | MOYEN | La méthode bloque le changement de farm_id pour les non-administrateurs. Cependant, le contrôle repose sur `has_group()` qui peut être contourné via `sudo()` ou des règles d'accès mal configurées. | Ajouter une vérification supplémentaire au niveau SQL/contrainte. |
| A5 | P1 | `models/patrimony/farm.py` | `_compute_allocated_area()` | Compte seulement les parcelles actives | FAIBLE | Le compute est correct : `farm.plot_ids.filtered('active')`. Cependant, si une parcelle est rendue active par un utilisateur non autorisé, le compute inclura immédiatement la nouvelle surface. | Vérifier que l'activation de parcelle fait l'objet d'un contrôle d'accès. |
| A6 | P1 | `models/patrimony/farm_access.py` | `_check_self_management()` | Bloque modification propres droits si user_company ∉ access_companies | MOYEN | La vérification compare `env.company` aux sociétés des accès. Mais `env.company` peut ne pas refléter la société contextuelle correcte dans tous les scénarios (multi-société, contexte explicite). | Tester avec contexte `company_id` explicite. |
| A7 | P1 | `models/patrimony/farm_access.py` | `write()` avec `farm_id` dans vals | Bloque le changement de farm_id pour non-administrateurs | MOYEN | Identique au problème farm.py : dépendance au groupe. Pas de protection contre `sudo()`. | Ajouter une contrainte SQL `CHECK` ou `ON DELETE RESTRICT`. |
| A8 | P1 | `models/patrimony/irrigation_sector.py` | `_check_plot_farm()` | Double sens : secteurs→parcelles ET parcelles→secteurs | MOYEN | La contrainte vérifie les deux sens. Cependant, si une parcelle est d'abord associée à un secteur, puis que la ferme de la parcelle change, la contrainte ne s'applique qu'à la prochaine modification. | Ajouter un `@api.onchange` pour feedback immédiat. |
| A9 | P1 | `models/patrimony/plot.py` | `write()` avec `farm_id` | Bloque changement de farm_id pour non-administrateurs | MOYEN | Même problème que farm.py/farm_access.py : pas de protection `sudo()`. De plus, la méthode ne vérifie pas si le nouvel farm_id est dans les sociétés autorisées de l'utilisateur. | Vérifier les sociétés autorisées via `res.users.gest_agri_managed_farm_ids`. |
| A10 | P1 | 13 modèles `models/configuration/*.py` | Contraintes `@api.constrains` | Bloquent `company_id=False` pour non-administrateurs | MOYEN | Les contraintes existent mais, comme pour tous les `@api.constrains`, elles ne s'exécutent qu'après la modification. Création ou modification en utilisant `sudo()` contourne les contraintes Python. | Utiliser des index UNIQUE avec filtres au niveau SQL. |
| A11 | P1 | `models/patrimony/plot.py` + `irrigation_sector.py` | Unicité des codes | Non vérifiée explicitement | ÉLEVÉ | Les mécanismes d'unicité reposent sur `check_unique_reference()` avec `global_scope`. Or, comme analysé à la section G, ce mécanisme ne garantit pas l'unicité dans les scénarios de concurrence (deux transactions peuvent créer le même code avant que l'une ne lève l'erreur). | Mettre en place des `UniqueIndex` DB avec `WHERE company_id IS NULL` et `WHERE company_id IS NOT NULL`. |
| A12 | P2 | `models/patrimony/farm.py` | `_invalidate_farm_access_cache()` | Invalidation ciblée mais globale `invalidate_all()` dans farm_access.py | FAIBLE | La méthode `invalidate_all()` dans farm_access.py invalide tous les caches, ce qui peut causer des performances réduites. La méthode de farm.py est plus ciblée. | Uniformiser sur une invalidation plus fine. |
| A13 | P2 | Modèles de test | `test_security.py`, `test_patrimony.py` | Couverture partielle des scénarios | MOYEN | Les tests existent et couvrent les cas de base, mais manquent de scénarios de concurrence, de multi-société étendu et de contournement via `sudo()`. | Ajouter des tests de concurrence et de sudo(). |
| A14 | P3 | `models/patrimony/farm.py` | `_invalidate_farm_access_cache()` | `invalidate_access_cache()` + `invalidate_ormcache("stable")` + `invalidate_ormcache("default")` | FAIBLE | La stratégie est correcte mais insuffisante : elle n'invalide pas le cache `irreversible` ni ne cible spécifiquement les caches liés aux droits d'accès par utilisateur. | Cibler `invalidate_records()` sur les enregistrements modifiés. |

---

## C. VÉRIFICATION DES CORRECTIONS PROMPT 4 TER

| Identifiant | Correction Annoncée | Statut | Justification |
|-------------|---------------------|--------|---------------|
| B1-1 | Ordre manifeste : `patrimony_views.xml` et `irrigation_views.xml` avant `farm_views.xml` | **Confirmée** | Vérification dans `__manifest__.py` lignes 52-62 : l'ordre est correct. |
| B1-2 | Action `action_gest_agri_farm_access` déplacée en tête de `farm_views.xml` | **Confirmée** | Vérification : l'enregistrement est à la ligne 5, juste après le commentaire. Tous les boutons `%(... )d` résolvent correctement. |
| B2-1 | `write()` farm.py vérifie farm_id et company_id | **Confirmée** | La méthode vérifie `has_group("gestion_agricole.group_gest_agri_admin")` before allowing farm_id change. |
| B2-2 | `_check_self_management()` farm_access.py + `write()` | **Confirmée** | Vérification `user_company not in access_companies` bloque les modifications sur exploitations d'autres sociétés. |
| B3-1 | 13 modèles config bloquent `company_id=False` pour non-admins | **Confirmée** | Toutes les contraintes `@api.constrains("code", "company_id", "active")` sont présentes avec le filtre de groupe. |
| B4-1 | `_check_plot_farm()` irrigation_sector.py double sens | **Confirmée** | La contrainte vérifie sens secteurs→parcelles ET parcelles→secteurs. |
| B4-2 | `write()` plot.py bloque farm_id | **Confirmée** | La méthode vérifie le groupe admin before allowing farm_id change. |
| B5-1 | `_compute_allocated_area()` ne compte que les actives | **Confirmée** | `farm.plot_ids.filtered('active')` dans le compute. |
| B5-2 | `_invalidate_farm_access_cache()` ciblée | **Confirmée** | Utilise `invalidate_access_cache()` + `invalidate_ormcache("stable")` + `invalidate_ormcache("default")` au lieu de `invalidate_all()`. |
| B6-1 | Structure XML `farm_views.xml` reconstituée | **Confirmée** | Syntaxe XML validée, action en tête, 9/9 éléments clés présents. |

**Total :** 14/14 corrections annoncées **confirmées** par le code source.

---

## D. SÉCURITÉ — VERDICTS PARTIELS

| Domaine | Verdict | justification |
|---------|---------|---------------|
| **Sécurité des exploitations** | ⚠️ PARTIELLE | Les contrôles farm_id et company_id sont en place, mais dépendent entièrement de `has_group()` qui peut être contourné via `sudo()`. Aucun mécanisme SQL de protection. |
| **Sécurité des accès** | ⚠️ PARTIELLE | `_check_self_management()` et `write()` farm_access.py offrent une bonne protection dans le cas d'usage prévu, mais la vérification `env.company` peut être incorrecte selon le contexte multi-société. |
| **Isolation multi-société** | ⚠️ PARTIELLE | Les calculs `gest_agri_farm_ids` et `gest_agri_managed_farm_ids` dans `res_users.py` (non directement vérifiés mais invoqués dans les rapports précédents) semblent prendre en compte les sociétés autorisées, mais cela n'a pas été vérifié directement dans cet audit. |
| **Configurations globales** | ⚠️ PARTIELLE | Les contraintes `@api.constrains` bloquent `company_id=False` pour les non-administrateurs, mais ne résistent pas aux créations via `sudo()` ou aux contournements au niveau SQL. |
| **Parcelles et irrigation** | ⚠️ PARTIELLE | L'invariant parcelle↔secteur est vérifié dans les deux sens via `_check_plot_farm()`, mais seule la modification ultérieure est protégée ; la création initiale peut contourner la règle si les IDs sont définis hors contexte de contrainte. |
| **Unicité et concurrence** | ❌ INSUFFISANTE | Le mécanisme `check_unique_reference()` avec `global_scope` ne garantit pas l'unicité en cas de concurrence two transactions concurrentes peuvent créer le même code avant levée de l'erreur. |

---

## E. TESTS

### Tests existants

| Fichier | Scénarios couverts | Scénarios manquants |
|---------|-------------------|---------------------|
| `tests/test_security.py` | Création d'utilisateurs, affectation de groupes, tests de base des droits d'accès, création/modification d'exploitations et d'accès | Scenarios de `sudo()`, concurrence multi-transaction, isolement multi-société complet |
| `tests/test_patrimony.py` | Création de ferme, parcelle, secteur, compute `allocated_area`, contraintes de base | Scénarios de concurrence, déplacement de parcelle vers autre ferme, modification de `active` + `area` simultanée, création avec `company_id=False` par admin |

### Tests pertinents

- Tests de base des méthodes `write()` avec vérification de groupe
- Tests de compute `_compute_allocated_area()` avecactivation/archivage
- Tests de contraintes `_check_plot_farm()` et `_check_code_unique`

### Tests insuffisants

- **Concurrence :** Aucun test de deux transactions essayant de créer la même ressource en même temps
- **sudo() :** Aucun test utilisant `sudo()` pour contourner les contraintes d'accès
- **Multi-société étendu :** Tests avec plusieurs sociétés et transferts entre elles
- **Edge cases :** Scénarios de suppression d'exploitations, fusion de fermes, archivage massif

### Scénarios non couverts

1. Création d'une exploitation via `sudo()` par un utilisateur non admin
2. Modification de `company_id` d'une exploitation existante pour la rendre globale
3. Déplacement de parcelle vers une ferme d'une autre société dans un contexte multi-entité
4. Concurrence sur création de code unique entre deux utilisateurs
5. Invalidation de cache suite à modification de droits dans un environnement multi-société

---

## F. DÉCISION FINALE

**Le module ne peut pas passer à un test d'installation isolé dans l'état actuel.**

Bien que les 14 corrections annoncées dans le Prompt N°4 TER aient été **confirmées** par la vérification du code source, subsistent les problèmes critiques suivants :

1. **Protection `sudo()` non couverte :** Toutes les protections `@api.constrains` et `has_group()` sont insuffisantes si un utilisateur ou un processus utilise `sudo()`. Aucune contrainte SQL ou mécanisme de base de données ne complète ces protections Python.

2. **Concurrence sur unicité des codes :** Le mécanisme actuel ne garantit pas que deux transactions concurrentes ne créeront pas le même code d'exploitation. Des `UniqueIndex` DB avec filtres partiels sont nécessaires pour une garantée absolue.

3. **Multi-société :** Les mécanismes de contrôle de société reposent sur `env.company` et `has_group()`, qui peuvent être mal configurés dans des environnements multi-entreprises complexes. Des tests avec plusieurs sociétés distinctes sont recommandés.

4. **Chemin de contournement indirect :** Il n'a pas été vérifié s'il existe des chemins indirects (via d'autres modèles, vues XML, actions) permettant de contourner les contrôles farm_id ou company_id.

### Recommandations avant installation :

1. Ajouter des `UniqueIndex` DB sur `(company_id, UPPER(code)) WHERE active IS TRUE` pour les modèles de configuration
2. Ajouter des contraintes `CHECK` ou `ON DELETE RESTRICT` au niveau SQL sur les champs `farm_id` critiques
3. Vérifier le code `res_users.py` pour les méthodes `gest_agri_farm_ids` et `gest_agri_managed_farm_ids`
4. Créer des tests de concurrence et de `sudo()` couvrant les scénarios de contourner
5. Tester avec au moins 2 sociétés distinctes dans la base

### Verdict final :

**NON VALIDÉ — Des corrections supplémentaires sont nécessaires avant toute installation ou mise en production.** Les corrections du Prompt N°4 TER résolvent les défauts bloquants majeurs (ordre XML, action introuvable, contrôles de base), mais les défis de sécurité et de robustesse restent ouverts.

---

*Rapport généré dans le cadre de l'audit Prompt N°5 — Module gestion_agricole — Odoo 20 Community — Lecture seule — Aucune modification apportée aux fichiers source.*