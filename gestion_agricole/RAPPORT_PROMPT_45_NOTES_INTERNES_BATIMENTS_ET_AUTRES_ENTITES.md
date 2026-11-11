# RAPPORT PROMPT N°45 — NOTES INTERNES DES BÂTIMENTS ET IDENTIFICATION DES AUTRES ENTITÉS

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. RÉSULTAT — BÂTIMENTS AGRICOLES

- Aucun champ `notes` n'existait sur `gest_agri.building` (seul `description`).
- Champ `notes` ajouté (`fields.Text`, « Notes internes », facultatif, vide par défaut).
- Aide : « Observations et informations complémentaires relatives au bâtiment agricole. »
- Onglet dédié « Notes internes » ajouté dans le formulaire, après le champ `description`, sans modifier les groupes existants.
- Aucune contrainte, aucun `tracking`, aucun affichage en liste/recherche.

---

# 2. FICHIERS MODIFIÉS

| Fichier | Modification |
|---|---|
| `models/patrimony/building.py` | Champ `notes` |
| `models/patrimony/infrastructure.py` | Champ `notes` |
| `models/patrimony/water_source.py` | Champ `notes` |
| `models/patrimony/irrigation_network.py` | Champ `notes` |
| `models/patrimony/irrigation_sector.py` | Champ `notes` |
| `models/patrimony/irrigation_pump.py` | Champ `notes` |
| `views/patrimony_views.xml` | Onglet « Notes internes » : bâtiment, infrastructure, source d'eau |
| `views/irrigation_views.xml` | Onglet « Notes internes » : réseau, secteur, pompe |
| `tests/test_patrimony.py` | 3 tests ajoutés |

Tous les fichiers ont été répliqués à l'identique dans
`/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/` et vérifiés par `diff -q`.

---

# 3. EXAMEN DES MODÈLES — DÉCISIONS

## 3.1 Modèles retenus (champ `notes` ajouté)

| Modèle | Justification |
|---|---|
| `gest_agri.building` | Bâtiment réel de l'exploitation ; observations de maintenance/état non couvertes par `description` descriptif. **Exigence explicite du prompt.** |
| `gest_agri.infrastructure` | Ouvrage physique (piste, clôture, drainage) ; observations de terrain utiles. |
| `gest_agri.water.source` | Ressource hydraulique réelle ; observations de débit, qualité, entretien. |
| `gest_agri.irrigation.network` | Équipement opérationnel ; observations de fonctionnement/incidents. |
| `gest_agri.irrigation.sector` | Sous-ensemble opérationnel d'irrigation ; observations localisées. |
| `gest_agri.irrigation.pump` | Équipement réel ; observations de maintenance et de performance. |

Ces six entités sont des **éléments physiques et opérationnels du patrimoine**,
conformes aux critères favorables du prompt. L'ajout reste simple et cohérent
avec `site`, `farm` et `plot`.

## 3.2 Modèles ayant déjà `notes` (aucune action)

| Modèle | État |
|---|---|
| `gest_agri.farm` | `notes` présent (Prompt 43) |
| `gest_agri.site` | `notes` présent (Prompt 42) |
| `gest_agri.plot` | `notes` présent (Prompt 44) |

## 3.3 Modèles écartés

| Modèle | Raison de l'exclusion |
|---|---|
| `gest_agri.building.type` | Référentiel technique (type). |
| `gest_agri.crop.type` | Référentiel technique (type de culture). |
| `gest_agri.crop.variety` | Référentiel technique (variété). |
| `gest_agri.equipment.type` | Référentiel technique (type d'équipement). |
| `gest_agri.farm.type` | Référentiel technique ; `description` + `help` déjà enrichis (Prompt 41). |
| `gest_agri.fertilizer.type` | Référentiel technique (type d'engrais). |
| `gest_agri.irrigation.type` | Référentiel technique (mode d'irrigation). |
| `gest_agri.livestock.breed` | Référentiel technique (race). |
| `gest_agri.livestock.species` | Référentiel technique (espèce). |
| `gest_agri.operation.type` | Référentiel technique (type d'opération). |
| `gest_agri.production.type` | Référentiel technique (type de production). |
| `gest_agri.soil.type` | Référentiel technique (type de sol). |
| `gest_agri.treatment.type` | Référentiel technique (type de traitement). |
| `gest_agri.farm.access` | Modèle de ligne de droits d'accès : écarté pour ce prompt (les observations générales appartiennent à l'exploitation) ; un besoin de justification propre à chaque habilitation reste à valider. |
| `res.users` (héritage) | Modèle technique natif Odoo ; hors périmètre métier. |
| Mixin / table de réservation | Composant purement technique (unicité référentielle), sans usage utilisateur. |

Chaque référentiel possède déjà un champ `description` ; ajouter un second champ
libre aurait constitué une multiplication inutile.

## 3.4 Domaines non encore implémentés

Le module ne contient actuellement **aucun modèle** pour : matériel/équipements
opérationnels, stocks et entrepôts, intrants, cultures et productions, opérations
et interventions, main-d'œuvre, campagnes, achats et suivi économique. Seuls
leurs **référentiels** existent. Aucun champ n'a donc pu être ajouté à ces
domaines ; ils seront traités lors de leur implémentation effective.

---

# 4. TESTS AJOUTÉS

| Test | Vérifications |
|---|---|
| `test_building_notes_default_and_modification` | Valeur vide par défaut, modification, conservation après `browse`, remise à vide |
| `test_building_creation_with_notes` | Création directe d'un bâtiment avec notes |
| `test_notes_on_other_patrimony_assets` | Pour infrastructure, source d'eau, réseau, secteur, pompe : valeur vide par défaut, écriture, persistance après relecture, remise à vide (sous-tests) |

Résultats : les trois tests ont démarré et n'apparaissent dans aucune erreur →
**réussis**.

---

# 5. CONTRÔLES STATIQUES

| Contrôle | Résultat |
|---|---|
| Compilation Python (`compileall`) | ✅ 0 erreur |
| Validation XML (7 fichiers) | ✅ bien formés |
| Analyse AST du fichier de tests | ✅ OK |
| Manifeste | ✅ inchangé |

---

# 6. MISE À JOUR ODOO

Vérifications : base `odoo20` / utilisateur `odoo20` / port 5433, module `installed`,
exécution autonome `--no-http --max-cron-threads=0 --stop-after-init`, `-d odoo20`
uniquement, service partagé non redémarré.

Commande exécutée :
```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init -u gestion_agricole
```

Résultat : **EXIT=0**.

Colonnes vérifiées en base (toutes présentes, type `text`) :
`gest_agri_building.notes`, `gest_agri_infrastructure.notes`,
`gest_agri_water_source.notes`, `gest_agri_irrigation_network.notes`,
`gest_agri_irrigation_sector.notes`, `gest_agri_irrigation_pump.notes`.

Module : `installed`, version `20.0.1.0.0`, `write_date` `2026-11-11 07:35:36`.

---

# 7. TESTS ODOO

Commande exécutée :
```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
```

Résultat global :
```
0 failed, 27 error(s) of 117 tests when loading database 'odoo20'
```

| Catégorie | Nombre |
|---|---|
| Tests exécutés | 117 |
| Réussis | 90 |
| Échoués (`failed`) | 0 |
| En erreur (`errors`) | 27 |
| Non exécutés | 0 |

Les 27 erreurs sont **exclusivement** les tests de réservation
(`test_reservation_unicity` : 26, `test_audit_prompt11` : 1), dues à l'absence
de `gest_agri_reference_reservation` (`btree_gist` non installé). Aucune erreur
hors réservation.

---

# 8. DIFFICULTÉS / DÉCISIONS EN ATTENTE

- Aucune difficulté technique.
- Aucune décision métier bloquante.
- Les domaines opérationnels non encore modélisés (matériel, stocks, intrants,
  cultures, opérations, main-d'œuvre, campagnes, achats) ne peuvent recevoir de
  `notes` tant que leurs modèles n'existent pas ; à traiter lors de leur création.

---

# 9. CONFIRMATION DE NON-INTERVENTION

- Seule la base `odoo20` mise à jour ; aucune autre base touchée.
- `/etc/odoo20.conf` non modifié ; rôles et permissions PostgreSQL inchangés.
- Aucune permission système modifiée.
- Aucun service Odoo partagé redémarré ; Odoo 16 non touché.
- `btree_gist` non installé ; les 27 erreurs historiques restent isolées.

---

# 10. PROPOSITION POUR LE PROMPT 46

**Prompt 46** : Ajouter un champ `notes` (Text, « Notes internes ») au modèle
`gest_agri.farm.access` (Droit d'accès à une exploitation), afin de permettre
de justifier les habilitations accordées (motif, périmètre, échéance), avec
affichage dans le formulaire de l'exploitation et tests ciblés.

---

*Rapport — Prompt N°45 — Module `gestion_agricole` — Odoo 20 Community.
Neuvième évolution fonctionnelle. Développement dans la copie de travail,
mise à jour et tests réels sur `odoo20`.*
