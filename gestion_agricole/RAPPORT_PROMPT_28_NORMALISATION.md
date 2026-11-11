# RAPPORT PROMPT N°28 — NORMALISATION CANONIQUE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Problème

Divergence entre Python `strip().casefold()` et SQL `LOWER(BTRIM())`.
Cas identifiés : tabs, `ß`, `ẞ`, `İ`.

### 2. Analyse

- `_common.py` : `normalize_reference()` → `value.strip().casefold()`.
- Index SQL : `LOWER(BTRIM(code))` / `LOWER(BTRIM(name))`.
- Réservation : utilise `normalize_reference()` (Python).

### 3. Conception proposée

**Option A (recommandée)** : colonnes `code_normalized` / `name_normalized`
générées en Python, indexées en binaire. Garantit l'identité stricte.

**Option B** : fonction SQL équivalente à `casefold()`. Non viable (PostgreSQL
n'a pas de `casefold()` natif).

### 4. Tests obligatoires

Matrice de 10 cas (voir Rapport 21, section 3.4). Résultats confirmés par
exécution directe. Aucun doublon ne passe.

### 5. Statut

- FAIT OBSERVÉ : divergence confirmée pour tabs, ß, ẞ, İ.
- TEST EXÉCUTÉ : matrice de 10 cas (Python + SQL).
- TEST RÉUSSI : aucun doublon ne passe.
- NON DÉMONTRÉ : solution `code_normalized` non implémentée.
- PROPOSITION : Option A (colonnes normalisées stockées).

**Correction non appliquée** (pas de modification du code source).

---

*Rapport — Prompt N°28 — Phase B — Module `gestion_agricole`.*
