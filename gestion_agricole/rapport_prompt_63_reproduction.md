# RAPPORT PROMPT 63 — REPRODUCTION ANIMALE, GESTATION, NAISSANCES ET MORTALITÉ

**Module :** `gestion_agricole`
**Version :** Odoo 20 Community
**Base de données :** `odoo20` (seule base utilisée)
**Date :** 12 novembre 2026
**Interpréteur :** `/etc/odoo20-venv/bin/python` (Python 3.12)
**Copie de développement :** `/tmp/opencode/dev/gestion_agricole/`
**Copie installée :** `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/`

---

## 1. Résumé fonctionnel

Le volet **Reproduction animale** du module `gestion_agricole` a été développé. Il couvre
désormais l'ensemble du cycle reproductif du cheptel :

- **Événements reproductifs** : accouplement naturel, insémination artificielle, transfert
  embryonnaire, autre événement, avec référence automatique, femelle/mâle, espèce/race
  cohérentes, méthode, origine de la semence, responsable et observations.
- **Gestations** : rattachées à un événement d'origine, avec date prévue de mise bas
  **calculée à partir d'une durée de gestation configurable par espèce** (pas de constante
  universelle codée en dur), méthode et date de confirmation, statut (à confirmer, confirmée,
  terminée, avortée, interrompue), et verrouillage des données principales après clôture.
- **Mises bas et naissances** : type de mise bas, décompte total / vivants / mort-nés,
  gestion des naissances multiples via un modèle de ligne `gest_agri.animal.birth.newborn`,
  et **création explicite** des nouveaux animaux par action métier (`action_create_newborn_animals`).
- **Mortalités** : individuelles (animal unique, passage automatique de l'animal à l'état
  « Décédé ») et par lot (effectif contrôlé par rapport à l'effectif disponible du lot),
  avec type, cause, diagnostic vétérinaire et liens vers le sanitaire.
- **Historique reproductif** de l'animal : filiation (mère, père, mise bas d'origine) et
  indicateurs calculés (nombre d'événements, de gestations, de mises bas, petits vivants,
  mort-nés, dernière mise bas, prochaine mise bas prévue, mortalités, décès).
- **Statistiques** reproductives et de mortalité par exploitation et par espèce.

Toutes les validations sont réalisées **côté serveur** (contraintes `@api.constrains`,
index uniques PostgreSQL, gardes d'état dans `write()`), les transitions d'état passent
exclusivement par des actions métier, et la suppression est limitée aux brouillons.

---

## 2. Modèles créés

| Modèle technique | Description | Fichier |
|---|---|---|
| `gest_agri.animal.reproduction` | Événement reproductif | `models/reproduction/event.py` |
| `gest_agri.animal.gestation` | Gestation animale | `models/reproduction/gestation.py` |
| `gest_agri.animal.birth` | Mise bas et naissance | `models/reproduction/birth.py` |
| `gest_agri.animal.birth.newborn` | Ligne nouveau-né d'une mise bas (naissances multiples) | `models/reproduction/birth.py` |
| `gest_agri.animal.mortality` | Mortalité animale (individuelle ou de lot) | `models/reproduction/mortality.py` |

Tous les modèles héritent de `mail.thread` (traçabilité), utilisent `_check_company_auto=True`,
et portent `farm_id` + `company_id` conformément aux conventions du module.

**Justification du modèle de ligne `gest_agri.animal.birth.newborn` :** la gestion des
naissances multiples exige de décrire individuellement chaque petit (sexe, race, lot,
animal déjà enregistré éventuel). Un unique champ texte ne permettrait ni la cohérence
de rattachement à un animal existant ni la création traçable des nouveaux animaux.

---

## 3. Modèles existants étendus

| Modèle étendu | Fichier | Nature de l'extension |
|---|---|---|
| `gest_agri.animal` | `models/reproduction/animal_reproduction.py` | Filiation + historique reproductif + indicateurs mortalité |
| `gest_agri.animal.lot` | `models/reproduction/animal_reproduction.py` | Historique des mortalités de lot |
| `gest_agri.livestock.species` | `models/configuration/livestock_species.py` | Ajout de la durée de gestation configurable |

Aucun modèle de santé animale (`gest_agri.animal.health`, `gest_agri.veterinary.consultation`,
`gest_agri.animal.treatment`, `gest_agri.sanitary.intervention`) n'a été modifié : les
nouveaux modèles s'y rattachent uniquement par des `Many2one` optionnels (intégration sans
altération).

---

## 4. Champs et relations ajoutés

### 4.1 `gest_agri.livestock.species` (référentiel existant réutilisé)

| Champ | Type | Note |
|---|---|---|
| `gestation_duration_days` | Integer | Durée de gestation configurable ; contrainte `> 0` si renseignée |

### 4.2 `gest_agri.animal.reproduction`

`name` (référence séquence, lecture seule), `active`, `female_id` (requis),
`male_id`, `farm_id` (calculé stocké depuis la femelle), `company_id` (lié stocké),
`site_id`, `species_id` / `breed_id` (liés stockés depuis la femelle), `event_date` (requis),
`event_type` (sélection), `method`, `semen_origin`, `responsible_id`, `notes`,
`state` (draft/confirmed/cancelled), `gestation_ids` (One2many), `gestation_count`.

### 4.3 `gest_agri.animal.gestation`

`name`, `active`, `female_id` (requis), `reproduction_id` (événement d'origine),
`male_id`, `farm_id` (calculé stocké), `company_id` (lié stocké), `site_id`,
`species_id` / `breed_id` (liés stockés), `start_date` (requis),
`expected_birth_date` (calculé stocké, modifiable), `confirmation_date`,
`confirmation_method` (sélection), `actual_end_date`, `responsible_id`, `notes`,
`state` (to_confirm/confirmed/terminated/aborted/interrupted), `birth_ids` (One2many),
`birth_count`.

### 4.4 `gest_agri.animal.birth`

`name`, `active`, `gestation_id` (requis), `mother_id` (lié stocké depuis la gestation),
`father_id`, `farm_id` (lié stocké), `company_id` (lié stocké), `site_id`,
`birth_datetime` (requis), `birth_type` (sélection), `total_count`, `alive_count`,
`stillborn_count`, `responsible_id`, `veterinarian_id`, `notes`, `newborn_ids` (One2many),
`newborn_count`, `state` (draft/validated/cancelled).

### 4.5 `gest_agri.animal.birth.newborn`

`birth_id` (requis), `farm_id` / `company_id` (liés stockés, pour la sécurité),
`animal_id` (animal déjà enregistré, optionnel), `name`, `sex`, `breed_id`, `lot_id`, `notes`.

### 4.6 `gest_agri.animal.mortality`

`name`, `active`, `animal_id`, `lot_id`, `farm_id` (calculé stocké), `company_id` (lié stocké),
`site_id`, `death_datetime` (requis), `mortality_type` (sélection), `cause`, `diagnosis`,
`health_record_id` (→ `gest_agri.animal.health`), `consultation_id` (→ `gest_agri.veterinary.consultation`),
`animal_count` (mortalité de lot), `responsible_id`, `notes`, `state` (draft/validated/cancelled).

### 4.7 `gest_agri.animal` (extension)

Filiation : `mother_id`, `father_id`, `birth_id`.
Historique : `reproduction_ids`, `gestation_ids`, `birth_ids`, `mortality_ids` (One2many).
Indicateurs **stockés** (`store=True`) : `reproduction_count`, `gestation_count`,
`gestation_terminated_count`, `gestation_failed_count`, `birth_count`,
`alive_newborn_count`, `stillborn_count`, `last_birth_date`, `next_expected_birth_date`,
`mortality_count`, `death_date`, `is_dead`.

> Le stockage des indicateurs est **nécessaire** : des champs calculés non stockés ne
> peuvent pas être utilisés dans un domaine de vue recherche (cela a provoqué une
> `ParseError` corrigée, cf. section 15).

### 4.8 `gest_agri.animal.lot` (extension)

`mortality_ids` (One2many), `mortality_count`.

---

## 5. Workflows et règles métier

### 5.1 États et transitions

- **Événement reproductif** : `draft` → `confirmed` (`action_confirm`) ; `draft|confirmed` → `cancelled` (`action_cancel`).
- **Gestation** : `to_confirm` → `confirmed` (`action_confirm`, renseigne `confirmation_date`) ;
  `confirmed` → `terminated` (`action_terminate`, renseigne `actual_end_date`) ;
  `to_confirm|confirmed` → `aborted` / `interrupted` (renseigne `actual_end_date`).
- **Mise bas** : `draft` → `validated` (`action_validate`, clôture la gestation confirmée associée) ;
  `draft|validated` → `cancelled` (`action_cancel`).
- **Mortalité** : `draft` → `validated` (`action_validate`, passe l'animal à `dead` si individuelle) ;
  `draft|validated` → `cancelled` (`action_cancel`).

Chaque modèle interdit l'écriture directe de `state` (garde `write()` levant `AccessError`,
contournée uniquement par les actions métier via un drapeau de contexte dédié).

### 5.2 Règles de cohérence (serveur)

- Femelle de sexe féminin, mâle de sexe masculin ; même espèce entre les deux.
- Animaux en état `dead`, `sold` ou `retired` interdits dans un nouvel événement reproductif.
- Dates chronologiquement cohérentes (événement ≥ naissance ; début de gestation ≥ événement ;
  date prévue > début ; fin ≥ début ; mise bas ≥ début de gestation).
- Site rattaché à l'exploitation de la femelle.
- **Une seule gestation par événement reproductif** (index unique PostgreSQL partiel +
  contrainte Python).
- Gestation clôturée (terminée/avortée/interrompue) : champs principaux verrouillés.
- Mise bas : `alive_count + stillborn_count == total_count`, compteurs positifs ou nuls.
- Création des nouveau-nés **explicite** ; le sexe est obligatoire pour créer un animal ;
  l'animal déjà enregistré doit appartenir à la même exploitation.
- Mortalité : exactement un animal **ou** un lot ; **unicité** par animal et unicité par
  couple (lot, date) ; effectif du lot strictement positif et ≤ effectif disponible.
- Suppression limitée aux états brouillon / « à confirmer » selon le modèle.

---

## 6. Vues et menus créés

**16 vues** (`views/reproduction_views.xml`) : listes, formulaires et recherches pour chacun
des 4 modèles principaux, une liste + recherche de **statistiques reproductives** sur
`gest_agri.animal`, plus **2 vues héritées** ajoutant les boutons intelligents
(« smart buttons ») sur la fiche animal (`view_gest_agri_animal_form_reproduction`) et sur
la fiche lot (`view_gest_agri_animal_lot_form_reproduction`).

- Boutons intelligents animal : Reproduction, Gestations, Mises bas, Mortalités.
- Bouton intelligent lot : Mortalités.
- Filtres et regroupements par exploitation, espèce, race, état, type et période.
- Boutons d'action conformes aux workflows dans les en-têtes.

**5 actions** et **6 menus** : un sous-menu **Reproduction** sous **Élevage**, contenant
*Événements reproductifs*, *Gestations*, *Mises bas et naissances*, *Mortalité* et
*Statistiques reproductives*.

---

## 7. Sécurité et droits d'accès

**15 lignes ACL** ajoutées dans `security/ir.access.csv` (3 par modèle × 5 modèles),
selon le modèle de sécurité éprouvé du module :

| Groupe | Opération | Domaine |
|---|---|---|
| `group_gest_agri_user` | `r` | `[('farm_id', 'in', user.gest_agri_farm_ids.ids)]` |
| `group_gest_agri_manager` | `cu` | `[('farm_id', 'in', user.gest_agri_managed_farm_ids.ids)]` |
| `group_gest_agri_admin` | `crud` | `[('company_id', 'in', company_ids)]` |

Le modèle de ligne `gest_agri.animal.birth.newborn` porte ses propres `farm_id` / `company_id`
(liés stockés) afin que l'isolation des exploitations soit appliquée directement, sans
chemin de domaine fragile. Aucun `sudo()` injustifié n'a été introduit.

---

## 8. Liste des tests réalisés et résultats

**Fichier :** `tests/test_reproduction.py` — **63 tests**, **0 échec, 0 erreur**.

```
Commande : --test-enable --test-tags /gestion_agricole:TestReproduction
Résultat : 0 failed, 0 error(s) of 63 tests when loading database 'odoo20'
```

Couverture par domaine :

**Événements reproductifs (13)**
`test_reproduction_creation`, `test_reproduction_confirm`, `test_reproduction_cancel`,
`test_reproduction_female_required`, `test_reproduction_female_sex`,
`test_reproduction_male_sex`, `test_reproduction_species_coherence`,
`test_reproduction_site_farm_coherence`, `test_reproduction_date_before_birth`,
`test_reproduction_direct_state_write_forbidden`, `test_reproduction_delete_draft_allowed`,
`test_reproduction_delete_confirmed_forbidden`, `test_reproduction_dead_animal_forbidden`.

**Gestations (16)**
`test_gestation_creation`, `test_gestation_expected_birth_date_computed`,
`test_gestation_no_duration_leaves_expected_empty`,
`test_gestation_duplicate_for_event_forbidden`, `test_gestation_female_coherence`,
`test_gestation_date_before_event`, `test_gestation_expected_before_start`,
`test_gestation_confirm`, `test_gestation_terminate`, `test_gestation_abort`,
`test_gestation_interrupt`, `test_gestation_locked_after_terminate`,
`test_gestation_direct_state_write_forbidden`, `test_gestation_delete_to_confirm_allowed`,
`test_gestation_delete_confirmed_forbidden`, `test_species_incoherent_duration_refused`.

**Mises bas et naissances (13)**
`test_birth_creation`, `test_birth_counts_coherence`, `test_birth_negative_counts`,
`test_birth_multiple`, `test_birth_validate`, `test_birth_validate_terminates_gestation`,
`test_birth_direct_state_write_forbidden`, `test_birth_father_species_coherence`,
`test_birth_create_newborn_animals`, `test_birth_newborn_requires_sex`,
`test_birth_newborn_existing_animal_coherence`, `test_birth_delete_draft_allowed`,
`test_birth_delete_validated_forbidden`.

**Mortalité (12)**
`test_mortality_individual_creation`, `test_mortality_requires_animal_or_lot`,
`test_mortality_animal_or_lot_exclusive`, `test_mortality_validate_sets_animal_dead`,
`test_mortality_duplicate_individual_forbidden`, `test_mortality_lot_creation`,
`test_mortality_lot_count_positive`, `test_mortality_lot_count_exceeds`,
`test_mortality_lot_duplicate_forbidden`, `test_mortality_direct_state_write_forbidden`,
`test_mortality_delete_draft_allowed`, `test_mortality_delete_validated_forbidden`.

**Indicateurs / intégration (5)**
`test_animal_reproduction_indicators`, `test_animal_birth_indicators`,
`test_animal_mortality_indicators`, `test_lot_mortality_indicator`,
`test_reproduction_linked_to_health_integration`.

**Sécurité / isolation (4)**
`test_reproduction_isolation`, `test_gestation_isolation`, `test_mortality_isolation`,
`test_birth_isolation`.

Les tests vérifient le comportement métier réel (refus effectifs, transitions d'état,
cohérence des compteurs, création effective des animaux, isolation des exploitations) et
non de simples assertions de surface.

**Décompte exact :** 13 (événements reproductifs) + 16 (gestations) + 13 (mises bas) +
12 (mortalité) + 5 (indicateurs) + 4 (sécurité) = **63 tests**.

---

## 9. Résultats des tests de régression

```
Commande : --test-enable --test-tags /gestion_agricole:TestLivestock,/gestion_agricole:TestFeeding,/gestion_agricole:TestHealth
Résultat : 0 failed, 0 error(s) of 133 tests when loading database 'odoo20'
```

| Suite | Domaine | Résultat |
|---|---|---|
| `TestLivestock` | Animaux et lots | 0 échec / 0 erreur |
| `TestFeeding` | Alimentation animale | 0 échec / 0 erreur |
| `TestHealth` | Santé animale | 0 échec / 0 erreur |

**Total régression : 133 tests, 0 échec, 0 erreur.** Aucune régression introduite.

---

## 10. Résultat de la compilation Python

```
/etc/odoo20-venv/bin/python -m py_compile \
  models/reproduction/*.py \
  models/configuration/livestock_species.py \
  tests/test_reproduction.py
=> PY_COMPILE_OK
```

**Compilation réussie**, aucune erreur de syntaxe.

---

## 11. Résultat de la validation XML

```
xml.dom.minidom.parse('views/reproduction_views.xml')      => XML OK
xml.dom.minidom.parse('data/ir_sequence_reproduction.xml') => XML OK
```

**XML valides.** Le chargement effectif des vues par Odoo (section 12) confirme en outre
leur validité sémantique.

---

## 12. Résultat du chargement du registre

Chargement du registre (`Registry.new("odoo20")`) puis vérification programmatique :

- **5 modèles** présents ;
- **12 champs** d'extension `gest_agri.animal` présents ;
- champ `gestation_duration_days` présent sur l'espèce ;
- **16 vues**, **5 actions**, **6 menus** résolus par xmlid ;
- **15 lignes ACL** (3 × 5 modèles) avec opérations et domaines attendus ;
- **4 séquences** présentes.

**Registre chargé sans erreur.**

---

## 13. Résultat de la mise à jour sur `odoo20`

Mise à jour du seul module `gestion_agricole` sur la seule base `odoo20`, via le
contournement neutre documenté (le problème préexistant de `IrModuleModule.update_list`
n'a pas été corrigé au niveau système) :

```
/etc/odoo20-venv/bin/python /tmp/opencode/update_noupdatelist.py
=> REGISTRY RC = 0
```

**Mise à jour réussie (RC = 0), aucune `ParseError`, aucune erreur de vue.**

---

## 14. Vérification de synchronisation des deux copies

```
diff -rq /tmp/opencode/dev/gestion_agricole \
         /mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole \
         -x __pycache__ -x "*.pyc"
=> NO DIFFERENCES
```

Les deux copies sont **strictement identiques**, à l'exception du fichier préexistant
`RAPPORT_PROMPT_55_BIS_FINAL.md` présent uniquement dans la copie installée (étranger à ce
prompt, non écrasé). Aucune modification étrangère n'a été touchée.

---

## 15. Difficultés rencontrées et réserves éventuelles

1. **Champs calculés non stockés dans un domaine de recherche.** La première mise à jour a
   échoué (`REGISTRY RC = -1`) avec une `ParseError` sur `views/reproduction_views.xml` :
   le filtre de recherche `with_repro` utilisait `reproduction_count`, champ calculé non
   stocké, impossible à rechercher. **Correction :** les 12 indicateurs de reproduction et
   de mortalité de `gest_agri.animal` ont été passés en `store=True` (ce qui est de toute
   façon nécessaire pour les filtres et regroupements statistiques). Nouvelle mise à jour :
   `RC = 0`.

2. **Unicité par index PostgreSQL et type d'exception.** Le test
   `test_gestation_duplicate_for_event_forbidden` échouait initialement car l'index unique
   PostgreSQL (`models.UniqueIndex`) est levé à l'INSERT, **avant** la contrainte Python,
   et propage une `psycopg2.errors.UniqueViolation` au niveau ORM. Ce comportement est
   **documenté et déjà géré** dans le module (cf. `tests/test_patrimony.py`) : le test
   accepte désormais `(ValidationError, psycopg2.errors.UniqueViolation)`. Au niveau web,
   Odoo convertit cette erreur en `ValidationError` (message métier affiché à l'utilisateur).

3. **Contournement `update_list`.** Le blocage préexistant de `IrModuleModule.update_list`
   a de nouveau nécessité le script de contournement
   `/tmp/opencode/update_noupdatelist.py` (monkeypatch neutre de `update_list` → `[0, 0]`,
   puis `Registry.new(..., update_module=True, upgrade_modules=["gest_agricole"])`). Ce
   contournement est **local, non généralisé** et n'a pas été propagé au code du module.

**Réserve :** l'extension PostgreSQL `btree_gist` n'est pas installée dans `odoo20` ; le
mécanisme de réservation d'unicité des référentiels reste donc **inerte**, comme lors des
prompts précédents. Cette situation est connue, isolée, et sans impact sur les
fonctionnalités de reproduction développées ici.

---

## 16. Fonctionnalités restant à développer

Conformément au périmètre exclu du Prompt 63, restent à traiter dans des prompts distincts :

- Production laitière.
- Production de viande.
- Production d'œufs.
- Transformation des produits animaux.
- Comptabilité et rentabilité détaillée de l'élevage.

---

**Mention finale :**

PROMPT 63 VALIDÉ ET CLÔTURÉ
