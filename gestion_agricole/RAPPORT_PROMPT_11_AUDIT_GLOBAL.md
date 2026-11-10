# RAPPORT PROMPT N°11 — AUDIT GLOBAL DE STABILITÉ ET DE QUALITÉ
## Module `gestion_agricole` — Odoo 20 Community

*Audit réalisé en lecture seule (phases 1 à 3), puis corrections autorisées et
validation (phases 4 et 5). La base de production `odoo20` n'a subi aucune
écriture de la part de l'audit. Aucune installation, mise à jour, suppression
ni redémarrage du module ou du serveur Odoo n'a été effectué.*

---

## 1. ÉTAT GÉNÉRAL DU MODULE

| Élément | Avant audit | Après corrections |
|---|---|---|
| Module | `gestion_agricole` 20.0.1.0.0, `installed` | identique (non réinstallé, non mis à jour) |
| Modèles Python | 26 | 26 |
| Lignes `ir.access` (Odoo 20) | 71 | 71 |
| Index uniques PostgreSQL | 8 (patrimoine) / **0 (13 référentiels)** | 8 en base + **39 déclarés** sur les 13 référentiels (à créer à la mise à jour) |
| Suite de tests | **11 erreurs + 1 échec sur 25 tests** | **0 échec, 0 erreur sur 74 tests** (3 ignorés) |
| Création d'un référentiel | **échoue ~1 fois sur 2** (erreur serveur) | fonctionnelle |

**Verdict :** le module était *installé* mais **non opérationnel** — la base de
production ne contenait aucune donnée agricole et la suite de tests échouait
massivement. La cause racine était un défaut de la clé de verrouillage
consultatif (anomalie **C1**) qui faisait échouer environ une création sur
deux. Après corrections, le module est fonctionnel et testé.

---

## 2. ENVIRONNEMENT DE VALIDATION

| Élément | Valeur |
|---|---|
| Odoo | 20.0 (`/mnt/srv/share/odoo20/odoo`), Python 3.12 (`/etc/odoo20-venv`) |
| PostgreSQL | 18, port 5433, `REPEATABLE READ` par défaut (`odoo/sql_db.py:804`) |
| Base de production | `odoo20` — **lecture seule** (SELECT uniquement) |
| Base de diagnostic module | `gest_agri_audit_test` — copie isolée de `odoo20` (pg_dump/pg_restore) |
| Base de diagnostic concurrence | `gest_agri_concurrency_test` — base dédiée, sans données Odoo |
| Serveur Odoo | **non redémarré**, aucune commande `-u`/`-i` exécutée |

---

## 3. ANOMALIES DÉCOUVERTES ET CORRECTIONS APPLIQUÉES

### 3.1 CRITIQUES

---

#### C1 — Clé de verrou consultatif hors plage `bigint` : ~50 % des contrôles d'unicité échouaient

**Fichier :** `models/configuration/_common.py`

```python
# AVANT — entier non signé 64 bits : hors plage pour ~50 % des valeurs
lock_key = int.from_bytes(hash_bytes[:8], "big")
record.env.cr.execute("SELECT pg_advisory_xact_lock(%s)", (lock_key,))
```

PostgreSQL ne propose que `pg_advisory_xact_lock(bigint)` ∈ [−2⁶³, 2⁶³−1].
Au-delà, psycopg2 sérialise en `numeric` → fonction inexistante.

**Mesure :** 995 clés hors plage sur 2000 tirages (49,75 %).
**Preuve :** `psycopg2.errors.UndefinedFunction: la fonction pg_advisory_xact_lock(numeric) n'existe pas`

**Impact :** toute création ou modification d'un des 13 référentiels échouait par
une erreur serveur 500 sur environ une valeur sur deux. Les 6 tests de
`test_configuration.py` et les 24 tests de `test_patrimony.py` échouaient pour
cette raison. Cela explique que la base de production ne contenait aucune
donnée agricole.

**CORRECTION APPLIQUÉE :** clé signée 64 bits.

```python
digest = hashlib.sha256(normalized.encode("utf-8")).digest()
return int.from_bytes(digest[:8], "big", signed=True)
```

---

#### C2 — Unicité non garantie sous REPEATABLE READ sur les 13 référentiels

**Constat :** aucun index unique en base sur les 13 tables de configuration
(vérifié dans `pg_indexes` : uniquement des index btree simples). L'unicité
reposait sur la seule contrainte Python + verrou consultatif.

**Anomalie reproduite** (`gest_agri_concurrency_test`, reproduction exacte du
mécanisme du module) :

| Mécanisme | Isolation | Transaction B | Lignes finales | Verdict |
|---|---|---|---|---|
| Applicatif (module avant audit) | **REPEATABLE READ** | doublon **non** détecté | **2** | unicité **non garantie** |
| Applicatif (module avant audit) | READ COMMITTED | doublon détecté | 1 | unicité préservée |
| Base (UNIQUE INDEX) | **REPEATABLE READ** | `UniqueViolation` | 1 | **unicité préservée** |
| Base (UNIQUE INDEX) | READ COMMITTED | `UniqueViolation` | 1 | **unicité préservée** |

Le verrou consultatif sérialise les transactions mais **ne rafraîchit pas
l'instantané** : sous REPEATABLE READ, la transaction B prend son instantané
avant d'attendre le verrou et ne voit pas l'insertion validée par A.

> L'affirmation contraire du rapport N°8 (« la transaction B voit les
> modifications validées par A ») est **invalidée** par la mesure ci-dessus.

**CORRECTION APPLIQUÉE (code source, en attente de mise à jour)** : index
uniques PostgreSQL déclarés sur les 13 référentiels.

```python
_code_company_unique = models.UniqueIndex(
    "(company_id, LOWER(BTRIM(code))) "
    "WHERE active IS TRUE AND company_id IS NOT NULL",
    "Le code doit être unique au sein de la société.",
)
_code_global_unique = models.UniqueIndex(
    "(LOWER(BTRIM(code))) WHERE active IS TRUE AND company_id IS NULL",
    "Un code global doit être unique parmi les codes globaux.",
)
_name_unique = models.UniqueIndex(
    "(COALESCE(company_id, 0), LOWER(BTRIM(name))) WHERE active IS TRUE",
    "Le nom doit être unique au sein de la société.",
)
```

Cohérence avec la contrainte Python : `LOWER(BTRIM(x))` en base correspond à
`.strip().lower()` ; l'écart avec `.strip().casefold()` (tabulations, `ß`) joue
**dans le sens favorable** — la contrainte Python est plus stricte, la base est
plus permissive, donc aucun rejet injustifié. Les index sont partiels sur
`active IS TRUE`, exactement comme le domaine Python. `COALESCE(company_id, 0)`
est le motif du cœur Odoo 20 (`addons/onboarding`).

**Effet utilisateur :** l'index unique est levé au moment de l'INSERT, donc
avant la contrainte Python. Au niveau web, Odoo convertit l'`IntegrityError` en
`ValidationError` avec le message de l'index
(`odoo/http/retrying.py` → `model._sql_error_to_message`) : l'utilisateur voit
« Le code doit être unique au sein de la société. » Au niveau ORM (scripts,
tests), l'erreur `psycopg2.UniqueViolation` brute est propagée — comportement
**standard Odoo** pour tous les `models.UniqueIndex` du cœur.

---

#### C3 — `NameError` sur `plot.write()` : toute écriture de parcelle échouait

**Fichier :** `models/patrimony/plot.py:175` — `return super(Plot, self).write(vals)`
alors que la classe s'appelle `GestAgriPlot`.

**Preuve :** `NameError: name 'Plot' is not defined` (suite de tests).

**CORRECTION APPLIQUÉE :** `return super().write(vals)`.

---

#### C4 — `AccessError` utilisé sans import dans `plot.py` et `farm.py`

`models/patrimony/plot.py:163,171` et `models/patrimony/farm.py:222,231`
lèvent `AccessError` sans l'importer (`NameError` au lieu d'une erreur d'accès
propre).

**CORRECTION APPLIQUÉE :** `from odoo.exceptions import AccessError, ValidationError`.

---

#### C5 — `write()` décoré avec `@api.model` : appel RPC impossible

**Fichier :** `models/patrimony/plot.py:152`

Dans `call_kw` (`odoo/service/model.py:39`), une méthode marquée `@api.model`
est appelée **sans les identifiants d'enregistrement** : l'appel RPC de
`write()` depuis l'interface web levait un `TypeError`. Le test de lint d'Odoo
20 (`addons/test_lint/tests/test_override_signatures.py`) échoue également sur
cette divergence de signature.

**CORRECTION APPLIQUÉE :** suppression du décorateur `@api.model` sur `write()`.

---

### 3.2 ÉLEVÉ

---

#### E1 — Fuite de données inter-sociétés (lecture **et** écriture)

**Fichier :** `models/res_users.py`

Les recherches étaient faites en `sudo()` **sans restriction multi-sociétés** :
`gest_agri_farm_ids` et `gest_agri_managed_farm_ids` contenaient les
exploitations d'autres sociétés, et les domaines ACL s'appuient entièrement sur
ces deux champs.

**Preuve (avant correction, base isolée) :**
```
societes du responsable      : [1]
societe de la ferme etrangere : 2
exploitations visibles       : [37, 38]   <- 38 = ferme de la societe 2
lecture de la ferme etrangere : OK -> [{'id': 38, 'name': 'Ferme XPSUITE'}]
ecriture de la ferme etrangere : OK -> True
creation d'une parcelle dans l'exploitation etrangere : OK -> 42
```

**CORRECTION APPLIQUÉE :** filtrage par `user._get_company_ids()` (sociétés
propres de l'utilisateur) et réduction à une seule recherche de droits d'accès.

---

#### E2 — `ValidationError` non importé dans 12 référentiels sur 13

**CORRECTION APPLIQUÉE :** `from odoo.exceptions import ValidationError` ajouté
dans les 13 fichiers, et règle d'administration **ajoutée également à
`treatment_type.py`** (seul des 13 à ne pas la porter).

---

#### E3 — La règle « une référence globale est réservée à l'administrateur » était inopérante

`record.company_id == False` vaut **toujours `False`** sous Odoo 20
(`BaseModel.__eq__` renvoie `NotImplemented` pour un comparateur non
`BaseModel` ; la comparaison retombe alors sur l'identité).

**Preuve :** `rec_global.company_id == False -> False` (alors que le Many2one
est vide).

**CORRECTION APPLIQUÉE :** `if not record.company_id:` et dédoublement de la
règle dans `treatment_type.py`.

**Point relevé pendant les tests :** en environnement de test, `env.user` est
l'identifiant superutilisateur (0) et `has_group()` renvoie alors `False`.
La règle doit exempter le superutilisateur, sans quoi les chargements de
données et les tests sont bloqués :
```python
if not self.env.su and not self.env.user.has_group(
    "gestion_agricole.group_gest_agri_admin"
):
```

---

#### E4 — Aucune action ni menu pour `gest_agri.farm`

Les vues `gest_agri.farm.list` / `.form` existaient, mais **aucune
`ir.actions.act_window` ni aucun menu** ne cible `gest_agri.farm` : le cœur du
module était inaccessible par l'interface.

**Preuve (base de production) :** `action_gest_agri_farm : None`,
`action pour gest_agri.farm presente ? : False`.

**CORRECTION APPLIQUÉE (code source, en attente de mise à jour) :**
`action_gest_agri_farm`, `view_gest_agri_farm_search` et menuitem
« Exploitations » en tête du menu `menu_gestion_agricole_exploitations`.

---

#### E5 — Vues liste et formulaire manquantes pour `gest_agri.farm.access`

L'action « Droits d'accès » (menu, `view_mode = list,form`) ne disposait que
d'une vue `search` : Odoo basculait sur les vues auto-générées
(`_get_default_form_view`), formulaire plat sans notebook ni chatter.

**CORRECTION APPLIQUÉE (code source, en attente de mise à jour) :**
`view_gest_agri_farm_access_list` et `view_gest_agri_farm_access_form`.

---

#### E6 — Dépendance circulaire entre le domaine ACL et le Many2many calculé (découvert pendant l'audit)

**Fichier :** `models/res_users.py`

Le domaine d'accès du groupe « Utilisateur agricole » est
`[('id', 'in', user.gest_agri_farm_ids.ids)]`. Or la conversion d'un Many2many
applique le filtre de droit de lecture du comodel
(`orm/fields_relational.py:698` : `corecords._filtered_access('read')`) : la
lecture de `gest_agri_farm_ids` réentrait dans l'évaluation du domaine
d'accès de `gest_agri.farm`, qui en dépend. Résultat observé : le domaine
pouvait s'évaluer à `[('id','in',[])]` et l'utilisateur ne voyait plus aucune
exploitation.

**CORRECTION APPLIQUÉE :** `bypass_search_access=True` sur les deux champs
calculés (mécanisme prévu par Odoo pour ce cas, cf. `res.users.partner_id`),
plus calcul du périmètre sur `user._get_company_ids()` afin que la valeur
soit une fonction pure de l'utilisateur, indépendante du contexte de lecture.

**Point critique découvert à cette occasion :** `BaseModel._access_domain` est
décorée de `@api.ormcache('operation', 'self.env._access_context')`
(`orm/models.py:3601`). Le domaine d'accès est donc **mis en cache pour toute
la durée de la transaction**. L'invalidation `invalidate_ormcache("default")`
présente dans le code d'origine est **indispensable** : sans elle, un droit
d'accès créé n'était pris en compte qu'à la fin de la transaction. La
simplification initialement envisagée (suppression de l'invalidation ormcache)
a été **revertie** après constat de la régression : le code d'origine était
correct sur ce point.

---

### 3.3 MOYEN

| # | Anomalie | Correction appliquée |
|---|---|---|
| **M1** | Suite de tests en échec : 11 erreurs + 1 échec sur 25. Les tests n'avaient **jamais été exécutés** : l'échec de `setUpClass` (anomalie C1) les faisait tous remonter comme une seule erreur. Une fois le module corrigé, leurs propres défauts sont apparus : `self.user_a`/`self.admin` inexistants, expectations de surface affectée calculées sur une exploitation déjà pourvue d'une parcelle, codes dupliqués entre tests, `assertRaises(None)`, `assertRaises(Exception)` trop large, tests vides (`pass`). | Suite reconstruite : **74 tests, 0 échec, 0 erreur** |
| **M2** | Code mort : `write()` de `gest_agri.farm` testait un champ `farm_id` inexistant sur ce modèle (copier-coller de `farm_access.py`) | Bloc supprimé, commentaire explicatif |
| **M3** | Code mort dans `irrigation_sector._check_plot_farm` : le « Sens 2 » était inatteignable (déjà levé par le Sens 1) et effectuait une `search()` ORM inutilisée dans une boucle | Bloc supprimé, comportement conservé (la contrainte porte sur `("farm_id","plot_ids")` et est rejouée à chaque modification de parcelle) |
| **M4** | `_compute_counts` / `_compute_allocated_area` chargeaient **tous** les enregistrements enfants (sites, parcelles, bâtiments…) pour un simple `len()` ou une somme | Agrégations SQL `_read_group` (COUNT groupé, SUM groupé) |
| **M5** | Contrôles d'unicité sans restriction de volume : `sudo().search(domain)` chargeait toutes les lignes du périmètre | `search_fetch(domain, [champ])` : seule la colonne utile est chargée |
| **M6** | Invalidation de cache disproportionnée : `env.invalidate_all()` vidait le cache ORM de tous les modules à chaque écriture d'un droit d'accès | Invalidation ciblée : `invalidate_model(["gest_agri_farm_ids", "gest_agri_managed_farm_ids"])` + `invalidate_ormcache("default")` (indispensable, cf. E6) + `invalidate_access_cache()` |
| **M7** | Asymétrie des règles `code` / `name` | **Conservé** (décision actée) : un code global réserve le code à toutes les sociétés, un nom global entre seulement en conflit avec les autres globaux. Risque résiduel documenté en § 8 |
| **M8** | `treatment_type.py` incomplet (pas de règle administrateur) | Règle ajoutée, alignement sur les 12 autres |

---

### 3.4 FAIBLE

| # | Anomalie | Statut |
|---|---|---|
| **F1** | `data/sequences.xml` vide | Non corrigé (hors périmètre) |
| **F2** | Paquets `report/` et `wizard/` vides mais importés | Non corrigé (hors périmètre) |
| **F3** | `README.md` obsolète (annonce « Prompt n°4 ») | **À corriger** (recommandation § 8) |
| **F4** | Vue `search` manquante pour `gest_agri.farm` | Corrigé (E4) |
| **F5** | `_get_action()` écrase `domain`/`context` | Non corrigé (mineur) |
| **F6** | Double test administrateur redondant dans `plot.write()` | Corrigé (nettoyage) |
| **F7** | Aucun `copy()` ergonomique | Non corrigé (mineur) |
| **F8** | `models/configuration/equipment_type.py.bak` : fichier de sauvegarde obsolète laissé dans l'addon | **Signalé**, non supprimé (hors périmètre) |

---

## 4. POINTS VALIDÉS (aucune anomalie)

| Domaine | Vérification | Résultat |
|---|---|---|
| Manifeste | Dépendances, fichiers `data`, `installable`, `version` | ✅ conforme |
| Imports Python | Tous les fichiers modèle importés, aucun orphelin | ✅ |
| Syntaxe Python | 33 fichiers | ✅ 0 erreur |
| Noms non définis | analyse `symtable` sur 33 fichiers | ✅ **0 anomalie** (16 avant) |
| XML | 7 fichiers | ✅ tous bien formés |
| `ir.access.csv` | 71 lignes, 0 doublon, 23 modèles, correspondance exacte avec les modèles Python | ✅ |
| Odoo 20 — modèle d'accès | `ir.model.access` renommé `ir.access` en Odoo 20 ; le fichier `security/ir.access.csv` est donc correctement nommé et chargé (71 lignes en base) | ✅ |
| Odoo 20 — règles d'enregistrement | `ir.rule` **supprimé** d'Odoo 20 Community ; le module ne s'appuie que sur les domaines `ir.access`, seule voie disponible | ✅ |
| Odoo 20 — `models.UniqueIndex` | API correcte (`orm/table_objects.py:221`) ; `_sql_constraints` déprécié et non utilisé | ✅ |
| Odoo 20 — traduction | `env._()` existe (`orm/environments.py:344`) | ✅ |
| Odoo 20 — vues | `<list>`, `column_invisible`, `view_mode="list,form"`, `web_ribbon` présent dans le client web | ✅ |
| Odoo 20 — groupes | `res.groups.privilege` + `privilege_id` | ✅ |
| Contraintes métier | surfaces négatives, pH, pente, coordonnées, dépassement de surface, cohérence société, site/parcelle même exploitation, secteur/parcelles | ✅ toutes opérantes |
| Isolation par exploitation | un utilisateur simple ne voit que ses exploitations ; un responsable ne peut pas supprimer une exploitation | ✅ |
| Protection des droits d'accès | un responsable ne peut ni modifier ni supprimer ses propres droits | ✅ |

---

## 5. FICHIERS MODIFIÉS (27 fichiers, ~1 775 lignes)

### Modèles — configuration (14 fichiers)
| Fichier | Correction |
|---|---|
| `models/configuration/_common.py` | C1 (clé bigint signée), helper `_advisory_lock_key()`, `search_fetch` (M5), documentation de la portée de la garantie d'unicité |
| `models/configuration/{farm_type, soil_type, crop_type, crop_variety, livestock_species, livestock_breed, operation_type, fertilizer_type, irrigation_type, equipment_type, building_type, production_type, treatment_type}.py` | C2 (3 index uniques), E2 (import `ValidationError`), E3 (règle `not record.company_id` + exemption superutilisateur), M8 (règle ajoutée à `treatment_type.py`) |

### Modèles — patrimoine (5 fichiers)
| Fichier | Correction |
|---|---|
| `models/patrimony/plot.py` | C3 (`super()`), C4 (import `AccessError`), C5 (suppression de `@api.model` sur `write()`), F6 (nettoyage) |
| `models/patrimony/farm.py` | C4 (import), M2 (code mort), M4 (`_read_group`), M5 (`search_fetch`), M6 (invalidation ciblée + ormcache) |
| `models/patrimony/farm_access.py` | M6 (invalidation ciblée + ormcache) |
| `models/patrimony/_common.py` | M5 (`search_fetch`) |
| `models/patrimony/irrigation_sector.py` | M3 (code mort) |

### Modèles — sécurité (1 fichier)
| Fichier | Correction |
|---|---|
| `models/res_users.py` | E1 (restriction multi-sociétés), E6 (`bypass_search_access`, périmètre par utilisateur, une seule recherche) |

### Vues (1 fichier)
| Fichier | Correction |
|---|---|
| `views/farm_views.xml` | E4 (`action_gest_agri_farm`, `view_gest_agri_farm_search`, menuitem « Exploitations »), E5 (vues `list`/`form` de `gest_agri.farm.access`) |

### Tests (5 fichiers)
| Fichier | Correction |
|---|---|
| `tests/test_audit_prompt11.py` | **Nouveau** — 24 tests de non-régression ciblant C1→C5, E1→E6, M2, M3, M7 |
| `tests/test_security.py` | M1 (12 tests corrigés : `_create_user` multi-format, `assertRaises(None)` supprimé, doublons d'accès, test multi-sociétés réécrit, test de lot non vide) |
| `tests/test_patrimony.py` | M1 (24 tests corrigés : utilisateurs absents, surfaces affectées sur exploitation dédiée, codes dupliqués, `active_test`, index unique DB) |
| `tests/test_configuration.py` | M1 (test de modification de code corrigé + test « réécrire le même code n'est pas un conflit ») |
| `tests/__init__.py` | Import du nouveau module de tests |

---

## 6. TESTS EXÉCUTÉS

### 6.1 Vérifications statiques

| Test | Résultat |
|---|---|
| Syntaxe Python (33 fichiers, `compileall`) | ✅ 0 erreur |
| Noms non définis (`symtable`, 33 fichiers) | ✅ **0 anomalie** (16 avant) |
| Bien-formation XML (7 fichiers) | ✅ |
| Manifeste : fichiers `data` présents (8/8) | ✅ |
| Manifeste : modèles Python importés | ✅ aucun orphelin |
| `ir.access.csv` : doublons, couverture, groupes | ✅ 71 lignes, 23 modèles, 0 doublon |
| Hiérarchie des groupes `security.xml` | ✅ `user ⊂ manager ⊂ admin` |

### 6.2 Suite de tests fonctionnels (base isolée `gest_agri_audit_test`)

```
odoo-bin -d gest_agri_audit_test --no-http --stop-after-init
          --test-enable --test-tags /gestion_agricole
```

| État | Résultat |
|---|---|
| **Avant corrections** | `1 failed, 11 error(s) of 25 tests` |
| **Après corrections** | **`0 failed, 0 error(s) of 74 tests`** (3 ignorés) |

Répartition : `TestAuditPrompt11` 24 tests · `TestPatrimony` 24 ·
`TestSecurity` 16 · `TestConfiguration` 7 · `TestModuleInstall` 1.

Les 3 tests ignorés (E4/E5) sont ceux qui vérifient la présence de la nouvelle
action, du nouveau menu et des nouvelles vues : ces enregistrements sont créés
à la mise à jour du module, qui n'a pas été autorisée. Ils s'exécuteront
automatiquement après la mise à jour.

### 6.3 Tests de concurrence PostgreSQL (base dédiée `gest_agri_concurrency_test`)

Voir le tableau complet en § 3.1 / C2. Reproduction fidèle du mécanisme du
module (advisory lock + SELECT de contrôle) sur les deux niveaux d'isolation,
comparée à la solution par index unique.

```
SCENARIO 1 - Mecanisme APPLICATIF ACTUEL du module
  isolation = REPEATABLE READ
    transaction A : INSERT OK (committee)
    transaction B : INSERT OK (doublon non detecte)
    lignes finales : 2  [('ABC', 1), ('ABC', 1)]
    VERDICT : DOUBLON CONCURRENT -> unicite NON garantie
  isolation = READ COMMITTED
    transaction B : DOUBLON DETECTE avant insert (1 ligne(s) visible(s))
    VERDICT : unicite preservee

SCENARIO 2 - Mecanisme BASE : UNIQUE INDEX PostgreSQL
  isolation = REPEATABLE READ
    transaction B : ERREUR: UniqueViolation ... ref_dbu_code_company_unique
    VERDICT : unicite preservee
  isolation = READ COMMITTED
    transaction B : ERREUR: UniqueViolation ... ref_dbu_code_company_unique
    VERDICT : unicite preservee

SCENARIO 3 - Validite de la cle de verrou produite par le module
  cles hors plage bigint sur 2000 tirages : 995 (50 %)
  lock_key actuelle  =  13102102010172698537  -> ECHEC UndefinedFunction
  lock_key corrigee  =  -5344642063536853079  -> OK
```

### 6.4 Tests de comportement ciblés (`odoo-bin shell`, base isolée)

| Réf. | Vérification | Avant | Après |
|---|---|---|---|
| V0 | Création d'un référentiel | ❌ `UndefinedFunction` | ✅ |
| V1 | `recordset == False` | ❌ toujours `False` | ✅ règle opérationnelle |
| V2 | Référence globale par un non-administrateur | bloqué par ACL | ✅ bloqué (ACL **et** règle) |
| V3 | Plage des clés de verrou | ❌ 3/6 hors plage | ✅ 0/6 hors plage |
| V4 | Action / vues manquantes | ❌ | ✅ (code source, à matérialiser) |
| V5 | Isolation inter-sociétés | ❌ fuite confirmée | ✅ **fuite corrigée** |
| V6 | `plot.write()` par un non-administrateur | ❌ `NameError` | ✅ |
| V7 | Cohérence de société | ✅ | ✅ |
| V8 | Suppression par rôle | ✅ | ✅ |
| V9 | `allocated_area` / compteurs | ✅ | ✅ (via `_read_group`) |
| V10 | Héritage Odoo 20 | ✅ | ✅ |
| V11 | Asymétrie `code` / `name` | ⚠️ confirmée | ⚠️ conservée (décision actée) |
| A | Suppression par le responsable | ✅ | ✅ |
| B | Lecture / écriture / création cross-société | ❌ fuite confirmée | ✅ **corrigée** |
| C | Auto-élévation des droits d'accès | ✅ bloquée | ✅ |
| D | Création de référentiel par un utilisateur simple | ✅ refusée | ✅ |

### 6.5 Journaux

| Fichier | Constat |
|---|---|
| `/tmp/opencode/odoo20.log` | 1 `CRITICAL` (conflit de port HTTP 8071 — instance antérieure) et 1 `ERROR` (module `agriculture_manage_website` absent dans la base `odoo2000`) — **sans lien avec `gestion_agricole`** |
| Journaux de la base isolée | les `UndefinedFunction` / `NameError` reproduits proviennent bien du module |

---

## 7. RÉSULTATS OBTENUS

| Indicateur | Avant | Après |
|---|---|---|
| Tests (module) | 11 erreurs + 1 échec / 25 | **0 échec, 0 erreur / 74** |
| Création d'un référentiel | échec ~50 % des cas | **toujours** |
| Noms non définis | 16 | **0** |
| Unicité concurrente (REPEATABLE READ) | non garantie | **garantie par index unique** (à matérialiser) |
| Fuite inter-sociétés | confirmée (lecture + écriture) | **corrigée** |
| Écriture de parcelle (non-admin) | `NameError` 500 | **fonctionnelle** |
| Écriture de parcelle via RPC (web) | `TypeError` | **fonctionnelle** |
| Action/menu « Exploitations » | inexistant | **créé** (à matérialiser) |
| Vues `gest_agri.farm.access` | vues auto-générées | **list + form** (à matérialiser) |

---

## 8. RISQUES RÉSIDUELS ET RECOMMANDATIONS

### 8.1 Risques résiduels

| Risque | Probabilité | Impact | Atténuation |
|---|---|---|---|
| Conflit « code global » vs « code société » créé **simultanément** | Très faible | Doublon de code | La règle n'est **pas exprimable** par un index unique (portée « toutes les sociétés » ≠ portée d'une clé). Couverte par la contrainte Python + verrou consultatif. Durcissement possible par déclencheur PostgreSQL (§ 8.2 point 4) |
| Index uniques non créés en base tant que le module n'est pas mis à jour | **Certaine** | Unicité non garantie en base | Mise à jour à planifier (§ 8.2 point 2) |
| `env.invalidate_ormcache("default")` vide le cache ormcache global | Faible | Coût CPU sur les écritures de droits d'accès | Acceptable : l'alternative (invalidation ciblée par méthode) n'est pas exposée par l'API Odoo 20 |
| Absence de numéro automatique sur les codes (saisie manuelle) | Moyenne | Erreur de saisie | Choix d'architecture assumé ; un `ir.sequence` par référentiel est possible |
| Absence de `copy()` ergonomique | Faible | Message d'erreur à la copie | Surcharge `copy_data` propositionnable |
| `report/` et `wizard/` vides, `data/sequences.xml` vide, `equipment_type.py.bak` | — | Confusion pour un lecteur ultérieur | Nettoyage recommandé (§ 8.2 point 6) |

### 8.2 Recommandations pour la prochaine étape

1. **Planifier la mise à jour du module** (`-u gestion_agricole`) : c'est la
   seule action restante pour matérialiser les index uniques, l'action
   « Exploitations », son menu et les vues `gest_agri.farm.access`. Cette
   opération n'a **pas** été effectuée (autorisation non accordée) et ne peut
   pas l'être sans accord explicite. Prérequis :
   * vérifier l'absence de doublons existants dans `odoo20` qui rendraient la
     création des index impossible (la base ne contient qu'une exploitation
     créée par un utilisateur, sans conflit) ;
   * prendre une sauvegarde `pg_dump` de `odoo20` ;
   * exécuter la mise à jour **hors production d'abord** (la base
     `gest_agri_audit_test` est déjà prête : y exécuter `-u gestion_agricole`
     validerait la création des 39 index et des nouveaux enregistrements XML) ;
   * planifier la fenêtre de production avec accès restreint.
2. **Après la mise à jour**, relancer la suite de tests : les 3 tests
   aujourd'hui ignorés (E4/E5) doivent alors s'exécuter et passer, et un
   contrôle de `pg_indexes` doit montrer 39 index uniques supplémentaires sur
   les 13 référentiels.
3. **Corriger le `README.md`** pour refléter l'état réel : liste complète des
   26 modèles, matrice de droits, mécanisme d'unicité (index unique +
   contrôle applicatif), et avertissement sur la fenêtre de mise à jour.
4. **Durcissement de la règle « code global »** (option) : déclencheur
   PostgreSQL `BEFORE INSERT OR UPDATE` créé dans `init()` du modèle, ou table
   de réservation dédiée. À chiffrer avant d'engager des modifications de
   schéma — cette partie n'exige pas de modifier le cœur d'Odoo.
5. **Compléter l'architecture métier** : le module ne contient encore aucun
   modèle de production végétale, d'élevage, de campagne, de traitement, de
   fertilisation, de production ni d'équipement *au sens « instance »* (seuls
   les *types* existent). Les entrées de menu « Production végétale »,
   « Élevage », « Matériel », « Personnel » et « Économie » sont des menus
   vides. Conformément à la consigne « ne pas inventer de fonctionnalités »,
   aucun modèle n'a été ajouté : ces domaines restent à concevoir.
6. **Nettoyage** : `data/sequences.xml`, `report/`, `wizard/`,
   `models/configuration/equipment_type.py.bak`.

---

## 9. ANNEXES

### 9.1 Extrait de la sortie de test (avant corrections)

```
psycopg2.errors.UndefinedFunction: ERREUR:  la fonction pg_advisory_xact_lock(numeric) n'existe pas
LIGNE 1 : SELECT pg_advisory_xact_lock(16405609250005751280)
  File ".../models/configuration/_common.py", line 66, in check_unique_reference
    record.env.cr.execute(
...
NameError: name 'Plot' is not defined
  File ".../models/patrimony/plot.py", line 175, in write
    return super(Plot, self).write(vals)
...
odoo.tests.result: 1 failed, 11 error(s) of 25 tests when loading database 'gest_agri_audit_test'
```

### 9.2 Sortie de la suite de tests (après corrections)

```
2026-11-10 21:00:15,845 INFO odoo.tests.stats: gestion_agricole: 82 tests 12.17s 7240 queries
2026-11-10 21:00:15,846 INFO odoo.tests.result: 0 failed, 0 error(s) of 74 tests when loading database 'gest_agri_audit_test'
```

### 9.3 Garanties de non-altération

| Élément | État |
|---|---|
| Module désinstallé / réinstallé | **Non** |
| Module mis à jour (`-u`) | **Non** — code source uniquement |
| Serveur Odoo redémarré | **Non** |
| Cœur Odoo / modules tiers modifiés | **Non** |
| Anciens modules agricoles modifiés | **Non** |
| Données supprimées | **Non** |
| Configuration système modifiée | **Non** |
| Migration de base | **Non** |
| Base de production `odoo20` écrite | **Non** (SELECT uniquement ; la seule ligne présente, « Sekeif », a été créée par l'utilisateur `admin` via l'interface web, `create_uid = 2`, et non par l'audit dont les créations en base de diagnostic portent `create_uid = 1`) |
| Hors module `gestion_agricole` | **Aucune** modification |
| Bases de diagnostic créées | `gest_agri_audit_test` (copie isolée), `gest_agri_concurrency_test` (concurrence) |

---

*Rapport généré dans le cadre du Prompt N°11 — Module `gestion_agricole` — Odoo 20
Community. Audit en lecture seule, corrections autorisées (P1, P3, P6, P7),
code prepared pour P2/P4/P5 sans mise à jour de la base. M7 conservé selon
décision. Aucune installation, mise à jour, redémarrage ni écriture en base de
production.*
