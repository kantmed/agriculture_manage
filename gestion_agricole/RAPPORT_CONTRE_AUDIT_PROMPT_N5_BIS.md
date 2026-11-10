# RAPPORT DE CONTRE-AUDIT PROMPT N°5 BIS — MODULE GESTION_AGRICOLE

*Audit strictement en lecture seule. Aucun fichier source n'a été modifié, aucune base de données ni serveur n'a été touché.*

---

## A. VERDICT GÉNÉRAL

**NON VALIDÉ — ANOMALIES CONFIRMÉES**

Le contre-audit confirme la plupart des anomalies identifiées dans le rapport Prompt N°5, mais révèle également plusieurs approximations dans l'analyse précédente. Plusieurs anomalies sont **partiellement confirmées** (les mécanismes existent mais ont des limitations techniques), et une anomalie critique (A11 - unicité et concurrence) est **techniquement confirmée** avec des preuves concrètes dans le code.

**Conclusion :** Le module présente des défauts réels, particulièrement sur le mécanisme d'unicité en concurrence et le contournement potentiel via `sudo()`. Les corrections du Prompt N°4 TER résolvent les défauts bloquants d'installation, mais les problématiques de sécurité et d'intégrité des données restent ouvertes.

---

## B. TABLEAU DE VÉRIFICATION DES ANOMALIES N°5

| ID | Gravité | Anomalie du Rapport N°5 | Verdict Contre-Audit | Preuve Technique |
|----|---------|------------------------|----------------------|------------------|
| A1 | P0 | Ordre manifeste : `patrimony_views.xml` et `irrigation_views.xml` avant `farm_views.xml` | **CONFIRMÉ** | Vérification dans `__manifest__.py` lignes 52-62 : l'ordre est correct. Les dépendances XML chargent dans le bon ordre. |
| A2 | P0 | Action `action_gest_agri_farm_access` déplacée en tête de `farm_views.xml` | **CONFIRMÉ** | L'enregistrement est à la ligne 5, juste après le commentaire `<!-- Exploitations agricoles -->`. Tous les boutons `%(... )d` référencent maintenant une action existante. |
| A3 | P0 | Structure XML validée mais dépendances inter-fichiers non vérifiées | **PARTIELLEMENT CONFIRMÉ** | Le XML est syntaxiquement valide et l'ordre manifeste est correct. Cependant, toute anomalie dans `patrimony_views.xml` ou `irrigation_views.xml` bloquerait tout de même l'installation. Ces fichiers n'ont pas été vérifiés en détail dans ce contre-audit. |
| A4 | P1 | `write()` farm.py vérifie farm_id et company_id | **CONFIRMÉ** | La méthode vérifie `has_group("gestion_agricole.group_gest_agri_admin")` before allowing farm_id change (lignes 211-237 de farm.py). **Risque :** Si l'opération est invoquée avec `sudo()`, le contrôle `has_group()` s'exécute tout de même sur `self.env.user` qui reste l'utilisateur d'origine, mais la write s'effectue avec les droits étendus. |
| A5 | P1 | `_compute_allocated_area()` ne compte que les parcelles actives | **CONFIRMÉ** | La ligne `farm.plot_ids.filtered('active')` est présente dans farm.py. Le compute est correct. |
| A6 | P1 | `_check_self_management()` farm_access.py compare `env.company` | **CONFIRMÉ** | La vérification `user_company not in access_companies` est présente (lignes 68-81 de farm_access.py). **Nuance :** `env.company` dépend du contexte actif et peut ne pas refléter la société "courante" dans tous les scénarios multi-entreprises. |
| A7 | P1 | `write()` farm_access.py avec `farm_id` dans vals | **CONFIRMÉ** | Même pattern que farm.py : vérification `has_group()` before allowing farm_id change (lignes 94-112 de farm_access.py). |
| A8 | P1 | `_check_plot_farm()` irrigation_sector.py double sens | **CONFIRMÉ** | La contrainte vérifie sens secteurs→parcelles ET parcelles→secteurs (lignes 73-102 de irrigation_sector.py). |
| A9 | P1 | `write()` plot.py bloque farm_id | **CONFIRMÉ** | Vérification `has_group()` present (lignes 153-172 de plot.py). Même remarque que A4/A7 concernant `sudo()`. |
| A10 | P1 | 13 modèles config bloquent `company_id=False` pour non-admins | **CONFIRMÉ** | Toutes les contraintes `@api.constrains` sont présentes avec le filtre de groupe. **Nuance technique critique :** ces contraintes utilisent `records.sudo().search(domain)` qui **bypass les droits d'accès** pendant la recherche (voir analyse A11). |
| A11 | P1 | Unicité et concurrence des codes | **CONFIRMÉ** (comme critique) | **Preuve technique :** Le mécanisme `check_unique_reference()` dans `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/models/configuration/_common.py` présente un bug de logique lorsque `global_scope=False` et `record.company_id` est défini : le domaine ne vérifie que la société et ignore les enregistrements globaux (company_id=False). De même, `check_unique_code()` n'empêche pas la coexistence d'un code global et d'un code société identique. De plus, `records.sudo().search()` dans les deux fonctions contourne les ACL pendant la recherche, ce qui signifie que la validation a lieu dans un contexte sans restrictions d'accès. |
| A12 | P2 | Invalidation des caches : `invalidate_all()` dans farm_access.py | **CONFIRMÉ** | La méthode `invalidate_all()` invalide tous les caches (voir farm_access.py lignes 43-48), alors que farm.py utilise une invalidation ciblée (`invalidate_access_cache()` + `invalidate_ormcache("stable")` + `invalidate_ormcache("default")`). La différence n'est pas fonctionnelle mais de performance/précision. |
| A13 | P2 | Couverture des tests | **CONFIRMÉ** | Les tests existants (`test_security.py`, `test_patrimony.py`) couvrent les cas de base mais manquent de scénarios de concurrence, de `sudo()` et de multi-société étendu. |
| A14 | P3 | Méthodes d'invalidation différentes selon les modèles | **CONFIRMÉ** | La différence d'implémentation entre farm.py et farm_access.py est réelle, mais les deux méthodes invalident les caches nécessaires. La stratégie de farm_access.py (`invalidate_all()`) est plus large mais techniquement correcte. |

---

## C. ANOMALIES VRAIMENT CONFIRMÉES (Classement par gravité)

### P0 — Installation et XML

| Anomalie | Statut | Détail |
|----------|--------|--------|
| A1 (ordre manifeste) | **Confirmée** | L'ordre dans `__manifest__.py` est correct : `patrimony_views.xml` et `irrigation_views.xml` chargent avant `farm_views.xml`. |
| A2 (action en tête XML) | **Confirmée** | L'action `action_gest_agri_farm_access` est bien placée en tête de `farm_views.xml` (ligne 5). |
| A3 (dépendances XML) | **Confirmée (faible)** | L'ordre manifeste est correct, mais l'intégrité des fichiers dépendants n'a pas été vérifiée. |

### P1 — Sécurité et Intégrité

| Anomalie | Statut | Détail |
|----------|--------|--------|
| A4 (write farm.py) | **Confirmée** | Vérification `has_group()` présente, mais contournable via `sudo()`. |
| A5 (compute allocated_area) | **Confirmée** | Compute correct avec `filtered('active')`. |
| A6 (_check_self_management) | **Confirmée** | Vérification `env.company` présente, mais dépendance au contexte. |
| A7 (write farm_access.py) | **Confirmée** | Même pattern que A4. |
| A8 (_check_plot_farm) | **Confirmée** | Double sens vérifié. |
| A9 (write plot.py) | **Confirmée** | Même pattern `has_group()`. |
| A10 (13 modèles config) | **Confirmée (technique)** | Contraintes `@api.constrains` présentes, mais utilisent `records.sudo().search()` qui bypass les ACL. |
| **A11 (unicité et concurrence)** | **CONFIRMÉE (CRITIQUE)** | Voir section D ci-dessous. |

### P2 — Calculs et Cache

| Anomalie | Statut | Détail |
|----------|--------|--------|
| A12 (invalidation cache) | **Confirmée** | Différence de stratégie entre les modèles, mais les deux sont techniquement valides. |
| A13 (tests) | **Confirmée** | Couverture partielle, scénarios manquants. |
| A14 (méthodes d'invalidation) | **Confirmée** | Différences existantes mais pas de risque critique. |

### P3 — Robustesse

| Anomalie | Statut | Détail |
|----------|--------|--------|
| Aucun | — | Toutes les corrections annoncées sont techniquement présentes. |

---

## D. ANALYSE TECHNIQUE CRITIQUE — anomalie A11 (unicité et concurrence)

### 1. Problème identifié dans `check_unique_reference()`

**Fichier :** `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/models/configuration/_common.py`

**Mécanisme examiné :** La fonction `check_unique_reference()` est utilisée par les 13 modèles de configuration (farm_type, soil_type, crop_type, etc.) pour vérifier l'unicité des codes et noms.

**Le bug de logique :**

```python
def check_unique_reference(records, field_name, label, global_scope=False):
    for record in records:
        value = record[field_name]
        if not value:
            continue
        domain = [("active", "=", True), ("id", "!=", record.id)]
        if record.company_id:
            if global_scope:
                domain = [
                    "|",
                    ("company_id", "=", record.company_id.id),
                    ("company_id", "=", False),
                ] + domain
            else:
                domain = [("company_id", "=", record.company_id.id)] + domain  # ← PROBLÈME
        elif not global_scope:
            domain = [("company_id", "=", False)] + domain
        # Si on atteint ici avec record.company_id=False et global_scope=True,
        # domain reste inchangé (pas de filtre company_id)

        # ... recherche avec records.sudo().search(domain)
```

**Les quatre cas de figure :**

| Cas | Condition | Domaine généré | Problème |
|-----|-----------|----------------|----------|
| 1 | `company_id` défini + `global_scope=True` | `(`company_id = X` `OR` `company_id = False`)` + base | ✅ Correct : vérifie société ET global |
| 2 | `company_id` défini + `global_scope=False` | `(`company_id = X`)` + base | ❌ **BUG**: n'ajoute pas de vérification pour `company_id = False` (global) |
| 3 | `company_id` False + `global_scope=False` | `(`company_id = False`)` + base | ✅ Correct : vérifie uniquement les globaux |
| 4 | `company_id` False + `global_scope=True` | base (pas de filtre company) | ⚠️ Comportement dépendant : recherche tous les enregistrements actifs sans filtre company |

**Le cas critique (Cas 2) :** Lorsqu'un enregistrement a `company_id` défini et que `global_scope=False`, la fonction ne vérifie **pas** la présence d'un enregistrement global (company_id=False) du même code. Cela signifie :

- Un code "POLY" unique au sein de la société A pourrait entrer en conflit avec un code global "POLY" existant, sans que la contrainte ne le détecte.
- Inversement, un code global "POLY" pourrait être créé alors qu'un code "POLY" existe déjà dans une société, sans lever d'erreur.

**De plus**, les deux fonctions `check_unique_reference()` et `check_unique_code()` utilisent `records.sudo().search(domain)`, ce qui **bypass les ACL (Access Control Lists)** pendant la recherche. La validation a donc lieu dans un contexte sans restrictions d'accès, ce qui n'est pas représentatif du comportement réel de l'utilisateur.

### 2. Problème dans `check_unique_code()`

**Fichier :** `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/models/patrimony/_common.py`

**Mécanisme :** Utilisé par plot.py, irrigation_sector.py, irrigation_pump.py, site.py, infrastructure.py, water_source.py.

**Fonctionnement :** La fonction accepte un `scope_field` (ex: `farm_id`) pour restreindre la recherche. Si `scope_field="farm_id"` et que la parcelle a `farm_id=X`, elle recherche les parcelles actives où `farm_id = X`.

**Limitation :** Elle ne prévient pas la coexistence entre :
- Un code global (farm_id=False) et un code société (farm_id=X) identique
- Deux codes société dans des sociétés différentes (autorisé, mais le mécanisme ne l'explicite pas)

De plus, comme `check_unique_reference`, elle utilise `records.sudo().search()`, ce qui contourne les droits d'accès pendant la validation.

### 3. Comportement en transaction concurrente

**PostgreSQL et index uniques :** Aucune contrainte Python (`@api.constrains`) ne peut garantir l'unicité en transaction concurrente, car :

1. La Transaction A lit l'état actuel, vérifie l'unicité (ok), puis écrit.
2. La Transaction B lit l'état actuel (même état), vérifie l'unicité (ok), puis écrit.
3. Les deux transactions aboutissent avec la même valeur en base, violant l'unicité.

Les `UniqueIndex` partiels de PostgreSQL sont la seule garantie, mais :
- Les index `(farm_id, UPPER(code)) WHERE active IS TRUE` présents dans le module garantissent l'unicité **dans le périmètre de la ferme**
- Ils ne garantissent pas l'unicité globale/société selon la règle :
  - "Un code global unique parmi toutes les sociétés"
  - "Un code société unique dans cette société"
  - "Un code global ne peut pas coexister avec un code identique dans une société"

**Conclusion :** Le mécanisme actuel ne respecte pas formellement la règle d'unicité globale/société demandée dans le prompt, et offre **aucune garantie de concurrence**.

---

## E. AFFIRMATIONS INCORRECTES DU RAPPORT PRÉCÉDENT

| Anomalie | Affirmation initiale | Vérification contre-audit | Correction |
|----------|--------------------|--------------------------|------------|
| A10 | "Les contraintes `@api.constrains` sont une protection suffisante" | **Incorrect** | Les contraintes utilisent `records.sudo().search()` qui bypass les ACL. Elles ne protègent que contre les modifications "normales" via l'interface Odoo, pas contre les opérations SQL directes ou les contournements `sudo()`. |
| A6 | "`env.company` est incorrect dans les scénarios multi-société" | **Non confirmé** | `env.company` se comporte comme prévu dans Odoo 20 : il reflète la société par défaut de l'utilisateur ou celle du contexte actif. Le problème n'est pas que `env.company` soit "faux", mais qu'il dépend du contexte, ce qui peut surprendre les développeurs non familiarisés avec Odoo multi-entreprises. |
| A14 | "`invalidate_all()` est une erreur critique" | **Incorrect** | `invalidate_all()` invalide tous les caches, ce qui est plus large mais pas erronné. Cela peut causer une recomputation inutile, mais ne laisse pas de droits obsolètes. La différence avec l'invalidation ciblée de farm.py est principalement de performance, pas de correction de sécurité. |

---

## F. PROPOSITION DE CORRECTIONS (À NE PAS APPLIQUER)

| Identifiant | Fichier | Méthode | Correction recommandée | Risque de régression | Test à ajouter |
|-------------|---------|---------|------------------------|----------------------|----------------|
| A11 | `models/configuration/_common.py` | `check_unique_reference()` | **Rajouter la vérification globale dans le Cas 2** : lorsque `global_scope=False` et `company_id` défini, ajouter `("company_id", "=", False)` au domaine :<br>`domain = [("company_id", "=", record.company_id.id)] + [("company_id", "=", False)] + domain` | **Médium** : Modifie le comportement d'union de domaines qui pourrait affecter d'autres cas d'usage des 13 modèles. | Test de création simultanée d'un code société et d'un code global identique. |
| A11 | `models/patrimony/_common.py` | `check_unique_code()` | **Ajouter une vérification de portée globale** : après la recherche par `scope_field`, ajouter une vérification supplémentaire pour les codes globaux (company_id=False) et les codes des autres sociétés. | **Faible** : La fonction est utilisée sur les modèles de domaine (plot, sector, etc.) qui ont déjà des index uniques par farm_id. | Test de création d'un code identique dans deux sociétés différentes. |
| A4/A7/A9 | `models/patrimony/farm.py`, `farm_access.py`, `plot.py` | `write()` | **Renforcer la protection contre `sudo()`** : ajouter une vérification au niveau du champ `company_id` ou utiliser `self.env.company` avec vérification explicite des sociétés autorisées. | **Faible** : Les méthodes actuelles fonctionnent correctement dans le cas d'usage Odoo standard. | Test avec appel `sudo()` depuis Python. |
| A6 | `models/patrimony/farm_access.py` | `_check_self_management()` | **Utiliser `user.company_id` au lieu de `env.company`** pour éviter la dépendance au contexte actif. | **Faible** | Test avec contexte `company_id` explicite. |

**Aucune correction ne doit être appliquée dans le cadre de cet audit.** Les propositions ci-dessus sont fournies à titre technique uniquement.

---

## G. DÉCISION FINALE

**État :** Le module nécessite des corrections ciblées avant toute mise en production, mais les défauts bloquants d'installation (P0) ont été résolus par le Prompt N°4 TER.

**Recommandations prioritaires :**

1. **Critique :** Corriger le bug de logique dans `check_unique_reference()` (anomalie A11, Cas 2) pour garantir la cohérence entre codes globaux et codes société. C'est le problème technique le plus sérieux identifié par ce contre-audit.

2. **Élevée :** Documenter et tester le comportement des méthodes `write()` lorsqu'elles sont appelées avec `sudo()`. Les contrôles `has_group()` sont efficaces pour l'interface utilisateur mais peuvent être contournés par des opérations Python privilégié.

3. **Moyenne :** Examiner le usage de `env.company` vs `user.company_id` dans les scénarios multi-société pour s'assurer que le contexte est toujours correct.

4. **Basse :** Uniformiser les stratégies d'invalidation de cache entre farm.py et farm_access.py (bien que les deux soient techniquement valides).

**Verdict final :**

**NON VALIDÉ — ANOMALIES CONFIRMÉES**, avec une priorité critique sur le mécanisme d'unicité des codes (A11). Le module peut être installé (les erreurs XML ont été corrigées), mais des corrections techniques sont nécessaires pour garantir l'intégrité des données dans les scénarios de concurrence et multi-société avant une mise en production.

*Rapport généré dans le cadre du contre-audit Prompt N°5 Bis — Module gestion_agricole — Odoo 20 Community — Lecture seule — Aucune modification apportée aux fichiers source.*