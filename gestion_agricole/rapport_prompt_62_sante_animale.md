# RAPPORT PROMPT 62 — SANTÉ ANIMALE ET SUIVI VÉTÉRINAIRE

**Projet :** `gestion_agricole`
**Version :** Odoo 20 Community (Python 3.12)
**Base de données :** `odoo20` (seule base utilisée)
**Préfixe technique :** `gest_agri`
**Date :** 12 novembre 2026

---

## 1. Analyse préalable

Avant toute modification, le cahier des charges du prompt 62 et le code existant ont été examinés :

- Les fonctionnalités Élevage des prompts 60 (cheptel : `gest_agri.animal`, `gest_agri.animal.lot`) et 61 (alimentation : `gest_agri.feed`, `gest_agri.feed.ration`, `gest_agri.feed.distribution`) ont été relues pour garantir la continuité et éviter tout doublon.
- Les modèles Exploitation (`gest_agri.farm`), Site (`gest_agri.site`) et Société (`res.company`) ainsi que leurs règles de cohérence (`farm_id` / `site_id`) ont été réutilisés à l'identique.
- Les référentiels déjà disponibles ont été réutilisés : `gest_agri.livestock.species` (espèces) et `gest_agri.livestock.breed` (races).
- Les modèles Odoo standards ont été réutilisés : `res.partner` (vétérinaires/contacts), `res.users` (responsables), `uom.uom` (unités de mesure). Aucun système parallèle de stock ni de médicaments n'a été créé (pas de doublon avec `product`/`stock`).
- Le mécanisme de sécurité existant a été respecté : groupes `group_gest_agri_user`, `group_gest_agri_manager`, `group_gest_agri_admin` et cloisonnement par exploitation via le domaine `farm_id in user.gest_agri_farm_ids.ids` (modèle Odoo 20 `ir.access`, champ `domain`).
- Les conventions techniques du module ont été suivies : `_inherit = ["mail.thread"]`, `_check_company_auto = True`, `reference` automatique via `ir.sequence`, workflow `state` + `action_*` + garde `write()` (drapeau de contexte pour les transitions), protection `unlink()`.

**Conclusion de l'analyse :** aucun modèle santé n'existait. Les entités à créer ont été confirmées : maladies, dossiers sanitaires, consultations vétérinaires, vaccinations, traitements, interventions sanitaires.

---

## 2. Référentiels et modèles existants réutilisés

| Élément réutilisé | Type | Usage |
|---|---|---|
| `gest_agri.farm` | Modèle | Exploitation (cloisonnement, cohérence) |
| `gest_agri.site` | Modèle | Site rattaché à l'exploitation |
| `gest_agri.animal` | Modèle | Animal individuel (étendu pour l'historique) |
| `gest_agri.animal.lot` | Modèle | Lot d'animaux (étendu pour l'historique) |
| `gest_agri.livestock.species` | Référentiel | Espèces concernées par une maladie |
| `res.partner` | Modèle Odoo | Vétérinaire / intervenant |
| `res.users` | Modèle Odoo | Responsable de déclaration / administration |
| `uom.uom` | Modèle Odoo | Unité de mesure des doses |
| `ir.sequence` | Modèle Odoo | Références automatiques |
| Groupes `group_gest_agri_*` | Sécurité | Lecture / gestion / administration |

Aucun de ces éléments n'a été dupliqué.

---

## 3. Modèles créés ou modifiés

### Créés (package `models/health/`)

| Modèle | Fichier | Description |
|---|---|---|
| `gest_agri.animal.disease` | `disease.py` | Référentiel des maladies animales |
| `gest_agri.animal.health` | `health_record.py` | Dossier sanitaire individuel |
| `gest_agri.veterinary.consultation` | `consultation.py` | Consultation / intervention vétérinaire |
| `gest_agri.vaccination` | `vaccination.py` | Vaccination (animal ou lot) |
| `gest_agri.animal.treatment` | `treatment.py` | Traitement vétérinaire (animal ou lot) |
| `gest_agri.sanitary.intervention` | `sanitary_intervention.py` | Intervention sanitaire sur lot |

### Étendus (héritage `_inherit`, aucun doublon)

| Modèle | Fichier | Ajouts |
|---|---|---|
| `gest_agri.animal` | `animal_health.py` | Historique sanitaire + échéances |
| `gest_agri.animal.lot` | `animal_health.py` | Historique sanitaire lot |

`models/health/__init__.py` et `models/__init__.py` importent le nouveau package.

---

## 4. Champs et relations

### `gest_agri.animal.disease`
- `name` (obligatoire, indexé), `code` (obligatoire, unique par société via `UniqueIndex` insensible à la casse), `description`, `symptoms`, `species_ids` (M2M `gest_agri.livestock.species`), `severity` (faible/moyenne/élevée/critique), `contagious`, `recommendations`, `active`, `company_id`.

### `gest_agri.animal.health`
- `name` (séquence `SAN/%(year)s/`), `animal_id` (obligatoire, cascade), `farm_id` (lié à l'animal, stocké), `company_id`, `site_id`, `observation_date` (obligatoire), `declaration_date`, `symptoms`, `disease_id`, `severity`, `notes`, `veterinarian_id` (res.partner), `responsible_id` (res.users), `state` (draft/validated/cancelled).

### `gest_agri.veterinary.consultation`
- `name` (séquence `CONS/%(year)s/`), `animal_id` **ou** `lot_id` (exclusifs), `farm_id` (calculé depuis animal ou lot), `company_id`, `site_id`, `consultation_datetime` (obligatoire), `veterinarian_id`, `reason`, `symptoms`, `diagnosis`, `acts`, `recommendations`, `next_control_date`, `notes`, `responsible_id`, `state` (draft/done/cancelled).

### `gest_agri.vaccination`
- `name` (séquence `VAC/%(year)s/`), `animal_id` **ou** `lot_id` (exclusifs), `farm_id` (calculé), `company_id`, `vaccine_name` (obligatoire), `vaccine_lot`, `vaccination_date` (obligatoire), `next_due_date`, `dose`, `uom_id`, `administration_route`, `veterinarian_id`, `responsible_id`, `notes`, `state` (draft/done/cancelled).

### `gest_agri.animal.treatment`
- `name` (séquence `TRT/%(year)s/`), `animal_id` **ou** `lot_id` (exclusifs), `farm_id` (calculé), `company_id`, `product_name` (obligatoire), `start_date` (obligatoire), `end_date_planned`, `end_date_actual`, `dosage`, `uom_id`, `frequency`, `administration_route`, `veterinarian_id`, `responsible_id`, `reason`, `notes`, `state` (draft/in_progress/done/cancelled).

### `gest_agri.sanitary.intervention`
- `name` (séquence `ISA/%(year)s/`), `lot_id` (obligatoire, restrict), `farm_id`, `company_id`, `intervention_type`, `intervention_date` (obligatoire), `animal_count`, `veterinarian_id`, `responsible_id`, `products_used`, `result`, `notes`, `state` (draft/done/cancelled).

### Extensions `gest_agri.animal`
- `health_record_ids` / `health_record_count`, `consultation_ids` / `consultation_count`, `vaccination_ids` / `vaccination_count`, `treatment_ids` / `treatment_count` (One2many + compteurs calculés).
- `next_vaccination_due_date`, `next_control_date`, `has_overdue_sanitary_deadline` (calculés, indicateurs d'échéances).
- Actions de navigation `action_view_health_records`, `action_view_consultations`, `action_view_vaccinations`, `action_view_treatments`.

### Extensions `gest_agri.animal.lot`
- `consultation_ids` / `consultation_count`, `vaccination_ids` / `vaccination_count`, `treatment_ids` / `treatment_count`, `sanitary_intervention_ids` / `sanitary_intervention_count`, action `action_view_sanitary_interventions`.

---

## 5. Règles de gestion (contrôles côté serveur)

1. **Cohérence animal / exploitation / site** : `_check_site_farm` — le site doit appartenir à l'exploitation de l'animal.
2. **Cohérence lot / exploitation / site** : `_check_scope_coherence` (consultations) — le site doit appartenir à l'exploitation du lot ou de l'animal.
3. **Compatibilité espèces / maladies** : à la création d'un dossier sanitaire, si la maladie définit des espèces, l'espèce de l'animal doit en faire partie.
4. **Cohérence des dates** : `declaration_date >= observation_date` ; `end_date_planned/actual >= start_date` ; `next_due_date >= vaccination_date`.
5. **Doses strictement positives** : contrôle `dose` / `dosage` / `animal_count` (refus des valeurs négatives).
6. **Fin de traitement ≥ début** : contrôlé en création et en `@api.constrains`.
7. **Rappel vaccinal cohérent** : `next_due_date` postérieure à la date de vaccination.
8. **Transitions d'état contrôlées** : chaque `action_*` vérifie l'état courant via `_check_allowed` ; l'écriture directe de `state` lève `AccessError` (drapeau de contexte dédié par modèle).
9. **Historique préservé** : les vaccinations conservent leurs données (nom du vaccin en texte libre), même si les référentiels changent.
10. **Suppressions dangereuses bloquées** : `unlink()` n'autorise la suppression qu'à l'état brouillon, sinon `UserError`.
11. **Cloisonnement par exploitation** : domaine `ir.access` sur `farm_id in user.gest_agri_farm_ids.ids` (lecture) et `gest_agri_managed_farm_ids` (écriture), `company_id in company_ids` pour l'admin.

Aucune règle médicale arbitraire ni prescription/dosage automatique n'a été implémentée : les champs sont descriptifs et proviennent d'une décision vétérinaire.

---

## 6. Vues et menus

### Vues (`views/health_views.xml`)
- 6 × (liste + formulaire + recherche) = 18 vues créées.
- Filtres et regroupements : état, gravité, contagieux, exploitation, site, animal, lot, maladie, vétérinaire.
- **Indicateurs d'échéances** :
  - Vaccinations : « Rappel à venir » / « Rappel dépassé ».
  - Consultations : « Contrôle à venir » / « Contrôle dépassé ».
  - Traitements : « Fin prévue à venir » / « Fin prévue dépassée ».
- Boutons intelligents sur la fiche Animal (dossiers, consultations, vaccinations, traitements) et sur la fiche Lot (interventions).
- Section « Échéances sanitaires » sur la fiche Animal (prochain rappel, prochain contrôle, échéance dépassée).
- Boutons métier : Valider/Annuler (dossier), Réaliser/Annuler (consultation, vaccination), Démarrer/Terminer/Annuler (traitement), Terminer/Annuler (intervention).

### Menus
Nouveau sous-menu **Gestion Agricole → Élevage → Santé animale** :
- Dossiers sanitaires
- Consultations vétérinaires
- Vaccinations
- Traitements
- Interventions sanitaires
- Échéances sanitaires
- Maladies

Les menus Élevage existants (Animaux, Lots, Alimentation) n'ont pas été modifiés.

---

## 7. Sécurité et droits d'accès

- 18 lignes ajoutées à `security/ir.access.csv` (3 par modèle : utilisateur `r`, responsable `cu`, administrateur `crud`).
- Modèle Odoo 20 `ir.access` (champ `domain` réellement appliqué) — aucun système parallèle.
- Domaines :
  - Utilisateur : `[('farm_id','in',user.gest_agri_farm_ids.ids)]` — cloisonnement par exploitation.
  - Responsable : `[('farm_id','in',user.gest_agri_managed_farm_ids.ids)]`.
  - Administrateur : `[('company_id','in',company_ids)]`.
  - Maladies : `[('company_id','in',company_ids)]` (référentiel transversal).
- Vérifié : lecture, création, modification, suppression, cloisonnement inter-exploitations, accès animaux/lots, restriction sur dossiers validés (suppression interdite hors brouillon).

---

## 8. Tests réalisés et résultats détaillés

Fichier : `tests/test_health.py` — classe `TestHealth` (TransactionCase).

**60 tests exécutés — 0 échec — 0 erreur.**

Extrait du journal :

```
odoo.tests.result: 0 failed, 0 error(s) of 60 tests when loading database 'odoo20'
```

Couverture (60 tests) :

| Thème | Tests |
|---|---|
| Référentiel maladies | `test_disease_creation`, `test_disease_species_compatibility`, `test_disease_code_unique`, `test_disease_read_allowed_for_user` |
| Dossiers sanitaires | `test_health_creation`, `test_health_animal_required`, `test_health_date_coherence`, `test_health_site_farm_coherence`, `test_health_workflow`, `test_health_direct_state_write_forbidden`, `test_health_delete_draft_allowed`, `test_health_delete_validated_forbidden`, `test_health_isolation` |
| Consultations | `test_consultation_creation`, `test_consultation_requires_animal_or_lot`, `test_consultation_animal_or_lot_exclusive`, `test_consultation_lot_based`, `test_consultation_site_farm_coherence`, `test_consultation_workflow`, `test_consultation_direct_state_write_forbidden`, `test_consultation_delete_draft_allowed`, `test_consultation_delete_done_forbidden`, `test_consultation_isolation` |
| Vaccinations | `test_vaccination_creation`, `test_vaccination_requires_animal_or_lot`, `test_vaccination_animal_or_lot_exclusive`, `test_vaccination_next_due_date`, `test_vaccination_dose_positive`, `test_vaccination_workflow`, `test_vaccination_direct_state_write_forbidden`, `test_vaccination_delete_draft_allowed`, `test_vaccination_delete_done_forbidden`, `test_vaccination_lot_based`, `test_vaccination_farm_from_lot`, `test_vaccination_isolation` |
| Traitements | `test_treatment_creation`, `test_treatment_requires_animal_or_lot`, `test_treatment_animal_or_lot_exclusive`, `test_treatment_dates`, `test_treatment_dosage_positive`, `test_treatment_workflow`, `test_treatment_cancel`, `test_treatment_direct_state_write_forbidden`, `test_treatment_delete_draft_allowed`, `test_treatment_delete_done_forbidden`, `test_treatment_isolation` |
| Interventions sanitaires | `test_sanitary_intervention_creation`, `test_sanitary_intervention_lot_required`, `test_sanitary_intervention_animal_count_positive`, `test_sanitary_intervention_workflow`, `test_sanitary_intervention_direct_state_write_forbidden`, `test_sanitary_intervention_delete_draft_allowed`, `test_sanitary_intervention_delete_done_forbidden`, `test_lot_sanitary_intervention_count` |
| Historique & échéances | `test_animal_health_history_counts`, `test_animal_next_vaccination_due_date`, `test_animal_overdue_sanitary_deadline`, `test_animal_next_control_date`, `test_draft_records_not_counted_as_deadline` |
| Sécurité / installation | `test_parse_and_install` |

**Non-régression Élevage :** `TestLivestock` + `TestFeeding` rejoués → `0 failed, 0 error(s) of 73 tests`.

---

## 9. Résultat de `py_compile`

```
/etc/odoo20-venv/bin/python -m py_compile models/health/*.py tests/test_health.py
PY_COMPILE_OK
```

XML validés : `views/health_views.xml`, `data/ir_sequence_health.xml`.

---

## 10. Résultat de la synchronisation

Copie dev → copie installée, puis contrôle d'identité :

```
diff -rq <dev> <installed> -x __pycache__ -x "*.pyc"
Seulement dans <installed>: RAPPORT_PROMPT_55_BIS_FINAL.md
```

L'unique écart est un rapport pré-existant (prompt 55), sans rapport avec ce développement. Tous les fichiers santé (modèles, vues, séquence, ACL, manifest, tests) sont **identiques**.

---

## 11. Résultat de la mise à jour sur `odoo20`

Contournement `update_list` utilisé (problème récurrent connu) :

`/etc/odoo20-venv/bin/python /tmp/opencode/update_noupdatelist.py`
- Monkeypatch de `odoo.addons.base.models.ir_module.IrModuleModule.update_list` → `[0, 0]`, puis `Registry.new("odoo20", update_module=True, upgrade_modules=["gestion_agricole"])`.
- Aucune modification du cœur Odoo ; contournement non généralisé.

Résultat : `Modules loaded.` puis `Registry loaded in 7.915s`, **`REGISTRY RC = 0`**. Aucune erreur/traceback liée au module.

---

## 12. Vérification du registre

| Contrôle | Résultat |
|---|---|
| 6 modèles enregistrés (`ir.model`) | OK |
| 18 vues (`ir.ui.view`) | OK |
| 8 entrées de menu sous Élevage → Santé animale | OK |
| 18 lignes `ir.access` (3 × 6 modèles) | OK |
| 6 champs santé sur `gest_agri.animal` | OK |
| Non-régression Élevage (73 tests) | OK |

---

## 13. Problèmes rencontrés et solutions

1. **`AccessError` non importé** dans `health_record.py`, `vaccination.py`, `sanitary_intervention.py` (3 erreurs au 1er passage de tests).
   → Correction des imports `from odoo.exceptions import AccessError, UserError, ValidationError`. Tests verts ensuite.
2. **`farm_id` lié uniquement à `animal_id.farm_id`** : les enregistrements basés sur un lot avaient `farm_id` vide, ce qui cassait le cloisonnement.
   → Remplacement par un champ calculé stocké `farm_id = animal_id.farm_id or lot_id.farm_id` (vaccination, traitement, consultation). Test `test_vaccination_farm_from_lot` le vérifie.
3. **Problème récurrent `update_list`** (blocage à « updating modules list ») : contourné par le script de monkeypatch documenté, sans toucher au cœur Odoo.
4. **`btree_gist` absent** (problème isolé pré-existant) : le mécanisme de réservation d'unicité reste inerte ; aucun impact sur ce développement.

---

## 14. Fichiers créés et modifiés

**Créés**
- `models/health/__init__.py`
- `models/health/disease.py`
- `models/health/health_record.py`
- `models/health/consultation.py`
- `models/health/vaccination.py`
- `models/health/treatment.py`
- `models/health/sanitary_intervention.py`
- `models/health/animal_health.py`
- `data/ir_sequence_health.xml`
- `views/health_views.xml`
- `tests/test_health.py`
- `rapport_prompt_62_sante_animale.md` (ce rapport)

**Modifiés**
- `models/__init__.py` (import du package `health`)
- `security/ir.access.csv` (+18 lignes)
- `tests/__init__.py` (import `test_health`)
- `__manifest__.py` (ajout `data/ir_sequence_health.xml` et `views/health_views.xml`)

---

## 15. Fonctionnalités restant à développer

Conformément aux limites du prompt 62, ces sujets sont **hors périmètre** et réservés à des prompts distincts :
- Reproduction animale (gestation, mise bas, naissances).
- Mortalité et suivi des sorties.
- Production animale : lait, viande, œufs.
- Rentabilité et comptabilité analytique détaillée de l'élevage.
- Gestion documentaire avancée (pièces jointes justificatives) sur les consultations.

---

**PROMPT 62 VALIDÉ ET CLÔTURÉ**
