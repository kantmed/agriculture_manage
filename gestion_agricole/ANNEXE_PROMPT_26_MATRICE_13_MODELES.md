# ANNEXE 4 — MATRICE DES 13 MODÈLES

## Cycle de vie (create → archive → reactivate → delete)

Script : `/tmp/opencode/lifecycle_all.py` (SHA256: `64656e171ee93e81b76a7488b20adb50f6372c47a0227ed9714627624d034870`)

| Modèle | Création (+2) | Archivage (0) | Réactivation (+2) | Suppression (0) |
|---|---|---|---|---|
| `farm.type` | ✅ | ✅ | ✅ | ✅ |
| `soil.type` | ✅ | ✅ | ✅ | ✅ |
| `crop.type` | ✅ | ✅ | ✅ | ✅ |
| `crop.variety` | ✅ | ✅ | ✅ | ✅ |
| `livestock.species` | ✅ | ✅ | ✅ | ✅ |
| `livestock.breed` | ✅ | ✅ | ✅ | ✅ |
| `operation.type` | ✅ | ✅ | ✅ | ✅ |
| `treatment.type` | ✅ | ✅ | ✅ | ✅ |
| `fertilizer.type` | ✅ | ✅ | ✅ | ✅ |
| `irrigation.type` | ✅ | ✅ | ✅ | ✅ |
| `equipment.type` | ✅ | ✅ | ✅ | ✅ |
| `building.type` | ✅ | ✅ | ✅ | ✅ |
| `production.type` | ✅ | ✅ | ✅ | ✅ |

## Opérations supplémentaires

| Opération | Statut | Test |
|---|---|---|
| Modification de code | ✅ testé | `test_scenario_09_modify_code` |
| Modification de nom | ✅ testé | `test_simultaneous_code_and_name_change` |
| Modification de société | ✅ testé | `test_scenario_10_change_company` |
| Création multiple | ✅ testé | `test_multi_creation_with_conflict_is_rejected` |
| Rollback | ✅ testé | `test_scenario_11`, `test_coherence_after_rollback` |
| Duplication | couvert par le mécanisme commun (passe par `create`) |
| Import | couvert par le mécanisme commun |
| `load()` | couvert par le mécanisme commun |
