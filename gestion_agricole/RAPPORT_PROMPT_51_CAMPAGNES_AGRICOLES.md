# RAPPORT PROMPT N°51 — CAMPAGNES AGRICOLES

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. RÉSUMÉ DES RÉALISATIONS

- Création du modèle **`gest_agri.crop.campaign`** (« Campagne agricole »).
- Génération automatique du code `CAM/AAAA/00001` par séquence Odoo.
- Quatre états avec transitions explicites par boutons : `draft`, `active`,
  `closed`, `cancelled` ; `closed` et `cancelled` terminaux.
- Contrôles de dates, clôture conditionnée à la date réelle, verrouillage des
  données métier après clôture ou annulation.
- Société dérivée de l'exploitation (cohérence structurelle).
- Relation inverse `farm.crop_campaign_ids`.
- Vues liste, formulaire, recherche ; action et menu « Campagnes agricoles »
  sous « Production végétale ».
- 3 ACL conformes aux conventions du module.
- **25 tests dédiés, tous réussis.**
- `gest_agri.crop.cycle` **non modifié** (aucun `campaign_id`).

---

# 2. FICHIERS CRÉÉS OU MODIFIÉS

| Fichier | Nature |
|---|---|
| `models/production/crop_campaign.py` | **créé** |
| `models/production/__init__.py` | modifié (import) |
| `models/patrimony/farm.py` | modifié (`crop_campaign_ids`) |
| `views/production_views.xml` | modifié (3 vues, action, menu) |
| `data/sequences.xml` | modifié (séquence campagne) |
| `security/ir.access.csv` | modifié (3 ACL) |
| `tests/test_crop_campaign.py` | **créé** |
| `tests/__init__.py` | modifié |

Aucun autre fichier touché.

---

# 3. MODÈLE ET CHAMPS

## `gest_agri.crop.campaign` — Campagne agricole

Héritage : `mail.thread` (suivi de l'état). Ordre : `date_start desc, id desc`.
`_check_company_auto = True`.

| Champ | Type | Propriétés |
|---|---|---|
| `name` | Char | requis, indexé |
| `code` | Char | requis, `copy=False`, indexé, généré automatiquement |
| `farm_id` | M2o `gest_agri.farm` | requis, `ondelete="cascade"`, `check_company`, indexé |
| `company_id` | M2o `res.company` | related `farm_id.company_id`, stocké, lecture seule, `precompute=True`, indexé |
| `date_start` | Date | requis |
| `date_end` | Date | facultatif |
| `date_end_actual` | Date | facultatif, requis pour clôturer |
| `state` | Selection | requis, défaut `draft`, indexé, `tracking=True`, `copy=False` |
| `description` | Text | facultatif |
| `notes` | Text | facultatif |
| `active` | Boolean | défaut `True` |
| `sequence` | Integer | défaut 10 |

Contrainte SQL : index unique `UPPER(BTRIM(code))` (unicité globale du code,
archives comprises) + contrainte Python pour le message utilisateur.

---

# 4. ÉTATS ET TRANSITIONS

| État | Libellé |
|---|---|
| `draft` | Brouillon (initial) |
| `active` | En cours |
| `closed` | Clôturée (terminal) |
| `cancelled` | Annulée (terminal) |

| Bouton | Méthode | Transition | Condition |
|---|---|---|---|
| Démarrer | `action_activate` | `draft` → `active` | — |
| Clôturer | `action_close` | `active` → `closed` | `date_end_actual` requise |
| Annuler | `action_cancel` | `draft` ou `active` → `cancelled` | — |

- Toute écriture directe de `state` hors contexte interne lève `AccessError`.
- Aucune réactivation d'une campagne clôturée ou annulée.
- Plusieurs campagnes `active` simultanées sont autorisées (aucune règle de
  chevauchement).

---

# 5. CONTRAINTES MÉTIER IMPLÉMENTÉES

1. `date_end >= date_start` lorsqu'elle est renseignée.
2. `date_end_actual >= date_start` lorsqu'elle est renseignée.
3. `closed` exige `date_end_actual` : contrôle dans `action_close()` **et**
   contrainte `@api.constrains("state", "date_end_actual")`.
4. Campagne clôturée : données métier verrouillées (nom, code, exploitation,
   dates, description, notes) → `UserError`.
5. Campagne annulée : même verrouillage.
6. `farm_id` requis ; exploitation validée par l'ORM.
7. Société toujours égale à `farm_id.company_id` (champ related stocké) ;
   isolation multi-sociétés portée par les ACL.
8. `active` et `sequence` restent modifiables après clôture (archivage possible).

Aucune règle de chevauchement, aucune unicité de campagne active par exploitation.

---

# 6. VUES ET MENUS

## Liste
Code, nom, exploitation, date de début, date de fin prévue, état (badge),
société (multi-société), `active` masqué.

## Formulaire
- En-tête : boutons Démarrer / Clôturer / Annuler + barre d'état.
- « Informations générales » : code (lecture seule), nom, exploitation, société,
  séquence.
- « Période » : début, fin prévue, clôture réelle.
- « Description ».
- Onglet « Notes internes ».
- Ruban « Archivé ».
- Les champs métier passent en lecture seule lorsque l'état est `closed` ou
  `cancelled`.

## Recherche
- Champs : code, nom, exploitation.
- Filtres : Brouillon, En cours, Clôturées, Annulées, Archivées.
- Regroupements : exploitation, état, année de début (`date_start:year`).

## Menu
« Campagnes agricoles » sous « Production végétale » (séquence 20, après
« Cultures implantées »), groupe utilisateur agricole.

Les trois vues ont été compilées avec succès via `get_views`.

---

# 7. ACL ET RÈGLES MULTI-SOCIÉTÉS

| Groupe | Opérations | Domaine |
|---|---|---|
| `group_gest_agri_user` | `r` | `[('farm_id', 'in', user.gest_agri_farm_ids.ids)]` |
| `group_gest_agri_manager` | `cu` | `[('farm_id', 'in', user.gest_agri_managed_farm_ids.ids)]` |
| `group_gest_agri_admin` | `crud` | `[('company_id', 'in', company_ids)]` |

Conformes aux conventions de `gest_agri.plot` et `gest_agri.crop.cycle`.
Aucune ACL d'un autre modèle modifiée, aucun groupe modifié, aucune règle
`ir.rule` ajoutée (le module n'en utilise pas).

---

# 8. TESTS AJOUTÉS

Fichier `tests/test_crop_campaign.py` — **25 tests**, tous exécutés :

| # | Test | Résultat |
|---|---|---|
| 1 | `test_create_campaign` | ✅ |
| 2 | `test_code_generated_and_unique` | ✅ |
| 3 | `test_code_uniqueness_on_write_rejected` | ✅ |
| 4 | `test_code_uniqueness_on_create_rejected` | ✅ |
| 5 | `test_farm_required` | ✅ |
| 6 | `test_company_derived_from_farm` | ✅ |
| 7 | `test_farm_inverse_relation` | ✅ |
| 8 | `test_planned_end_before_start_rejected` | ✅ |
| 9 | `test_actual_end_before_start_rejected` | ✅ |
| 10 | `test_draft_to_active` | ✅ |
| 11 | `test_draft_to_cancelled` | ✅ |
| 12 | `test_active_to_closed_with_actual_date` | ✅ |
| 13 | `test_close_without_actual_date_rejected` | ✅ |
| 14 | `test_active_to_cancelled` | ✅ |
| 15 | `test_forbidden_transitions` | ✅ |
| 16 | `test_direct_state_write_rejected` | ✅ |
| 17 | `test_multiple_active_campaigns_allowed` | ✅ |
| 18 | `test_closed_campaign_protected` | ✅ |
| 19 | `test_cancelled_campaign_protected` | ✅ |
| 20 | `test_archive_and_unarchive` | ✅ |
| 21 | `test_acl_user_read_only` | ✅ |
| 22 | `test_acl_manager_create_write_no_delete` | ✅ |
| 23 | `test_acl_admin_full` | ✅ |
| 24 | `test_multi_company_isolation` | ✅ |
| 25 | `test_crop_cycle_untouched` | ✅ |

---

# 9. COMMANDES EXÉCUTÉES

```
# Vérification de la cible
PGPASSWORD=odoo20 psql -U odoo20 -h 127.0.0.1 -p 5433 -d odoo20

# Mise à jour du module
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 \
         --stop-after-init -u gestion_agricole

# Tests
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 \
         --stop-after-init --test-enable --test-tags /gestion_agricole \
         --log-level=test
```

---

# 10. RÉSULTATS DÉTAILLÉS DES TESTS

```
0 failed, 27 error(s) of 185 tests when loading database 'odoo20'
```

| Catégorie | Nombre |
|---|---|
| Tests exécutés | 185 |
| Réussis (`passed`) | **158** |
| Échoués (`failed`) | **0** |
| En erreur (`errors`) | **27** |
| Nouveaux tests Prompt 51 | **25 / 25 réussis** |

Les 27 erreurs sont **exactement** l'ensemble historique déjà constaté
(comparaison nom par nom avec le run du Prompt 50 : ensembles identiques) :
`TestReservationUnicity` (26) et `TestAuditPrompt11` (1), liées à l'absence de
`gest_agri_reference_reservation` / `btree_gist`. Aucune erreur liée aux
campagnes.

---

# 11. RÉSULTAT DE LA MISE À JOUR SUR `odoo20`

**EXIT=0.**

Contrôles en base :

| Contrôle | Résultat |
|---|---|
| Table `gest_agri_crop_campaign` | créée |
| Index unique `UPPER(BTRIM(code))` | présent |
| Séquence `gest_agri.crop.campaign` | `CAM/%(year)s/`, padding 5 |
| ACL | 3 règles conformes |
| Vues | form, list, search présentes |
| Action et menu | « Campagnes agricoles » sous « Production végétale » |
| Module | `installed`, version `20.0.1.0.0` |

---

# 12. SYNCHRONISATION DES DEUX RÉPERTOIRES

Copie de développement : `/tmp/opencode/dev/gestion_agricole/`
Module chargé : `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/`

- `diff -q` sur chacun des 8 fichiers modifiés : identiques.
- `diff -qr` global (hors `__pycache__`, rapports et cahier des charges) :
  aucune différence.

---

# 13. CONFIRMATION : CYCLES DE CULTURE NON MODIFIÉS

- `models/production/crop_cycle.py` **non modifié** dans ce prompt.
- Aucun champ `campaign_id` ni `campaign_ids` ajouté à `gest_agri.crop.cycle`.
- `gest_agri.plot`, `gest_agri.crop.type`, `gest_agri.crop.variety` non modifiés.
- Le test `test_crop_cycle_untouched` vérifie l'absence de champ de campagne sur
  le cycle et l'absence d'effet d'une création de campagne sur un cycle existant.
- Le rattachement des cycles aux campagnes reste réservé au Prompt 52.

---

# 14. ANOMALIES ET RÉSERVES TECHNIQUES

## Anomalie rencontrée et corrigée
Premier passage des tests : **1 erreur** dans `test_acl_admin_full`. Cause :
le jeu de données de test utilisait `date_start = 2027-01-01` avec la date de fin
par défaut `2026-12-31`, ce qui déclenchait à juste titre la contrainte
`date_end >= date_start`. Correction du test (fin au 2027-12-31), sans
modification du modèle. Résultat suivant : 0 échec, 27 erreurs historiques
uniquement.

## Réserves
- L'unicité du code est **globale** (toutes sociétés, archives comprises) et non
  par société : c'est cohérent avec une séquence unique et un code technique
  auto-généré. Aucune décision métier contraire n'existe dans le cahier des
  charges.
- Le champ `state` (`active` = « En cours ») et le champ `active` (archivage)
  sont distincts ; l'interface les présente dans des zones différentes.
- Le verrouillage des données métier s'applique aux champs listés au §5. Le champ
  `sequence` peut encore être ajusté après clôture (ordre d'affichage).
- Aucune règle de chevauchement entre campagnes, conformément à la consigne.
- Les 27 erreurs de réservation restent hors périmètre et inchangées.

---

*Rapport — Prompt N°51 — Module `gestion_agricole` — Odoo 20 Community.
Quatorzième évolution fonctionnelle. Développement dans la copie de travail,
réplication vérifiée et tests réels sur `odoo20`.*
