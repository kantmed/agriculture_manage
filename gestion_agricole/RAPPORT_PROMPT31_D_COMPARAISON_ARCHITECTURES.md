# RAPPORT PROMPT 31 — COMPARAISON DES ARCHITECTURES

## Module `gestion_agricole` — Odoo 20 Community

### 1. Option 1 — Utiliser directement `gest_agri_audit_test`

| Critère | Évaluation |
|---|---|
| Isolation production | Faible (même rôle propriétaire) |
| Propriété des objets | Problématique (objets appartiennent à `odoo20`) |
| Compatibilité Odoo | Bonne |
| Mises à jour des modules | Possible (propriétaire de la base) |
| Séquences | Accessibles |
| Extensions | `btree_gist` déjà installée |
| Sauvegarde/restauration | Simple |
| Filestore | Partagé avec production (même `data_dir`) |
| Risque opérationnel | Moyen (même base, même rôle) |
| Facilité de maintenance | Bonne |

### 2. Option 2 — Créer une nouvelle base `gest_agri_dev_db`

| Critère | Évaluation |
|---|---|
| Isolation production | Élevée (base distincte) |
| Propriété des objets | Bonne (restauration avec propriétaire dédié) |
| Compatibilité Odoo | Bonne |
| Mises à jour des modules | Possible (rôle propriétaire) |
| Séquences | Accessibles |
| Extensions | `btree_gist` à installer (disponible v1.8) |
| Sauvegarde/restauration | Plus complexe |
| Filestore | Indépendant |
| Risque opérationnel | Faible |
| Facilité de maintenance | Moyenne |

### 3. Recommandation

**Option 2 recommandée.** Elle offre une meilleure isolation et une propriété
claire des objets. La sauvegarde/restauration de `gest_agri_audit_test` vers
`gest_agri_dev_db` est réalisable avec `pg_dump`/`pg_restore`.

---

*Rapport — Prompt 31 — Phase D — Module `gestion_agricole`.*
