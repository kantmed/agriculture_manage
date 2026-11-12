# Rapport Prompt 56 — Développement du module Matériel agricole

**Module :** `gestion_agricole` — Odoo 20 Community
**Base de données :** `odoo20`
**Interpréteur :** `/etc/odoo20-venv/bin/python` (Python 3.12)
**Date :** 2026-11-12

---

## 1. Modèles créés

### `gest_agri.equipment` (Équipement agricole)
Fichier : `models/equipment/equipment.py`

- **Identification** : `name` (désignation), `reference` (séquence `MAT/YYYY/NNNNN`), `equipment_type_id` (référentiel existant `gest_agri.equipment.type`), `brand`, `model`, `serial_number`, `registration_number`, `description`, `image_1920`.
- **Rattachement** : `farm_id` (obligatoire), `site_id` (facultatif), `company_id` (dérivé), `location`.
- **Acquisition** : `acquisition_date`, `acquisition_price`, `supplier_id`, `commissioning_date`, `warranty_end_date`, `condition` (neuf/occasion), `notes`.
- **Compteurs** : `hour_meter`, `odometer`, `cycle_counter` (positifs ou nuls).
- **État** : `draft`, `available`, `in_use`, `maintenance`, `out_of_service`, `retired` (transitions par méthodes métier, écriture directe interdite).
- **Relations/statistiques** : `usage_ids`, `usage_count`, `maintenance_ids`, `maintenance_count`, `last_usage_date`, `last_maintenance_date`, `next_maintenance_date/hours/km`, `total_maintenance_cost`.
- **Archivage** : `active`.

### `gest_agri.equipment.usage` (Utilisation)
Fichier : `models/equipment/usage.py`

- **Identification** : `name` (séquence `UTI/YYYY/NNNNN`).
- **Rattachement** : `equipment_id` (obligatoire), `farm_id`/`company_id` dérivés, `plot_id`, `intervention_id`, `operator_id`.
- **Période** : `start_datetime`, `end_datetime`, `duration_hours` (calculé).
- **Compteurs** : `counter_start`, `counter_end`, `counter_delta` (calculé).
- **État** : `draft`, `done`, `cancelled`.
- **Contrôles** : dates, compteurs, chevauchements temporels, cohérence exploitation/parcelle, refus si équipement retiré/hors service/en maintenance.

### `gest_agri.equipment.maintenance` (Maintenance)
Fichier : `models/equipment/maintenance.py`

- **Identification** : `name` (séquence `MAI/YYYY/NNNNN`).
- **Rattachement** : `equipment_id` (obligatoire), `farm_id`/`company_id` dérivés.
- **Type** : préventive, corrective, inspection, révision, réparation.
- **Dates** : `planned_date`, `realized_date`, `duration_hours`.
- **Intervenants** : `provider_id`, `technician_id`.
- **Descriptions** : `problem_description`, `work_description`, `parts_used`, `notes`.
- **Compteurs** : `counter_at_maintenance`.
- **Coûts** : `parts_cost`, `labor_cost`, `external_cost`, `total_cost` (calculé).
- **Échéance préventive** : `next_due_date`, `next_due_hours`, `next_due_km`.
- **État** : `draft`, `planned`, `in_progress`, `done`, `cancelled` (transitions contrôlées).
- **Effet** : maintenance en cours rend l'équipement indisponible ; remise à disposition après terminaison.

---

## 2. Référentiels existants réutilisés

- `gest_agri.equipment.type` (types de matériel) — réutilisé, non recréé.
- `gest_agri.farm`, `gest_agri.site`, `gest_agri.plot` — rattachement organisationnel.
- `gest_agri.crop.intervention` — référence optionnelle dans les utilisations.
- `res.partner`, `res.users` — fournisseur/opérateur/technicien.
- Groupes de sécurité existants : `group_gest_agri_user`, `group_gest_agri_manager`, `group_gest_agri_admin`.
- `_check_company_auto = True` réutilisé.

---

## 3. Champs et règles métier

- Contraintes Python : compteurs positifs, cohérence site/exploitation, dates, chevauchements, états.
- Contraintes de transition d'état via méthodes métier (`action_*`), écriture directe interdite.
- Calculs : `duration_hours`, `counter_delta`, `total_cost`, `usage_count`, `maintenance_count`, `last_usage_date`, `last_maintenance_date`, `total_maintenance_cost`.

---

## 4. Workflows

- **Équipement** : `draft` → `available` → `in_use` / `maintenance` / `out_of_service` → `retired` (avec possibilité de retour en brouillon depuis retiré).
- **Utilisation** : `draft` → `done` / `cancelled`.
- **Maintenance** : `draft` → `planned` → `in_progress` → `done` / `cancelled`.

---

## 5. Vues, actions et menus

Fichier : `views/equipment_views.xml`

- Vues liste, formulaire (7 onglets), recherche pour chaque modèle.
- Actions `ir.actions.act_window` pour les trois modèles.
- Menus sous « Matériel » : Équipements, Utilisations, Maintenances.
- Boutons statistiques sur la fiche équipement (utilisations, maintenances).
- Boutons de navigation vers les listes filtrées.

---

## 6. ACL et restrictions d'accès

Fichier : `security/ir.access.csv` — 9 entrées (3 par modèle × 3 groupes), avec domaines par exploitation/société, conformes au pattern existant (interventions, récoltes).

---

## 7. Tests exécutés

Commande :
```
/etc/odoo20-venv/bin/python /mnt/srv/share/odoo20/odoo/odoo-bin -c /etc/odoo20.conf -d odoo20 \
  --no-http --http-port=0 --max-cron-threads=0 --stop-after-init \
  --test-enable --test-tags /gestion_agricole:TestEquipment --log-level=test
```

Résultat (`/tmp/opencode/odoo_tests_eq2.log`) :
```
35 post-tests in 1.40s, 796 queries
gestion_agricole: 37 tests 1.33s 796 queries
0 failed, 0 error(s) of 35 tests
```

| Catégorie | Nombre |
|---|---:|
| Tests exécutés et réussis | **35** |
| Tests échoués (`failed`) | **0** |
| Erreurs d'exécution (`errors`) | **0** |
| Tests non exécutés | **0** |

---

## 8. Mise à jour de la base `odoo20`

- Mise à jour via le script avec neutralisation de `update_list` (contournement documenté).
- Résultat : `Registry loaded in 5.489s`, `Module gestion_agricole loaded in 3.27s`, **REGISTRY RC = 0**.
- Modèles `gest_agri.equipment`, `gest_agri.equipment.usage`, `gest_agri.equipment.maintenance` présents en base.
- Menus Équipements/Utilisations/Maintenances présents.

---

## 9. Synchronisation développement / module installé

- Tous les fichiers sources synchronisés (`diff -rq` : aucune différence).
- Py_compile OK.

---

## 10. Anomalies restantes et limitations

- Aucune anomalie bloquante.
- La mise à jour explicite `-u gestion_agricole` reste bloquée à `update_list` (service partagé), mais le contournement documenté fonctionne.
- Pas de gestion de stock, comptabilité, personnel ou achats (hors périmètre, prompts distincts).

---

## CRITÈRE DE CLÔTURE

**PROMPT 56 VALIDÉ ET CLÔTURÉ**

Les équipements, utilisations et maintenances fonctionnent conformément aux exigences, les 35 tests ciblés sont réussis et le module est correctement chargé.