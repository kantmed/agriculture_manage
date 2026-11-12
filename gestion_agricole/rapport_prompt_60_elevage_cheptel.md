# Rapport Prompt 60 — Développement du module Élevage : gestion du cheptel

**Module :** `gestion_agricole` — Odoo 20 Community
**Base de données :** `odoo20`
**Interpréteur :** `/etc/odoo20-venv/bin/python` (Python 3.12)
**Date :** 2026-11-12

---

## 1. Documents du cahier des charges consultés

- `01_CAHIER_DES_CHARGES_GENERAL.md` (modules prévus : élevage)
- `02_CARTOGRAPHIE_FONCTIONNELLE.md`
- `03_PROCESSUS_METIER.md`
- `05_REGLES_DE_GESTION.md`
- `07_MATRICE_DES_TESTS_ACCEPTATION.md`

## 2. Référentiels existants réutilisés

- `gest_agri.livestock.species` (espèce animale)
- `gest_agri.livestock.breed` (race animale)
- `gest_agri.farm`, `gest_agri.site`, `gest_agri.plot`
- Groupes de sécurité : `group_gest_agri_user`, `group_gest_agri_manager`, `group_gest_agri_admin`

## 3. Modèles créés

| Modèle | Fichier | Description |
|---|---|---|
| `gest_agri.animal` | `models/livestock/animal.py` | Animal individuel (identification, espèce/race, sexe, dates, exploitation, lot, état) |
| `gest_agri.animal.lot` | `models/livestock/animal_lot.py` | Lot d'animaux (espèce, race, exploitation, membres, effectif, état) |

## 4. Champs et relations

- **Animal** : `name`, `reference` (séquence `ANI/YYYY/NNNNN`), `official_id` (unique), `species_id`, `breed_id`, `sex`, `birth_date`, `entry_date`, `origin`, `farm_id`, `site_id`, `company_id`, `lot_id`, `state`, `notes`, `active`.
- **Lot** : `name`, `reference` (séquence `LOT/YYYY/NNNNN`), `species_id`, `breed_id`, `farm_id`, `site_id`, `company_id`, `constitution_date`, `member_ids` (One2many), `member_count` (compute), `state`, `notes`, `active`.
- Relations : animal → lot (Many2one), lot → animaux (One2many).

## 5. Règles métier

- Cohérence espèce/race.
- Cohérence exploitation/site.
- Cohérence lot/exploitation.
- Unicité du numéro d'identification officiel.
- Contrôle des transitions d'état (écriture directe interdite).
- Suppression d'un lot avec membres interdite.

## 6. Vues et menus

Fichier : `views/livestock_views.xml`

- Vues liste, formulaire, recherche pour animaux et lots.
- Actions `ir.actions.act_window`.
- Menus sous « Élevage » : Animaux, Lots d'animaux.

## 7. Droits d'accès

Fichier : `security/ir.access.csv` — 6 entrées (2 modèles × 3 groupes) avec domaines par exploitation/société.

## 8. Tests exécutés

Commande :
```
/etc/odoo20-venv/bin/python /mnt/srv/share/odoo20/odoo/odoo-bin -c /etc/odoo20.conf -d odoo20 \
  --no-http --http-port=0 --max-cron-threads=0 --stop-after-init \
  --test-enable --test-tags /gestion_agricole:TestLivestock --log-level=test
```

Résultat (`/tmp/opencode/odoo_tests_live2.log`) :
```
36 post-tests in 1.22s, 808 queries
gestion_agricole: 38 tests 1.15s 808 queries
0 failed, 0 error(s) of 36 tests
```

| Catégorie | Nombre |
|---|---:|
| Tests exécutés et réussis | **36** |
| Tests échoués (`failed`) | **0** |
| Erreurs d'exécution (`errors`) | **0** |
| Tests non exécutés | **0** |

## 9. Résultat de mise à jour de `odoo20`

- Mise à jour via script avec neutralisation de `update_list` (contournement documenté).
- Résultat : `Registry loaded in 6.145s`, `Module gestion_agricole loaded`, **REGISTRY RC = 0**.
- Modèles `gest_agri.animal` et `gest_agri.animal.lot` présents en base.

## 10. Vérification de synchronisation

- Sources dev ↔ install identiques (aucune différence).
- Py_compile OK.

## 11. Anomalies restantes

- Aucune anomalie bloquante.
- La mise à jour explicite `-u gestion_agricole` reste bloquée à `update_list` (service partagé), contournement documenté.

## 12. Fonctionnalités réservées aux prochains prompts

- Alimentation animale.
- Santé et traitements vétérinaires.
- Reproduction, naissances, mortalité.
- Production animale (lait, viande, œufs).
- Économie liée à l'élevage.

---

## CRITÈRE DE CLÔTURE

**PROMPT 60 VALIDÉ ET CLÔTURÉ**

La gestion individuelle des animaux est opérationnelle, la gestion des lots est opérationnelle, les référentiels existants sont correctement réutilisés, les contrôles métier sont fonctionnels, les vues et menus sont accessibles, la sécurité respecte l'architecture existante, 36 tests ciblés sont réussis et le module est correctement chargé.