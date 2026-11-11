# RAPPORT PROMPT N°50 — CRÉATION DU MODÈLE DES CULTURES IMPLANTÉES

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. ANALYSE PRÉALABLE DE L'EXISTANT

Vérifications effectuées avant toute modification :

| Élément | Constat |
|---|---|
| `gest_agri.plot` | `farm_id` requis, `site_id` optionnel, `company_id` related stocké, `area`, `crop_type_id` statique |
| `gest_agri.crop.type` | Référentiel avec `crop_cycle` (`annual`/`perennial`) |
| `gest_agri.crop.variety` | `crop_type_id` **requis** → point d'appui pour la cohérence variété/type |
| ACL de `gest_agri.plot` | 3 règles : user `r` sur `user.gest_agri_farm_ids`, manager `cu` sur `gest_agri_managed_farm_ids`, admin `crud` sur `company_ids` |
| `security/security.xml` | Uniquement les 3 groupes ; **aucune règle d'enregistrement** (`ir.rule`) |
| `data/sequences.xml` | Vide, réservé aux futures séquences |
| Manifeste | 7 fichiers de données, ajout d'une vue nécessaire |
| `models.UniqueIndex` | Déjà utilisé (`plot`, `crop.type`, `crop.variety`, `farm.access`) |
| Réservation | `ReferenceReservationMixin` existant, inerte sans `btree_gist` |
| Notebook parcelle | Un seul onglet « Notes internes » |
| Menu « Production végétale » | Existant mais vide |

Aucun modèle campagne, intervention ou récolte n'existe. Aucun champ équivalent à
une culture implantée n'est présent.

**`plot.crop_type_id` n'a pas été modifié** : il conserve son sens de
caractéristique statique.

---

# 2. MODÈLE CRÉÉ

## `gest_agri.crop.cycle` — « Culture implantée »

Fichier : `models/production/crop_cycle.py`
Héritage : `mail.thread` (suivi des changements d'état, **sans** `mail.activity.mixin`).
Ordre : `date_start desc, id desc`. `_check_company_auto = True`.

| Champ | Type | Propriétés |
|---|---|---|
| `name` | Char | requis, `copy=False`, indexé, séquence automatique |
| `sequence` | Integer | défaut 10 |
| `active` | Boolean | défaut `True` |
| `plot_id` | M2o `gest_agri.plot` | requis, indexé, `ondelete="restrict"` |
| `farm_id` | M2o `gest_agri.farm` | related `plot_id.farm_id`, stocké, lecture seule, `precompute=True`, indexé |
| `site_id` | M2o `gest_agri.site` | related `plot_id.site_id`, stocké, lecture seule, indexé |
| `company_id` | M2o `res.company` | related `plot_id.company_id`, stocké, lecture seule, `precompute=True`, indexé |
| `crop_type_id` | M2o `gest_agri.crop.type` | requis, `check_company=True`, restreint, indexé |
| `crop_variety_id` | M2o `gest_agri.crop.variety` | facultatif, `check_company=True`, restreint, indexé, domaine dynamique |
| `date_start` | Date | requis |
| `date_end_planned` | Date | facultatif |
| `date_end_actual` | Date | facultatif, obligatoire pour `done` |
| `area_ha` | Float (16,2) | défaut 0, initialisé depuis la parcelle, strictement positif |
| `state` | Selection | 5 états, requis, indexé, `tracking=True`, `copy=False` |
| `notes` | Text | facultatif |

---

# 3. SÉQUENCE ET RÉFÉRENCES

Séquence `ir.sequence` créée dans `data/sequences.xml` :

| Paramètre | Valeur |
|---|---|
| Code | `gest_agri.crop.cycle` |
| Nom | Culture implantée |
| Préfixe | `CUL/%(year)s/` |
| Padding | 5 |
| Implémentation | `standard` |

Format obtenu : `CUL/2026/00001`.

La référence est attribuée dans `create()` (surcharge `@api.model_create_multi`)
lorsque `name` est absent, ce qui couvre la création UI **et** la création par
code. Si la séquence est introuvable, un `UserError` explicite est levé : aucune
référence vide ni générique commune n'est possible. `copy=False` garantit qu'une
duplication réattribue une nouvelle référence.

Vérification en base : séquence présente avec `prefix = CUL/%(year)s/`,
`padding = 5`, `implementation = standard`. Aucune séquence existante écrasée.

---

# 4. CONTRAINTES DE DATES ET DE SURFACE

## Dates
- `date_end_planned >= date_start` si les deux sont renseignées.
- `date_end_actual >= date_start` si les deux sont renseignées.
- Aucune relation imposée entre fin prévue et fin réelle.
- `done` exige `date_end_actual` : contrôlé à la fois par `action_done()`
  (`UserError` explicite) et par `@api.constrains("state", "date_end_actual")`
  (protection contre tout autre chemin d'écriture).

## Surface
- Initialisation : `create()` renseigne `area_ha = plot.area` si la clé est
  absente ; `@api.onchange("plot_id")` fait de même dans l'interface lorsque la
  surface est vide.
- Aucun calcul permanent : une surface partielle saisie n'est jamais écrasée.
- Contrainte : `0 < area_ha <= plot_id.area` (message indiquant la surface de la
  parcelle).
- Un changement de parcelle vers une parcelle plus petite déclenche la
  contrainte et impose une correction.

---

# 5. RÈGLE DE CHEVAUCHEMENT

## Intervalle
Début : `date_start`. Fin effective :
`date_end_actual or date_end_planned or +infini`. **Intervalles inclusifs.**

## Contrôle Python
`@api.constrains("plot_id", "date_start", "date_end_planned", "date_end_actual", "state", "active")`
→ `_check_overlap`.

Pour chaque culture non annulée, recherche (en `sudo`, `active_test=False`) des
cultures de la même parcelle non annulées dont `date_start <= fin`, puis
vérification `début <= fin_autre`. Le message identifie la parcelle, la culture
conflictuelle et sa période.

Comportements validés :

| Cas | Résultat |
|---|---|
| Chevauchement partiel | refusé |
| Même jour de début | refusé (index unique et/ou contrainte) |
| Dates qui se touchent le même jour | refusé (inclusif) |
| Succession sans jour commun | accepté |
| Culture précédente sans date de fin | bloque toute culture suivante |
| Succession après la fin réelle | acceptée |
| Culture `cancelled` | exclue du contrôle |
| Culture `active = False` | **continue de bloquer** |
| Modification de date | contrôlée |
| Modification de parcelle | contrôlée |
| Réactivation d'un cycle archivé | contrôlée |
| Réactivation d'un cycle annulé (`action_reset`) | contrôlée |

## Index PostgreSQL
`models.UniqueIndex` :

```sql
CREATE UNIQUE INDEX gest_agri_crop_cycle_plot_start_unique
ON gest_agri_crop_cycle (plot_id, date_start)
WHERE state <> 'cancelled';
```

Index effectivement présent en base.

---

# 6. LIMITE DE CONCURRENCE

**Cette solution ne constitue pas une garantie d'intégrité concurrente absolue.**

- L'index unique garantit seulement l'unicité de `(plot_id, date_start)` pour les
  cultures non annulées, y compris sous transactions concurrentes.
- Deux transactions simultanées créant des intervalles chevauchants avec des
  dates de début **différentes** peuvent toutes deux être validées : la
  contrainte Python ne voit pas les écritures non encore validées de l'autre
  transaction.
- La contrainte d'exclusion PostgreSQL `EXCLUDE USING gist` apporterait la
  garantie forte, mais elle nécessite `btree_gist`.
- `btree_gist` **n'a pas été installé** (vérifié : extensions présentes =
  `plpgsql`, `pg_trgm` uniquement). Aucune contrainte dépendante n'a été créée.
- Cette limite reste documentée comme décision différée (D1 / INF-10).

---

# 7. ÉTATS ET TRANSITIONS RÉELLEMENT IMPLÉMENTÉS

| État | Libellé |
|---|---|
| `planned` | Prévue (défaut) |
| `planted` | Implantée |
| `in_progress` | En cours |
| `done` | Terminée (terminal) |
| `cancelled` | Annulée |

| Bouton | Méthode | Transition | Condition |
|---|---|---|---|
| Implanter | `action_plant` | `planned` → `planted` | — |
| Démarrer | `action_start` | `planted` → `in_progress` | — |
| Terminer | `action_done` | `in_progress` → `done` | `date_end_actual` requise |
| Annuler | `action_cancel` | `planned`/`planted`/`in_progress` → `cancelled` | — |
| Réinitialiser | `action_reset` | `cancelled` → `planned` | responsable ou administrateur |

Protection : `write()` refuse toute modification de `state` hors du contexte
interne `gest_agri_state_transition` → `AccessError`. Les boutons passent par
`_apply_state()`. Aucune transition supplémentaire n'a été ajoutée.

---

# 8. MODIFICATIONS DU MODÈLE PARCELLE

- Ajout de `crop_cycle_ids = One2many("gest_agri.crop.cycle", "plot_id")`.
- Ajout d'un onglet **« Cultures »** dans le formulaire parcelle, avec : référence,
  type, variété, début, fin prévue, fin réelle, surface, état. Les lignes ouvrent
  le formulaire détaillé.
- **Aucune** modification de `crop_type_id`, des états, des surfaces, des calculs
  d'exploitation ni des contraintes existantes.

---

# 9. VUES CRÉÉES ET MENU

Fichier `views/production_views.xml` :

- **Liste** : référence, exploitation, site, parcelle, type, variété, début, fin
  prévue, surface (total), état, société (multi-société).
- **Formulaire** : en-tête avec 5 boutons et barre d'état ; groupes
  « Identification », « Parcelle et exploitation », « Culture et variété »,
  « Période », « Surface » ; onglet « Notes internes » ; ruban « Archivé ».
- **Recherche** : référence, parcelle, exploitation, type, variété ; filtres des
  5 états ; « Cycles actifs » / « Cycles archivés » (distincts de `cancelled`) ;
  regroupements exploitation, parcelle, type de culture, état.
- **Action fenêtre** et menu **« Cultures implantées »** sous « Production
  végétale » (vérifié en base : parent = Production végétale).

Les trois vues et le formulaire parcelle ont été chargés et compilés avec succès
via `get_views` (aucune erreur d'expression de domaine ou de visibilité).

---

# 10. ACL ET RÈGLES D'ENREGISTREMENT

Trois lignes ajoutées à `security/ir.access.csv` :

| Groupe | Opérations | Domaine |
|---|---|---|
| `group_gest_agri_user` | `r` | `[('farm_id', 'in', user.gest_agri_farm_ids.ids)]` |
| `group_gest_agri_manager` | `cu` | `[('farm_id', 'in', user.gest_agri_managed_farm_ids.ids)]` |
| `group_gest_agri_admin` | `crud` | `[('company_id', 'in', company_ids)]` |

Conventions reprises à l'identique de `gest_agri.plot`. Aucune règle `ir.rule`
supplémentaire (le module n'en utilise pas). Aucune ACL d'un autre modèle
modifiée, aucun groupe modifié.

Vérification en base : les 3 règles sont présentes avec les domaines attendus.

---

# 11. TESTS AJOUTÉS ET RÉSULTATS INDIVIDUELS

Fichier `tests/test_crop_cycle.py` — **36 tests, tous exécutés et tous réussis**.

| # | Test | Résultat |
|---|---|---|
| 1 | `test_create_minimal_cycle` | ✅ |
| 2 | `test_reference_generated_and_unique` | ✅ |
| 3 | `test_area_initialized_from_plot` | ✅ |
| 4 | `test_area_partial_modification` | ✅ |
| 5 | `test_area_zero_or_negative_rejected` | ✅ |
| 6 | `test_area_exceeding_plot_rejected` | ✅ |
| 7 | `test_variety_from_other_type_rejected` | ✅ |
| 8 | `test_onchange_clears_incompatible_variety` | ✅ |
| 9 | `test_dates_consistent_accepted` | ✅ |
| 10 | `test_planned_end_before_start_rejected` | ✅ |
| 11 | `test_actual_end_before_start_rejected` | ✅ |
| 12 | `test_done_without_actual_end_rejected` | ✅ |
| 13 | `test_done_with_actual_end_accepted` | ✅ |
| 14 | `test_partial_overlap_rejected` | ✅ |
| 15 | `test_same_start_day_rejected` | ✅ |
| 16 | `test_touching_on_same_day_rejected` | ✅ |
| 17 | `test_successive_without_common_day_accepted` | ✅ |
| 18 | `test_previous_without_end_blocks` | ✅ |
| 19 | `test_succession_after_effective_actual_end` | ✅ |
| 20 | `test_cancelled_cycle_excluded_from_overlap` | ✅ |
| 21 | `test_archived_cycle_still_blocks` | ✅ |
| 22 | `test_overlap_checked_on_date_change` | ✅ |
| 23 | `test_overlap_checked_on_plot_change` | ✅ |
| 24 | `test_reactivation_checks_overlap` | ✅ |
| 25 | `test_reset_cancelled_cycle_checks_overlap` | ✅ |
| 26 | `test_allowed_transitions` | ✅ |
| 27 | `test_forbidden_transitions` | ✅ |
| 28 | `test_direct_state_write_rejected` | ✅ |
| 29 | `test_cancelled_reset_by_manager` | ✅ |
| 30 | `test_cancelled_reset_forbidden_for_user` | ✅ |
| 31 | `test_farm_isolation` | ✅ |
| 32 | `test_multi_company_isolation` | ✅ |
| 33 | `test_user_can_read_accessible_cycle` | ✅ |
| 34 | `test_manager_can_create_and_write_on_managed_farm` | ✅ |
| 35 | `test_admin_can_manage_cycle` | ✅ |
| 36 | `test_user_cannot_create_write_or_unlink` | ✅ |

Preuve : les 36 tests apparaissent en « Starting TestCropCycle.* » et **aucun**
n'apparaît en `ERROR` ou `FAIL`.

---

# 12. FICHIERS MODIFIÉS / CRÉÉS

| Fichier | Nature |
|---|---|
| `models/production/crop_cycle.py` | **créé** |
| `models/production/__init__.py` | **créé** |
| `models/__init__.py` | modifié (import production) |
| `models/patrimony/plot.py` | modifié (`crop_cycle_ids`) |
| `views/production_views.xml` | **créé** |
| `views/patrimony_views.xml` | modifié (onglet Cultures) |
| `data/sequences.xml` | modifié (séquence) |
| `security/ir.access.csv` | modifié (3 ACL) |
| `tests/test_crop_cycle.py` | **créé** |
| `tests/__init__.py` | modifié |
| `__manifest__.py` | modifié (vue production) |

---

# 13. VÉRIFICATION DE RÉPLICATION

Copie de développement : `/tmp/opencode/dev/gestion_agricole/`
Module chargé : `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/`

`diff -q` sur chacun des 11 fichiers : identiques.
`diff -qr` global (hors `__pycache__`, rapports et cahier des charges) : aucune
différence.

---

# 14. RÉSULTAT DE LA MISE À JOUR ODOO

Vérifications préalables : base `odoo20`, utilisateur PostgreSQL `odoo20`, port
5433, module `gestion_agricole` `installed`, exécution autonome sans HTTP ni cron.

```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 \
         --stop-after-init -u gestion_agricole
```

**Résultat : EXIT=0.**

Contrôles en base après mise à jour :

| Contrôle | Résultat |
|---|---|
| Table `gest_agri_crop_cycle` | créée |
| Index unique partiel | présent, `WHERE state <> 'cancelled'` |
| Séquence | `CUL/%(year)s/`, padding 5 |
| ACL | 3 règles conformes |
| Vues | form, list, search présentes |
| Onglet Cultures sur la parcelle | présent |
| Menu | « Cultures implantées » sous « Production végétale » |
| Module | `installed` |

---

# 15. RÉSULTATS COMPLETS DES TESTS

Commande :

```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 \
         --stop-after-init --test-enable --test-tags /gestion_agricole \
         --log-level=test
```

Résultat global :

```
0 failed, 27 error(s) of 160 tests when loading database 'odoo20'
```

| Catégorie | Nombre |
|---|---|
| Tests exécutés | 160 |
| Réussis (`passed`) | **133** |
| Échoués (`failed`) | **0** |
| En erreur (`errors`) | **27** |
| Dont nouveaux tests Prompt 50 | **36 / 36 réussis** |

Les 27 erreurs sont **exactement** les mêmes qu'avant ce prompt (comparaison
nom par nom avec le run du Prompt 48 : ensembles identiques) :
`TestReservationUnicity` (26) et `TestAuditPrompt11` (1), dues à l'absence de
`gest_agri_reference_reservation` / `btree_gist`. Aucune erreur liée au modèle
`gest_agri.crop.cycle`.

---

# 16. CONFIRMATION D'ABSENCE DE MODIFICATION EXTERNE

- Seule la base `odoo20` a été mise à jour ; aucune autre base touchée.
- `/etc/odoo20.conf` non modifié.
- Rôles et permissions PostgreSQL non modifiés.
- Aucun service Odoo partagé redémarré.
- Odoo 16 non touché.
- Aucun autre module modifié.
- `btree_gist` non installé, aucune extension ajoutée.
- Aucun modèle campagne, intervention ou récolte créé ; aucun `campaign_id`.
- `plot.crop_type_id` inchangé ; aucune culture secondaire ; aucune rotation
  automatique.
- Aucune mise à jour globale de tous les modules.

---

# 17. DIFFICULTÉS RENCONTRÉES ET CORRECTIONS

| Difficulté | Traitement |
|---|---|
| Initialisation de `area_ha` sans écraser une saisie partielle | `create()` ne renseigne la surface que si la clé est absente ; l'onchange ne l'initialise que si elle est vide ; aucun champ calculé stocké |
| Contournement possible des transitions par écriture directe de `state` | Garde dans `write()` + contexte interne réservé aux boutons |
| `done` sans date réelle possible par création/écriture directe | Double protection : `action_done()` + contrainte `state`/`date_end_actual` |
| Cycles archivés à inclure dans le contrôle | Recherche en `sudo().with_context(active_test=False)` |
| Index unique pouvant masquer le message métier sur même date de début | Test acceptant `ValidationError` **ou** `UniqueViolation`, comme les conventions existantes du module |

Aucune correction n'a été nécessaire après le premier passage des tests : les 36
nouveaux tests ont réussi dès la première exécution complète.

---

*Rapport — Prompt N°50 — Module `gestion_agricole` — Odoo 20 Community.
Treizième évolution fonctionnelle. Première brique opérationnelle de production
végétale, développée dans la copie de travail, répliquée et testée sur `odoo20`.*
