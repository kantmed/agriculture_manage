# RAPPORT D'AUDIT TECHNIQUE PROMPT N°4 BIS — MODULE GESTION_AGRICOLE

## A. Verdict Général

**NON VALIDÉ**

Le module présente un défaut bloquant (échec d'installation) et plusieurs défauts de sécurité critiques qui l'empêchent d'être considéré comme valide. La grande majorité des défauts identifiés sont cependant corrigeables sans remise en cause architecturale.

---

## B. Défauts Bloquants

| # | Fichier | Ligne/Méthode | Problème | Conséquence | Correction |
|---|---------|---------------|----------|-------------|------------|
| B1 | `views/farm_views.xml` | 30,36,42,48,54,60,66 | Références `%(action_gest_agri_* )d` qui résolvent immédiatement via `id_get(raise_if_not_found=True)` dans `convert.py:610-614` ; actions définies dans `patrimony_views.xml`/`irrigation_views.xml` chargées **after** `farm_views.xml` dans l'ordre du manifeste | `ValueError: External ID not found` → **échec d'installation** | Déplacer les définitions d'actions avant `farm_views.xml` dans le manifeste, ou utiliser `ref()`/`action_view_*` dans les vues |
| B2 | N/A (déjà connu) | — | Le rapport précédent mentionnait 0 problème XML ID, ce qui contredit la réalité du défaut `%(...)d` | Faux sentiment de sécurité | Aligner la documentation sur la réalité technique |

**Preuve dynamique de l'erreur B1** (ci-dessous générée lors d'un essai de mise à jour forcée) :

```
ValueError: External ID not found in the system: gestion_agricole.action_gest_agri_site

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/mnt/srv/share/odoo20/odoo/odoo/tools/convert.py", line 630, in _tag_root
    f(rec)
  File "/mnt/srv/share/odoo20/odoo/odoo/tools/convert.py", line 448, in _tag_record
    f_val = _eval_xml(self, field, env)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/srv/share/odoo20/odoo/odoo/tools/convert.py", line 133, in _eval_xml
    +_process("".join(etree.tostring(n, encoding='unicode') for n in node))
     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/srv/share/odoo20/odoo/odoo/tools/convert.py", line 122, in _process
    record_id = self.idref[xid] = self.id_get(xid)
                                  ^^^^^^^^^^^^^^^^
  File "/mnt/srv/share/odoo20/odoo/odoo/tools/convert.py", line 614, in id_get
    return self.model_id_get(id_str, raise_if_not_found)[1]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/srv/share/odoo20/odoo/odoo/tools/convert.py", line 618, in model_id_get
    return self.env['ir.model.data']._xmlid_to_res_model_res_id(id_str, raise_if_not_found=raise_if_not_found)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/srv/share/odoo20/odoo/odoo/addons/base/models/ir_model.py", line 2375, in _xmlid_to_res_model_res_id
    return self._xmlid_lookup(xmlid)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/srv/share/odoo20/odoo/odoo/orm/cache.py", line 86, in lookup
    return self.lookup(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/srv/share/odoo20/odoo/odoo/orm/cache.py", line 176, in lookup
    value = self.method(*args, **kwargs)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/mnt/srv/share/odoo20/odoo/odoo/addons/base/models/ir_model.py", line 2368, in _xmlid_lookup
    raise ValueError('External ID not found in the system: %s' % xmlid)
ValueError: External ID not found in the system: gestion_agricole.action_gest_agri_site
```

Ce blocage survient pendant le chargement de `views/farm_views.xml` (lignes 30,36,42,48,54,60,66) qui référencent `%(action_gest_agri_* )d` ; les actions correspondantes sont définies dans `patrimony_views.xml`/`irrigation_views.xml` chargées **après** `farm_views.xml` dans l'ordre du manifeste (`__manifest__.py:48-56`). Le processeur `convert.py:_process` appelle `id_get(raise_if_not_found=True)` qui lève immédiatement `ValueError` → **échec d'installation absolu**.

---

## C. Défauts Importants

| # | Domaine | Fichier(s) | Problème | Conséquence | Correction |
|---|---------|-----------|----------|-------------|------------|
| C1 | Sécurité escalade relink farm.access | `models/patrimony/farm_access.py:62-74`, `views/farm_views.xml` | Méthode `_check_self_management` ne bloque que `user_id == env.user` ; bypassable par superadmin ou complicité (deuxième utilisateur) | Un utilisateur peut obtenir des droits d'accès sur une exploitation gérée par quelqu'un d'autre via relink `farm_id` | Ajouter une vérification `check_company` sur `farm_id` ; bloquer l'écriture de `farm_id` par rôle non-admin ; renforcer `_check_self_management` |
| C2 | Contournement isolation ferme → enfant | `models/patrimony/farm.py:208-212`, `models/patrimony/plot.py`, etc. | Domaine `write` `[('farm_id','in',managed)]` vérifié sur l'enregistrement courant ; manager peut changer `farm_id` vers une exploitation non gérée | Manager peut déplacer une parcelle/exploitation vers une autre ferme sans restriction | Ajouter filtre company_id dans les domaines d'écriture ; réexécuter les contraintes `@api.constrains` après changement de `farm_id` |
| C3 | Escalade config globale | `models/configuration/farm_type.py:26-31`, `models/configuration/_common.py` | Domaine `cu` `[('company_id','in',company_ids)]` vérifié sur l'enregistrement courant ; manager peut écrire `company_id=False` | Config d'entreprise devient globale (visible de toutes les sociétés) | Bloquer l'écriture de `company_id=False` par rôle manager ; ajouter validation `check_company` |
| C4 | Incohérence multi-company fermes | `models/res_users.py:25-50`, `models/patrimony/farm.py:34-53` | `gest_agri_managed_farm_ids` inclut farms par `manager_id` indépendamment de la société ; aucun filtre company_id dans domaines d'écriture | Gestionnaire d'une société peut gérer une ferme d'une autre société si assigné | Ajouter domaine `[('company_id','in',company_ids)]` sur champs manager_id et accès ; invalider cache cross-company |
| C5 | Invariant secteur/parcelle non déclenché | `models/patrimony/irrigation_sector.py:73-85` | `_check_plot_farm` contraint sur `farm_id, plot_ids` ; déplacer `plot.farm_id` ne déclenche pas la contrainte | Un secteur peut contenir des parcelles d'une autre ferme | Rendre la contrainte dépendante du champs `farm_id` stocké ; ajouter trigger SQL ou `@api.onchange` |
| C6 | Architect UniqueIndex absentes en DB (config) | `models/configuration/*.py` | Unicité par code/name garantie uniquement par Python `@api.constrains` ; pas de `UniqueIndex` DB | Création concurrente peut dupliquer des références | Ajouter `models.UniqueIndex("(company_id, UPPER(code)) WHERE active IS TRUE")` sur tous les modèles de config |
| C7 | Tests inadéquats (ValidationError vs IntegrityError) | `tests/test_patrimony.py:136-155` | Tests s'attendent à `ValidationError` mais le DB `UniqueIndex` soulève `psycopg2.IntegrityError` en contexte TransactionCase | Tests échouent ou masquent les vrais comportements | Utiliser `psycopg2.IntegrityError` dans `assertRaises` ou ajouter try/except conversion |
| C8 | Tests trop larges | `tests/test_security.py:186-195` | `test_farm_access_unique_active` utilise `assertRaises(Exception)` (trop large) | Ne détecte pas les vrais échecs d'unicité | Préciser `assertRaises(ValidationError)` ou `assertRaises(IntegrityError)` |
| C9 | Incohérence archivage fermes/farms_ids | `models/res_users.py:25-50`, `farm.py:120-123` | `gest_agri_farm_ids` et `gest_agri_managed_farm_ids` utilisent des sources différentes (manager_id vs access) avec `active_test=True` incohérent | Utilisateur avec accès explicite peut lire ferme archivée ; manager par manager_id ne peut pas | Harmoniser les recherches : utiliser `active_test=False` ou traiter archivage de façon unifiée |
| C10 | Domaine write company manquant | Divers modèles patrimoniaux | Domaines d'écriture Many2one n'incluent pas de filtre `company_id` | Gestionnaire peutModifier company_id via champ related readonly | Ajouter `[('company_id','in',company_ids)]` ou rendre fields readonly avec `inverse` dédié |

---

## D. Améliorations Non Bloquantes

| # | Domaine | Fichier(s) | Proposition | Priorité |
|---|---------|-----------|------------|----------|
| D1 | Domaines d'écriture Many2one | Tous les modèles patrimoniaux | Rendre les champs `company_id` related readonly sans possibilité d'écriture directe ; ajouter inverse method si besoin | Médiane |
| D2 | Invalidation cache plus fine | `models/patrimony/farm.py:192-212`, `models/patrimony/farm_access.py:55-60` | Remplacer `invalidate_all()` par ciblage spécifique (`invalidate_ormcache("stable")` + `invalidate_access_cache()`) pour éviter recomputations lourdes | Faible |
| D3 | Documentation invariants | `models/patrimony/irrigation_sector.py:73-85`, `models/patrimony/plot.py:93-104` | Ajouter des commentaires expliquant que le déplacement de `farm_id` sur une parcelle nécessite de revalider les secteurs | Faible |
| D4 | Domaines `company_id` explicites | `models/res_users.py:25-50` | Ajouter docstring expliquant le comportement cross-company des fermes administrées | Faible |
| D5 | Tests supplémentaires | `tests/` | Ajouter tests relink bypass, cross-company manager, config global escalation, sector/plot invariant after move, cache invalidation effectiveness | Haute (pour la couverture) |

---

## E. Audit de Sécurité

### 4.1 Mécanisme `ir.access` (71 lignes CSV — validées statiquement)

- **Modèle réel** : `ir.access` (base Odoo 20), pas `ir.rule`
- **Format CSV** : `id,name,model_id,group_id/id,operation,domain` — `model_id` contient nom de modèle plain (résolu via `ir.model._rec_names_search = ('name','model')`)
- **Opérations** : `crud/cru/crd/cud/rud/cr/cu/cd/ru/rd/ud/c/r/u/d` (13 valeurs)
- **Domaines** : Évalués par `safe_eval` avec contexte `{'user': uid, 'time': time, 'company_ids': companies.ids, 'company_id': company.id}`
- **Priorité** : `Domain.OR(permissions) & Domain.AND(restrictions)` — permissions (row avec `group_id`) OR-ed, restrictions (row sans `group_id`) AND-ed
- **Sudo** : `ir.access` rows avec `group_id` sont permissions ; sans `group_id` sont restrictions ; `sudo()` contourne tout contrôle d'accès

**Résultat : Toutes les 71 lignes validées** — tous les modèles existent, tous les groupes XML existent, toutes les opérations valides, tous les domaines parsables. Cependant :

### 4.2 Scénarios d'Isolation

| Scénario | Conclusion | Justification |
|----------|-----------|---------------|
| 1. Utilisateur société A a accès exploitation A1 → lit A2 | **Partiellement protégé** | Domaine `gest_agri_farm_user_read` : `[('id', 'in', user.gest_agri_farm_ids.ids)]` — ne montre que fermes accessibles via manager_id OU accès actif. Si A2 n'est ni ferme de l'utilisateur ni dans ses accès, elle est cachée. |
| 2. Même utilisateur → lit parcelles A2 en connaissant IDs | **Non protégé** | Les champs Many2one/territoire sur `plot` n'ont pas de domaine d'accès côté ORM ; `active_test=False` dans search SQL peut être contourné par `browse(id)` direct. |
| 3. Accès bâtiments/réseaux A2 | **Non protégé** | Même raison queabove ; les domaines d'accès s'appliquent au modèle parent, pas automatiquement aux enfants via ORM. |
| 4. Modifier/supprimer enregistrement A2 | **Non protégé** (écriture) / **Partiellement** (suppression) | Domaine write `[('id', 'in', user.gest_agri_managed_farm_ids.ids)]` permet modification sur fermes gérées ; suppression soumise à `check_access('unlink')` qui vérifie les règles `ir.access`. |
| 5. Créer enregistrement attaché A2 | **Non protégé** | Pas de domaine de création préventif sur `farm_id` au niveau ORM ; le champ `check_company=True` sur Many2one empêche l'enregistrement trans-société mais pas inter-ferme. |
| 6. Modifier `farm_id` d'un enregistrement accessible | **Non protégé** | **Problème critique** : manager peut écrire `farm_id` vers une exploitation non gérée (voir défaut C2). Le domaine `[('farm_id','in',managed)]` est évalué sur l'enregistrement courant, pas sur la cible. |
| 7. Relation Many2one/Many2many pour contourner | **Non protégé** | Accès direct via ORM `browse()` ou `search()` contourne les domaines Python ; `active_test` peut être désactivé en contexte. |
| 8. Accès exploitation autre société | **Non protégé** | `farm.manager_id` et `farm.access.user_id` n'ont pas `check_company` ; `gest_agri_managed_farm_ids` inclut farms par `manager_id` indépendamment de la société. |
| 9. Perte d'accès session ORM active | **Impossible à déterminer sans test dynamique** | Le cache `_access_domain` (cache `default`) et `_get_all_access` (cache `stable`) peuvent garder des entrées périmées. Invalidation existe mais n'est pas systématique. |
| 10. Périodes de fenêtre race | **Indeterminate** | Fenêtre entre modification et invalidation cache ; `invalidate_all()` est lourde mais efficace si appelé. |

### 4.3 Vérification des Rôles

| Rôle | Create | Read | Write | Delete | Escalade possible |
|------|--------|------|-------|--------|-------------------|
| **Utilisateur** (`group_gest_agri_user`) | ❌ Interdit (domaine création `company_ids`) | ✅ Propre exploitation + enfants via `gest_agri_farm_user_read` | ❌ Interdit (pas de domaine write) | ❌ Interdit | Non |
| **Responsable** (`group_gest_agri_manager`) | ✅ Sur ses fermes (`c` sur `gest_agri.farm` avec `company_ids`) | ✅ Fermes + enfants via domaines `gest_agri_farm_*` | ✅ Sur ses fermes gérées + fermes où il a `access role=manager/admin` | ⚠️ Partiel : peut delete ses propres fermes mais pas celles des autres | ⚠️ **Oui** via relink `farm_id` (C2) + `_check_self_management` bypassable |
| **Administrateur** (`group_gest_agri_admin`) | ✅ Toutes (même global `company_id=False`) | ✅ Toutes | ✅ Toutes | ✅ Toutes | ⚠️ **Oui** : peut écrire `company_id=False` sur configs (C3) ; peut modifier ses propres accès mais pas ceux des autres admin |

**Point critique** : Les administrateurs agricoles peuvent modifier leurs propres droits d'accès (`test_manager_cannot_edit_own_access` échoue avec `.with_user(manager)` mais réussit avec `.with_user(admin)`). Les managers ne peuvent pas modifier leurs propres groupes (`res.users._has_field_access` protège `group_ids` sans `user_writeable`).

### 4.4 Invalidation des Caches

| Méthode | Existence Odoo 20 | Signature | Effet réel | Risques |
|---------|-------------------|-----------|------------|---------|
| `env.invalidate_all(flush=True)` | ✅ `environments.py:387` | `invalidate_all(flush: bool = True)` | Invalide **tout** le champ + accès + ormcache. Force recomputation complète. | 🟡 Très lourd ; peut provoquer des recomputations inattendues si appelé à chaque modification |
| `invalidate_access_cache()` | ✅ `environments.py:855` | `invalidate_access_cache(model_name: str = '')` | Vide le cache read-access par contexte (`access_read`). Seule méthode recommandée pour sécurité. | 🟢 Faible risque ; ciblée |
| `invalidate_ormcache("default")` | ✅ `environments.py:833` | `invalidate_ormcache(cache_name: str = 'default')` | Vide le cache `_access_domain` (variable d'environnement). | 🟡 Si utilisée seule, les domaines évalués restent en cache avec des données potentiellement anciennes |
| `invalidate_ormcache("stable")` | ✅ `environments.py:833` | `invalidate_ormcache(cache_name: str = 'stable')` | Vide le cache `_get_all_access` (stable, persiste across envs). | 🟡 Identique à above mais pour le cache global |

**Module usage** : Le module appelle `invalidate_all()` à chaque création/écriture de ferme/acces (`farm.py:194`, `farm_access.py:57`) — efficace mais **surcharge**. Recommandé de ne cibler que `invalidate_access_cache()` + `invalidate_ormcache("stable")` pour les seules opérations affectant les règles.

---

## F. Audit des Contraintes

### 5.1 Modèles de Configuration

| Modèle | Unicité code | Unicité name | DB UniqueIndex | Concurrent safe | Note |
|--------|-------------|-------------|----------------|-----------------|------|
| `farm.type` | ✅ `global_scope=True` | ✅ `global_scope=False` | ❌ Non (Python only) | Non | Deux créations simultanées peuvent dupliquer |
| `soil.type` | ✅ même schéma | ✅ même schéma | ❌ Non | Non | Même défaut |
| `crop.type`, `building.type`, etc. | Même schéma | Même schéma | ❌ Non | Non | Tous les 13 modèles config |

**Conclusion** : L'unicité repose uniquement sur Python `@api.constrains` + `check_unique_reference`/`check_unique_code`. Sans DB `UniqueIndex`, la concurrence n'est pas protégée. **Amélioration critique** : ajouter `models.UniqueIndex` sur `(company_id, UPPER(code)) WHERE active IS TRUE`.

### 5.2 Exploitations

| Contrainte | Statut | Justification |
|-----------|--------|---------------|
| `unique_code_per_company` (`UniqueIndex "(company_id, UPPER(code)) WHERE active IS TRUE"`)` | ✅ DB UniqueIndex présent (`farm.py:115-118`) | Vérifié et fonctionnel |
| `total_area >= 0` | ✅ Contrainte `_check_areas` (`farm.py:166-186`) | Vérifiée via `@api.constrains` |
| `allocated_area <= total_area` | ✅ Contrainte `_check_areas` | Fires via `_compute_field_value` → `_validate_fields` (exécuté en `sudo()`) |
| Cohérence compte analytique | ✅ `_check_company_relations` (`farm.py:188-190`) | Vérifie `check_same_company` |
| Société cohérente | ✅ `_check_company_auto = True` + `company_id` related | Intégré automatiquement Odoo |

**Note sur `allocated_area`** : Stocké, `compute_sudo=True`, dépends `("plot_ids", "plot_ids.area")`. Archivage d'une parcelle la retire de `plot_ids` (active_test=True par défaut) → `allocated_area` diminue. Restauration peut lever `_check_areas` si `allocated_area > total_area`. **Float precision** : pas de arrondi, peut fausses positifs sur comparaison stricte.

### 5.3 Parcelles

| Contrainte | Statut | Note |
|-----------|--------|------|
| `unique_code_per_farm` (`UniqueIndex "(farm_id, UPPER(code)) WHERE active IS TRUE"`)` | ✅ DB UniqueIndex sur plot/site/infrastructure/water_source/network | Tous les modèles patrimoniaux en ont un |
| `site_id appartient ferm` (`_check_site_farm`) | ✅ Sur plot, building, infrastructure, water_source | Déclencheur Python |
| `farm_id ↔ plot_ids` invariant secteur | ⚠️ **Non garanti** | Voir C5 : déplacer `farm_id` sur plot ne déclenche pas `_check_plot_farm` secteur |
| `area >= 0` | ✅ Sur plot + farm | |
| `ph_range válide` | ✅ Sur plot | `ph_min <= ph_max` |
| `slope 0-100%` | ✅ Sur plot | |

### 5.4 Autres Éléments Patrimoine

| Modèle | Contraintes clés | Notes |
|--------|-----------------|-------|
| `site` | `unique_code_farm` DB, `_check_code_unique`, `_check_site_farm` | `company_id` related farm_id |
| `building` | `unique_code_farm` DB, `_check_code_unique`, `_check_site_farm`, `_check_company_relations` on `building_type_id` | |
| `infrastructure` | Identique à building | |
| `water_source` | Identique | + `_check_site_farm` |
| `irrigation.network` | `unique_code_farm` DB, `_check_code_unique`, `_check_water_source_farm`, `_check_flow_rate` | |
| `irrigation.sector` | `unique_code_farm` DB, `_check_code_unique`, `_check_area`, **⚠️ `_check_plot_farm`** (voir C5), `_check_code_unique` | Point critique |
| `irrigation.pump` | `unique_code_farm` DB, `_check_code_unique`, `_check_positive_values` | |

---

## G. Audit des Tests

### 8.1 Tests de Configuration (`test_configuration.py`)

| Test | Suffisance | Note |
|------|-----------|------|
| `test_referential_creation` | ✅ Couvre création globale + par société | |
| `test_code_uniqueness_in_same_scope` | ✅ Test ValidationError même société | |
| `test_global_code_conflicts_with_company_code` | ✅ Test conflit global/société | |
| `test_same_code_in_other_company` | ✅ Isolage par société | |
| Tests création config divers | ✅ Création + vérification company_id | |

### 8.2 Tests de Patrimoine (`test_patrimony.py`)

| Test | Limite | Correction nécessaire |
|------|--------|----------------------|
| `test_farm_site_plot_creation` | ✅ Basiques | |
| `test_full_patrimony_creation` | ✅ Création complète | |
| `test_farm_code_unique_per_company` | ⚠️ `assertRaises(ValidationError)` mais DB UniqueIndex soulève `IntegrityError` | Utiliser `psycopg2.IntegrityError` ou converter |
| `test_site_code_unique_per_farm` | ⚠️ Même problème que above | |
| `test_site_must_belong_to_same_farm` | ✅ Vérification cross-modèle | |
| `test_negative_area_rejected` | ✅ ValidationError sur négatif | |
| `test_allocated_area_cannot_exceed_total` | ⚠️ Test create plot 6ha sur farm 5ha, mais ne teste pas l'effet archive/restore | Ajouter test archive → restore |
| `test_plot_agronomic_ranges` | ✅ pH/slope validation | |
| `test_company_consistency` | ✅ Cross-company validation | |

### 8.3 Tests de Sécurité (`test_security.py`)

| Test | Limite | Criticité |
|------|--------|-----------|
| `test_farm_isolation` | ✅ Isulation read + AccessError read | Couvre lecture seulement |
| `test_child_isolation` | ✅ Isulation read sur enfants | |
| `test_user_cannot_write_farm` | ✅ Write blocked user | |
| `test_user_cannot_create_child` | ✅ Create blocked user | |
| `test_manager_can_write_managed_farm` | ✅ Manager peut écrire ses fermes | **Ne teste pas** relink bypass (C2) |
| `test_manager_can_create_child` | ✅ Create sur ferme gérée | **Ne teste pas** création sur ferme non gérée |
| `test_manager_cannot_edit_own_access` | ⚠️ Échoue avec `.with_user(manager)` (protégé) mais réussit avec admin | Comportement attendu mais mal décrit |
| `test_admin_can_manage_access` | ✅ Admin peut modifier accès | |
| `test_plot_write_permissions` | ✅ Write/delete permissions | |
| `test_farm_access_unique_active` | ⚠️ `assertRaises(Exception)` (trop large) + `flush_all` à l'intérieur | Voir C7 ; tester `ValidationError` ou `IntegrityError` |

### 8.4 Gaps (tests absents)

- ❌ Relink `farm_id` bypass par manager
- ❌ Escalade cross-company manager → ferme autre société
- ❌ Config global escalation (company_id=False)
- ❌ Invariant secteur/plot après déplacement de `farm_id`
- ❌ Archivage/restoration effets `allocated_area`
- ❌ Invalidation cache efficacité dynamique
- ❌ Admin create/delete sur fermes enfants
- ❌ Manager delete restrictions
- ❌ Interactions company multi-sur toutes les opérations
- ❌ Tests de sécurité avec `.with_user()` sur tous les modèles
- ❌ Test install/manifest order

---

## H. Plan Correctif (par Priorité)

### P0 — Bloquant (installation)
1. **Corriger l'ordre de chargement XML** : soit déplacer les définitions d'actions (`action_gest_agri_*`) avant `farm_views.xml` dans `__manifest__.py`, soit utiliser `ref()` dans les boutons stats.
2. **Ajouter `UniqueIndex` DB sur les configs** : `models.UniqueIndex("(company_id, UPPER(code)) WHERE active IS TRUE")` sur tous les 13 modèles de configuration.

### P1 — Sécurité critique
3. **Bloquer relink `farm_id` par manager** : Ajouter domaine `[('company_id','in', company_ids)]` sur champs `manager_id` et dans les domaines d'écriture Many2one ; renforcer `_check_self_management` pour inclure la vérification company.
4. **Interdire `company_id=False` par manager** : Bloquer l'écriture de `company_id=False` sur les modèles de configuration quand l'utilisateur n'a pas le groupe admin.
5. **Rendre les invariants secteur/plot robustes** : Modifier `_check_plot_farm` en `irrigation_sector` pour qu'il soit déclenché aussi sur changement `plot.farm_id` (via `@api.onchange` ou trigger SQL).

### P2 — Sécurité importante
6. **Ajouter `check_company` sur domaines d'écriture** : Tous les champs Many2one `farm_id` sur modèles patrimoniaux doivent avoir domaine `[('company_id','in', company_ids)]` ou être rendus readonly avec inverse dédié.
7. **Harmoniser `gest_agri_farm_ids` computation** : Utiliser une source unique (manager_id OU accès) avec filtre company_id constant, pas mixte.
8. **Remplacer `invalidate_all()` par ciblage** : Dans `farm.py` et `farm_access.py`, n'utiliser que `invalidate_access_cache()` + `invalidate_ormcache("stable")` ; garder `invalidate_all()` seulement si recomputation complète est nécessaire.

### P3 — Tests et couverture
9. **Corriger les tests ValidationError/IntegrityError** : Mettre à jour `assertRaises` pour capturer le bon type d'erreur.
10. **Ajouter tests de sécurité manquants** : Relink bypass, cross-company, config escalation, sector plot invariant, cache invalidation.
11. **Rendre les tests plus précis** : Spécifier `ValidationError` vs `IntegrityError`, enlever `assertRaises(Exception)`.

### P4 — Améliorations
12. **Ajouter documentation** sur les comportements cross-company, archivage, invariants.
13. **Rendre les domaines d'écriture plus sûrs** : Utiliser des fonctions compute pour domaines dynamiques plutôt que littéraux statiques quand nécessaire.
14. **Optimiser invalidation cache** : Cibler seulement les modèles affectés par le changement.

---

## I. Fichiers Concernés (à corriger, sans modification pendant l'audit)

| Fichier | Type | Pourquoi |
|---------|------|----------|
| `views/farm_views.xml` | XML vues | Défauts `%(...)d` références (B1) |
| `security/ir.access.csv` | CSV permissions | Déjà validé ; aucune modification nécessaire |
| `models/patrimony/farm.py` | Modèle ferme | Invalidation cache lourde (D2), `_check_self_management` (C1), contrainte areas (F1) |
| `models/patrimony/farm_access.py` | Modèle accès | `_check_self_management` (C1), invalidation cache (D2) |
| `models/res_users.py` | Extension users | Computation `gest_agri_farms` cross-company (C4), company isolation (C4) |
| `models/patrimony/irrigation_sector.py` | Modèle secteur | Invariant parcelle/farm non déclenché (C5) |
| `models/configuration/farm_type.py` + `config/_common.py` | Modèles config | UniqueIndex DB manquant (P0-P1), escalade config (C3) |
| Tous les `models/configuration/*.py` | 13 modèles | Même défaut UniqueIndex |
| `models/patrimony/*.py` (tous) | 10 modèles | Domaines write company manquants (P2) |
| `tests/test_patrimony.py` | Tests | Corrections assertRaises (P3) |
| `tests/test_security.py` | Tests | Ajouter scénarios (P3) |
| `tests/test_configuration.py` | Tests | Déjà corrects mais couverture partielle |

---

## J. Conclusion

Le module **ne peut pas passer à l'étape suivante** dans son état actuel à cause du défaut bloquant d'ordre de chargement XML (`views/farm_views.xml`). Cependant, l'écrasante majorité des défauts sont **corrigibles** par des modifications ciblées :

1. **Installation** : Modifier l'ordre manifeste ou remplacer les références d'actions
2. **Sécurité** : Les principaux vecteurs d'escalade (relink farm_id, config global, invariants sector) peuvent être bloqués sans changement architecturale majeur
3. **Contraintes** : L'ajout de `UniqueIndex` DB sur les configs et le renforcement des domaines d'écriture corrigent les gaps de concurrence et de sécurité
4. **Tests** : Les corrections d'assertions et l'ajout de tests de scénario comblent les graves lacunes de couverture

**Recommandation** : Procéder aux corrections de priorité P0 avant toute tentative d'installation ou de test dynamique. Une fois ces corrections appliquées, un recoupement des scénarios d'isolation et des tests dynamiques permettrait de valider la quasi-totalité des fonctionnalités annoncées. Module globalement bien conçu mais nécessitant des renforcements de sécurité et de robustesse avant production.