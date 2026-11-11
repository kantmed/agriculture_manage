# ANNEXE 2 — NORMALISATION ET UNICITÉ

## Règle métier officielle

Normalisation Python : `value.strip().casefold()` (fonction `normalize_reference`
dans `_common.py`).

## Identité des chemins

- Création ORM : utilise `normalize_reference()` ✅
- Modification ORM : utilise `normalize_reference()` ✅
- Import : passe par `create` → `normalize_reference()` ✅
- Copie : passe par `create` → `normalize_reference()` ✅
- Écritures SQL directes : hors ORM → pas de normalisation → contournement possible

## Contrainte PostgreSQL

- Index unique : `LOWER(BTRIM(code))` — différent de `casefold()`.
- Contrainte GiST : utilise la colonne `normalized` (Python) — identique à Python.

## Matrice de 10 cas

Voir Rapport 21, section 3.4. Résultats confirmés par exécution directe
(Python et SQL).

## Architecture proposée

Option A (colonne normalisée stockée) recommandée. Non implémentée.

## Divergences

- Python plus strict pour tabs, ß, ẞ.
- SQL plus strict pour İ.
- Aucun doublon ne passe (au moins l'un des deux bloque).
