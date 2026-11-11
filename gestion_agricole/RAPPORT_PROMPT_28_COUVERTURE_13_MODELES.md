# RAPPORT PROMPT N°28 — COUVERTURE DES 13 MODÈLES

## Module `gestion_agricole` — Odoo 20 Community

### Matrice des opérations

| Modèle | create | write code | write name | write company | archive | reactivate | unlink | copy | import | load | multi-create | rollback |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `farm.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `soil.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `crop.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `crop.variety` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `livestock.species` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `livestock.breed` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `operation.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `treatment.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `fertilizer.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `irrigation.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `equipment.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `building.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |
| `production.type` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | couvert | couvert | couvert | ✅ | ✅ |

✅ = testé directement
couvert = couvert par le mécanisme commun (passe par `create`/`write`)

### Cycle de vie

13/13 modèles : create→2, archive→0, reactivate→2, delete→0 (script réexécuté).

---

*Rapport — Prompt N°28 — Phase E — Module `gestion_agricole`.*
