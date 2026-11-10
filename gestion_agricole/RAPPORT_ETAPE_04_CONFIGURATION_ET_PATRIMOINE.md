# RAPPORT DE LIVRAISON — PROMPT N°4
## Module Odoo 20 Community « Gestion Agricole » — Configuration et patrimoine agricole

> **Destinataire :** ChatGPT (validation de l'étape PROMPT N°4)
> **Objet :** compte rendu complet de l'implémentation, des contrôles effectués et des limites.
> **Consigne :** cette étape s'arrête ici. Aucune étape ultérieure (production végétale, élevage, campagnes, stocks, achats/ventes, comptabilité, personnel) n'a été commencée.

---

## 1. Identification

| Élément | Valeur |
|---|---|
| Module | `gestion_agricole` |
| Version | `20.0.1.0.0` |
| Odoo | 20 Community |
| Dossier | `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/` |
| Préfixe métier | `gest_agri` |
| Addon installable | un seul |
| Dépendances | `base`, `mail`, `contacts`, `uom`, `product`, `stock`, `stock_account`, `purchase`, `sale_management`, `account`, `analytic`, `maintenance` |

Aucune dépendance vers `hr`, `fleet`, `project`, `website`, `portal`, `report_xlsx`, `base_account_budget` ou `base_accounting_kit`.

---

## 2. Périmètre livré

| Élément | Quantité |
|---|---|
| Référentiels de configuration | 13 |
| Modèles de patrimoine | 10 |
| Modèles métier `gest_agri.*` | 23 |
| Modèle natif étendu (`res.users`) | 1 |
| Lignes de droits `ir.access` | 71 |
| Vues liste / formulaire / recherche | 69 (23 × 3) |
| Actions de fenêtre | 23 |
| Menus | 8 racines + 6 sous-menus Configuration + 23 entrées |
| Fichiers XML | 7 |
| Fichiers de tests | 4 |

---

## 3. Arborescence livrée

```
gestion_agricole/
├── __init__.py
├── __manifest__.py
├── README.md
├── data/
│   └── sequences.xml
├── models/
│   ├── __init__.py
│   ├── res_users.py
│   ├── configuration/
│   │   ├── __init__.py
│   │   ├── _common.py
│   │   ├── building_type.py
│   │   ├── crop_type.py
│   │   ├── crop_variety.py
│   │   ├── equipment_type.py
│   │   ├── farm_type.py
│   │   ├── fertilizer_type.py
│   │   ├── irrigation_type.py
│   │   ├── livestock_breed.py
│   │   ├── livestock_species.py
│   │   ├── operation_type.py
│   │   ├── production_type.py
│   │   ├── soil_type.py
│   │   └── treatment_type.py
│   └── patrimony/
│       ├── __init__.py
│       ├── _common.py
│       ├── farm.py
│       ├── farm_access.py
│       ├── site.py
│       ├── plot.py
│       ├── building.py
│       ├── infrastructure.py
│       ├── water_source.py
│       ├── irrigation_network.py
│       ├── irrigation_sector.py
│       └── irrigation_pump.py
├── security/
│   ├── security.xml
│   └── ir.access.csv
├── views/
│   ├── menu_views.xml
│   ├── configuration_views.xml
│   ├── farm_views.xml
│   ├── patrimony_views.xml
│   └── irrigation_views.xml
├── tests/
│   ├── __init__.py
│   ├── test_module_install.py
│   ├── test_configuration.py
│   ├── test_patrimony.py
│   └── test_security.py
└── static/description/icon.png   (512 × 512, RGBA, original)
```

---

## 4. Fichiers créés et modifiés

### 4.1 Créés

**Configuration (13 modèles + 2 fichiers techniques)**
`models/configuration/_common.py`, `__init__.py`, et un fichier par modèle : `farm_type`, `soil_type`, `crop_type`, `crop_variety`, `livestock_species`, `livestock_breed`, `operation_type`, `treatment_type`, `fertilizer_type`, `irrigation_type`, `equipment_type`, `building_type`, `production_type`.

**Patrimoine (10 modèles + 2 fichiers techniques)**
`models/patrimony/_common.py`, `__init__.py`, `farm.py`, `farm_access.py`, `site.py`, `plot.py`, `building.py`, `infrastructure.py`, `water_source.py`, `irrigation_network.py`, `irrigation_sector.py`, `irrigation_pump.py`.

**Autres**
`models/res_users.py`, les 4 fichiers de vues (`configuration_views.xml`, `farm_views.xml`, `patrimony_views.xml`, `irrigation_views.xml`), et les 3 fichiers de tests (`test_configuration.py`, `test_patrimony.py`, `test_security.py`).

### 4.2 Modifiés

| Fichier | Modification |
|---|---|
| `__manifest__.py` | ajout des 4 fichiers de vues dans `data`, dans l'ordre de dépendance correct |
| `models/__init__.py` | import de `configuration`, `res_users`, `patrimony` |
| `security/security.xml` | `group_gest_agri_user` implique désormais `base.group_user` |
| `security/ir.access.csv` | matrice complète de 71 lignes |
| `tests/__init__.py` | ajout des 3 nouveaux modules de tests |
| `README.md` | réécriture pour le périmètre du prompt n°4 |
| `static/description/icon.png` | icône originale 512×512 RGBA générée avec PIL |

---

## 5. Modèles et champs

### 5.1 Référentiels de configuration

| Modèle | Champs | Champs spécifiques |
|---|---|---|
| `gest_agri.farm.type` | `name`, `code`, `description`, `active`, `company_id`, `sequence` | — |
| `gest_agri.soil.type` | idem | — |
| `gest_agri.crop.type` | idem | `crop_cycle` : `annual` / `perennial` |
| `gest_agri.crop.variety` | idem | `crop_type_id` obligatoire, `check_company` |
| `gest_agri.livestock.species` | idem | — |
| `gest_agri.livestock.breed` | idem | `species_id` obligatoire, `check_company` |
| `gest_agri.operation.type` | idem | — |
| `gest_agri.treatment.type` | idem | — |
| `gest_agri.fertilizer.type` | idem | — |
| `gest_agri.irrigation.type` | idem | — |
| `gest_agri.equipment.type` | idem | — |
| `gest_agri.building.type` | idem | — |
| `gest_agri.production.type` | idem | — |

Portée des référentiels :
- `company_id` **facultatif**, valeur par défaut = société courante ;
- sans société = **global** ;
- avec société = **propre à cette société** ;
- `_check_company_auto = True` partout.

### 5.2 Patrimoine

| Modèle | Champs principaux |
|---|---|
| `gest_agri.farm` | `name`, `code`, `farm_type_id`, `manager_id`, `partner_id`, `company_id`, `analytic_account_id`, `total_area`, `allocated_area` (calculé stocké), `description`, `active`, `sequence`, relations vers sites / parcelles / bâtiments / infrastructures / sources / réseaux / secteurs / pompes / droits d'accès, compteurs et actions de navigation |
| `gest_agri.farm.access` | `farm_id`, `user_id`, `role` (`user` / `manager` / `admin`), `company_id` (lié), `description`, `active` |
| `gest_agri.site` | `name`, `code`, `farm_id`, `company_id` (lié), `description`, `active`, `sequence` |
| `gest_agri.plot` | `name`, `code`, `farm_id`, `site_id`, `area`, `soil_type_id`, `irrigation_type_id`, `ph_min`, `ph_max`, `slope_percent`, `latitude`, `longitude`, `description`, `active`, `sequence` |
| `gest_agri.building` | `name`, `code`, `farm_id`, `site_id`, `building_type_id`, `area` (m²), `capacity`, `description`, `active`, `sequence` |
| `gest_agri.infrastructure` | `name`, `code`, `farm_id`, `site_id`, `infrastructure_kind`, `length_m`, `area`, `description`, `active`, `sequence` |
| `gest_agri.water.source` | `name`, `code`, `farm_id`, `site_id`, `source_type`, `capacity_m3_day`, `depth_m`, `description`, `active`, `sequence` |
| `gest_agri.irrigation.network` | `name`, `code`, `farm_id`, `water_source_id`, `network_type`, `flow_rate_m3_h`, `description`, `active`, `sequence` |
| `gest_agri.irrigation.sector` | `name`, `code`, `network_id`, `farm_id` / `company_id` liés, `area`, `plot_ids` (M2M), `description`, `active`, `sequence` |
| `gest_agri.irrigation.pump` | `name`, `code`, `network_id`, `farm_id` / `company_id` liés, `power_kw`, `flow_rate_m3_h`, `description`, `active`, `sequence` |

Choix de valeur :
- `infrastructure_kind` : `road`, `fence`, `storage`, `drainage`, `other` ;
- `water.source.source_type` : `well`, `borehole`, `spring`, `river`, `pond`, `network`, `other` ;
- `irrigation.network.network_type` : `drip`, `sprinkler`, `gravity`, `pivot`, `other`.

### 5.3 Extension `res.users`

- `gest_agri_farm_ids` : exploitations accessibles (responsable ou accès actif).
- `gest_agri_managed_farm_ids` : exploitations gérables (responsable ou rôle `manager`/`admin`).
- Champs non stockés, `compute_sudo=True`, utilisés par les domaines de sécurité.

---

## 6. Contraintes et règles métier

### 6.1 Référentiels

- Unicité du **code** : insensible à la casse et aux espaces ; un code global entre en conflit avec toutes les sociétés ; un code société entre en conflit avec la même société et les codes globaux.
- Unicité du **nom** : strictement dans la même portée (même société, ou global/global).
- Contraintes Python `@api.constrains` (pas d'index SQL, voir limites).

### 6.2 Exploitation

- `code` obligatoire, unique **par société** (contrainte Python + `models.UniqueIndex` partiel sur `(company_id, UPPER(code)) WHERE active IS TRUE`).
- `total_area ≥ 0`, `allocated_area ≥ 0`.
- `allocated_area` = somme des surfaces des parcelles (champ stocké, `compute_sudo=True`, dépend de `plot_ids.area`, sans récursion).
- `allocated_area ≤ total_area`.
- Cohérence de société sur `farm_type_id` et `analytic_account_id`.
- `manager_id` par défaut = utilisateur courant.
- Hérite de `mail.thread` et `mail.activity.mixin` (chatter).
- Invalidation des caches si `manager_id`, `company_id` ou `active` change.

### 6.3 Droits d'accès

- Un seul accès **actif** par couple exploitation/utilisateur (`models.UniqueIndex` partiel sur `(farm_id, user_id) WHERE active IS TRUE`).
- Rôles : `user`, `manager`, `admin`.
- `company_id` dérivé de l'exploitation et en lecture seule.
- Un non-administrateur ne peut ni créer, ni modifier, ni supprimer **ses propres** droits : `AccessError` ; l'administrateur agricole et le mode sudo le peuvent.
- Toute écriture invalide les caches d'accès et d'ORM.

### 6.4 Patrimoine

- `code` unique **par exploitation** : sites, parcelles, bâtiments, infrastructures, sources d'eau, réseaux, secteurs, pompes.
- Le site d'une parcelle / d'un bâtiment / d'une infrastructure / d'une source d'eau doit appartenir à la **même exploitation**.
- La source d'eau d'un réseau doit appartenir à la **même exploitation**.
- Les parcelles d'un secteur d'irrigation doivent appartenir à la **même exploitation**.
- Contrôles physiques : surfaces, longueurs, capacités, débits, puissance, profondeur ≥ 0 ; pH 0–14 ; pente 0–100 % ; latitude −90–90 ; longitude −180–180.
- `company_id` dérivé de l'exploitation (`related`, `store=True`, `precompute=True`, lecture seule) ; `_check_company_auto = True`.
- Aucune relation vers des modèles de campagne/culture non encore créés.

---

## 7. Sécurité

### 7.1 Groupes

| Groupe XML ID | Libellé | Implication |
|---|---|---|
| `group_gest_agri_user` | Utilisateur agricole | implique `base.group_user` |
| `group_gest_agri_manager` | Responsable agricole | implique `group_gest_agri_user` |
| `group_gest_agri_admin` | Administrateur agricole | implique `group_gest_agri_manager` ; membres par défaut `base.user_root` et `base.user_admin` |

Un privilège `res.groups.privilege` et une catégorie de module (`ir.module.category`) regroupent ces trois groupes.

### 7.2 Matrice `ir.access` (71 lignes)

| Modèle | Utilisateur | Responsable | Administrateur |
|---|---|---|---|
| 13 référentiels | `r` société + global | `cu` société | `crud` société + global |
| `gest_agri.farm` | `r` exploitations accessibles | `c` société, `u` exploitations gérées | `crud` société |
| `gest_agri.farm.access` | `r` ses propres droits | `r` ses droits + exploitations gérées ; `cud` exploitations gérées | `crud` société |
| 8 modèles de patrimoine | `r` exploitations accessibles | `cu` exploitations gérées | `crud` société |

Domaines utilisés :
- portée société : `['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]` ;
- société stricte : `[('company_id', 'in', company_ids)]` ;
- exploitations accessibles : `[('id', 'in', user.gest_agri_farm_ids.ids)]` ;
- exploitations gérées : `[('id', 'in', user.gest_agri_managed_farm_ids.ids)]` ;
- enfants : `[('farm_id', 'in', user.gest_agri_farm_ids.ids)]` / `[('farm_id', 'in', user.gest_agri_managed_farm_ids.ids)]` ;
- droits d'accès : `[('user_id', '=', user.id)]`, ou `['|', ('user_id', '=', user.id), ('farm_id', 'in', user.gest_agri_managed_farm_ids.ids)]`.

### 7.3 Isolation effective côté serveur

L'isolation est appliquée par l'ORM via les domaines `ir.access` (évalués par `safe_eval` avec `user`, `company_ids`, `company_id`), et non seulement par les menus ou les boutons. Les tests vérifient des `read`, `write`, `create` et `unlink` refusés par `AccessError` hors interface.

Invalidation après changement de périmètre (`farm`, `farm.access`) :
`env.invalidate_all()`, `invalidate_access_cache()`, `invalidate_ormcache("default")`, `invalidate_ormcache("stable")`.

### 7.4 Protection des droits d'accès

`_check_self_management()` refuse à tout utilisateur hors administrateur agricole (et hors sudo) la création/modification/suppression de ses propres droits, y compris via des opérations ORM directes.

---

## 8. Vues, actions et menus

### 8.1 Menus

- **Gestion Agricole** (racine)
  - Exploitations → Exploitations, Sites, Parcelles, Bâtiments, Infrastructures, Droits d'accès
  - Production végétale (réservé aux étapes suivantes)
  - Élevage (réservé)
  - Irrigation → Sources d'eau, Réseaux, Secteurs, Pompes
  - Matériel (réservé)
  - Personnel (réservé)
  - Économie (réservé)
  - Configuration → Exploitations, Cultures, Élevage, Interventions, Matériel, Irrigation

### 8.2 Vues

- Une liste, un formulaire et une recherche par modèle (69 vues).
- Listes : colonnes utiles, `sum` sur surfaces/débits, `handle` sur la séquence, `company_id` visible uniquement avec `base.group_multi_company`.
- Formulaires : `web_ribbon` pour les archivés, `oe_title`, groupes, notebook, chatter sur l'exploitation.
- Recherches : filtres Actifs / Archivés, regroupements (société, exploitation, type, rôle, etc.).
- Fiche exploitation : 7 boutons statistiques + onglets vers tout le patrimoine.
- Domaines dynamiques sur les champs dépendants (ex. `site_id` limité à l'exploitation choisie).

Respect des schémas Odoo 20 : `<list>` (pas `<tree>`), `<group>` de recherche sans attribut `expand`/`string`, `<chatter/>`.

---

## 9. Tests

### 9.1 Inventaire des méthodes

**`tests/test_configuration.py` (4 tests)**
- `test_referential_creation`
- `test_code_uniqueness_in_same_scope`
- `test_global_code_conflicts_with_company_code`
- `test_same_code_in_other_company`

**`tests/test_patrimony.py` (9 tests)**
- `test_farm_site_plot_creation`
- `test_full_patrimony_creation`
- `test_farm_code_unique_per_company`
- `test_site_code_unique_per_farm`
- `test_site_must_belong_to_same_farm`
- `test_negative_area_rejected`
- `test_allocated_area_cannot_exceed_total`
- `test_plot_agronomic_ranges`
- `test_company_consistency`

**`tests/test_security.py` (10 tests)**
- `test_farm_isolation`
- `test_child_isolation`
- `test_user_cannot_write_farm`
- `test_user_cannot_create_child`
- `test_manager_can_write_managed_farm`
- `test_manager_can_create_child`
- `test_manager_cannot_edit_own_access`
- `test_admin_can_manage_access`
- `test_plot_write_permissions`
- `test_farm_access_unique_active`

**`tests/test_module_install.py` (1 test existant)**
- `test_module_present`

Total : **24 tests**.

### 9.2 Statut d'exécution

Les tests **n'ont pas été exécutés** : l'installation/mise à jour du module et toute modification de base de données sont interdites dans le cadre de cette étape. Ils sont écrits pour une base de test Odoo 20 avec le module installé.

### 9.3 Validations statiques réalisées

| Contrôle | Résultat |
|---|---|
| `python3 -m compileall` sur tout le module | OK |
| Parsing XML de tous les fichiers | 7/7 OK |
| Validation `odoo/import_xml.rng` | 7/7 VALID |
| Validation RelaxNG `list_view.rng` + `search_view.rng` | 46 vues, 0 erreur |
| Cohérence champs de vues / modèles (analyse AST) | 0 problème |
| Références XML internes (`parent`, `action`, `ref`, `groups`, `%(...)d`) | 0 problème, 135 ids locaux |
| Couverture `ir.access.csv` | 23 modèles métier couverts ; `res.users` volontairement absent (droits natifs) |
| Recherche de syntaxes obsolètes (`ir.rule`, `groups_id`, `<tree>`, `_sql_constraints`, `attrs=`) | 0 occurrence |
| `git status` | aucun changement hors `gestion_agricole/` |

---

## 10. Limites, points d'attention et risques

1. **Tests non exécutés** : seuls des contrôles statiques ont été réalisés.
2. **Unicité des référentiels en Python seul** : pas d'index SQL unique, car la règle global/société ne s'exprime pas simplement en index. Risque théorique de course concurrente.
3. **Référentiels globaux** : autorisés par les domaines d'accès (administrateur uniquement en création/modification), sans règle dure supplémentaire.
4. **Archivage d'une parcelle** : `allocated_area` ne somme que les parcelles actives ; archiver une parcelle libère donc de la surface affectée.
5. **Secteur d'irrigation** : la surface du secteur n'est pas comparée à la somme des surfaces des parcelles desservies.
6. **Cohérence de société** : portée par `check_company` + `_check_company_auto` + contraintes Python, pas par des contraintes SQL.
7. **Menus réservés** (Production végétale, Élevage, Matériel, Personnel, Économie) : présents mais sans entrée métier avant les étapes suivantes.
8. **`res.users`** : pas de lignes `ir.access` dédiées ; les champs calculés sont en `compute_sudo=True`.

---

## 11. Confirmations

- Aucun module installé, mis à jour ou désinstallé.
- Aucun serveur Odoo redémarré.
- Aucune base de données créée, modifiée ou migrée.
- Aucun fichier de configuration Odoo touché.
- Aucun module noyau, ancien module `agriculture_manage_*` ou module tiers modifié.
- Les répertoires `odoo20`, `adoo20` et `odoo2000` n'ont pas été modifiés.
- Seuls des fichiers sous `addons/kantmoh/gestion_agricole/` ont été créés ou modifiés.

---

## 12. État de l'étape

**PROMPT N°4 : terminé — en attente de validation.**

Aucune étape ultérieure ne sera engagée avant validation explicite.
