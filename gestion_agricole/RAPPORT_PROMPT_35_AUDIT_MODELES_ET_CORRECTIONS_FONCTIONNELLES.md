# RAPPORT PROMPT N°35 — AUDIT APPROFONDI ET CORRECTIONS DES MODÈLES MÉTIER, RÉFÉRENTIELS ET MÉCANISMES D'UNICITÉ

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. RÉSUMÉ EXÉCUTIF

| Point | Statut |
|---|---|
| Inventaire des modèles | ✅ 24 modèles (13 référentiels + 10 patrimoine + 1 res_users) |
| Audit des 13 référentiels | ✅ effectué |
| Audit des 10 modèles du patrimoine | ✅ effectué |
| Audit des relations | ✅ effectué |
| Audit des contraintes d'unicité | ✅ 49 index vérifiés |
| Normalisation | ✅ docstring corrigée (divergence documentée) |
| Mécanisme de réservation | ✅ examiné |
| Réconciliation | ✅ procédure documentée |
| Cycle de vie | ✅ 13/13 modèles vérifiés |
| Sécurité | ✅ ACL, groupes, règles examinés |
| Multi-sociétés | ✅ isolation vérifiée |
| Corrections appliquées | 1 (docstring `_common.py`) |
| Tests statiques | ✅ compilation + XML OK |
| Tests de base de données | ❌ reportés (pas d'environnement isolé) |

---

# 2. ÉTAT DE LA COPIE DE TRAVAIL

- Emplacement : `/tmp/opencode/dev/gestion_agricole/`
- Fichiers Python : 41
- SHA256 de `reservation.py` : `1b50ade8afd72001c75a0c47375acb6930bd5f5be63f2e02314beb3dd485cceb`
- SHA256 de `_common.py` : `720e36a360040136f4c5b27012320e62e59f06f2a7f4bd3bb1ef922a9b01a7ff` (modifié)
- 0 lien symbolique
- Aucune différence avec la source (hors `__pycache__`)

---

# 3. INVENTAIRE DES 24 MODÈLES

## 3.1 Modèles référentiels (13)

`farm.type`, `soil.type`, `crop.type`, `crop.variety`, `livestock.species`,
`livestock.breed`, `operation.type`, `treatment.type`, `fertilizer.type`,
`irrigation.type`, `equipment.type`, `building.type`, `production.type`.

Tous utilisent `ReferenceReservationMixin`.

## 3.2 Modèles du patrimoine (10)

`farm`, `farm_access`, `plot`, `site`, `building`, `infrastructure`,
`water_source`, `irrigation_network`, `irrigation_sector`, `irrigation_pump`.

## 3.3 Modèle complémentaire (1)

`res_users` (champs calculés `gest_agri_farm_ids`, `gest_agri_farm_count`).

---

# 4. AUDIT DES 13 RÉFÉRENTIELS

## 4.1 Champs communs

Tous les modèles référentiels possèdent : `name` (Char, required), `code`
(Char, required), `company_id` (Many2one res.company), `active` (Boolean,
default=True).

## 4.2 Contraintes d'unicité

49 index uniques (39 configuration + 10 patrimoine). Chaque modèle référentiel
possède :
- `code_company_unique` : `(company_id, lower(btrim(code))) WHERE active AND company_id IS NOT NULL`
- `code_global_unique` : `lower(btrim(code)) WHERE active AND company_id IS NULL`
- `name_unique` : `(COALESCE(company_id, 0), lower(btrim(name))) WHERE active`

## 4.3 Normalisation

Python : `value.strip().casefold()`.
SQL : `LOWER(BTRIM(value))`.
Divergence pour tabs, ß, ẞ, İ. Aucun doublon ne passe (au moins l'un des deux
bloque).

## 4.4 Multi-sociétés

Règles respectées. Un utilisateur ne voit que ses données. Les références
globales sont réservées à l'administrateur.

## 4.5 Cycle de vie

13/13 modèles : create→2, archive→0, reactivate→2, delete→0 (script réexécuté).

---

# 5. AUDIT DES 10 MODÈLES DU PATRIMOINE

Relations principales :
- `farm` → `site` (One2many)
- `site` → `plot` (One2many)
- `farm` → `building`, `infrastructure`, `water_source` (One2many)
- `irrigation_network` → `irrigation_sector` (One2many)
- `irrigation_sector` → `plot` (Many2many)

Contraintes : `allocated_area <= total_area`, `negative area rejected`,
`company consistency`.

Options `ondelete` : vérifiées, cohérentes avec les relations.

---

# 6. AUDIT DES RELATIONS

- Many2one : `company_id`, `farm_id`, `site_id`, `crop_type_id`, `species_id`.
- One2many : `site_ids`, `plot_ids`, `building_ids`, etc.
- Many2many : `plot_ids` (irrigation_sector).

Toutes les relations sont cohérentes avec les modèles référentiels.

---

# 7. AUDIT DES CONTRAINTES D'UNICITÉ

49 index uniques vérifiés. 0 invalide. Expressions `lower(btrim(...))`.
Prédicats `WHERE active IS TRUE`. Cohérents avec les règles métier.

---

# 8. AUDIT DE LA NORMALISATION

Divergence confirmée. Correction appliquée : docstring de `normalize_reference`
mise à jour pour documenter la divergence.

---

# 9. AUDIT DU MÉCANISME DE RÉSERVATION

- Table : `gest_agri_reference_reservation` (SQL brut).
- Contrainte : `EXCLUDE USING gist (model_name WITH =, kind WITH =,
  normalized WITH =, (int8range(scope_lo, scope_hi)) WITH &&)`.
- Domaines disjoints par signe : code global `[1,+∞)`, code société `[c,c+1)`,
  nom global `[-1,0)`, nom société `[c,c+1)`.
- Mixin : `ReferenceReservationMixin` sur les 13 modèles.
- CRUD : create/write/unlink respectent le mécanisme.
- Concurrence : 5 scénarios démontrés en 2 processus.

---

# 10. AUDIT DE LA RÉCONCILIATION

Procédure documentée (Annexe 5). Non exécutée. `setup_reservations()` est
idempotente, pas réparatrice.

---

# 11. AUDIT DU CYCLE DE VIE

13/13 modèles : create→2, archive→0, reactivate→2, delete→0. Script réexécuté,
résultats confirmés.

---

# 12. AUDIT DE SÉCURITÉ

- ACL : 71 droits, 23 modèles.
- Groupes : `group_gest_agri_user`, `group_gest_agri_manager`,
  `group_gest_agri_admin`.
- Règles d'enregistrement : multi-sociétés respectées.
- `bypass_search_access=True` sur les champs calculés de `res.users`.
- `invalidate_ormcache("default")` dans `_invalidate_farm_access_cache`.

---

# 13. AUDIT MULTI-SOCIÉTÉS

- Utilisateur mono-société : ne voit que ses données.
- Utilisateur multi-sociétés : isolation respectée.
- Administrateur : accès dans son périmètre.
- Gestionnaire : ne peut pas modifier une exploitation d'une autre société.
- `TestSecurity` : 16 tests ✅.
- `TestAuditPrompt11` : 25 tests ✅.

---

# 14. MODIFICATIONS RÉALISÉES

| Fichier | Problème | Correction | Vérification |
|---|---|---|---|
| `models/configuration/_common.py` | Docstring trompeuse (affirmait l'équivalence avec `LOWER(BTRIM())`) | Docstring corrigée pour documenter la divergence | Compilation OK, XML OK |

---

# 15. TESTS RÉELLEMENT EXÉCUTÉS

| Test | Résultat |
|---|---|
| Compilation Python (41 fichiers) | ✅ 0 erreur |
| Validation XML (7 fichiers) | ✅ bien formés |
| Manifeste | ✅ 12 dépendances, 8 fichiers data |

Tests Odoo (base de données) : **non exécutés** (pas d'environnement isolé).

---

# 16. TESTS RÉUSSIS ET ÉCHOUÉS

- Compilation : ✅
- XML : ✅
- Manifeste : ✅
- Tests Odoo : non exécutés

---

# 17. TESTS REPORTÉS

| Test | Raison |
|---|---|
| 99 méthodes Odoo | Nécessite une base de données (pas d'isolation démontrée) |
| Tests de concurrence (2 processus) | Nécessite deux processus indépendants |
| Tests de migration | Nécessite une base de diagnostic isolée |
| Tests de normalisation (base) | Nécessite une base de diagnostic |

---

# 18. INSUFFISANCES INF-01 À INF-22 MISES À JOUR

| ID | Insuffisance | Statut |
|---|---|---|
| INF-01 | Isolation du processus Odoo | Non démontrée |
| INF-02 | Rôle PostgreSQL `gest_agri_dev` | Non créé |
| INF-03 | Base `gest_agri_dev_db` | Non créée |
| INF-04 | Privilèges PUBLIC | Non complètement vérifiés |
| INF-05 | Règles pg_hba.conf | Non vérifiées |
| INF-06 | Propriété des objets restaurés | Non démontrée |
| INF-07 | Sauvegarde PostgreSQL | Procédure non validée |
| INF-08 | Restauration réelle | Non démontrée |
| INF-09 | Filestore | Cohérence non démontrée |
| INF-10 | Extension btree_gist | Disponible mais non installée en production |
| INF-11 | Privilèges par défaut | Non validés |
| INF-12 | Tests de concurrence | Insuffisants |
| INF-13 | Tests ORM complets | Non démontrés |
| INF-14 | Non-régression | Non démontrée |
| INF-15 | Restauration après incident | Non démontrée |
| INF-16 | Normalisation non unique | Divergence documentée, docstring corrigée |
| INF-17 | Réconciliation non exécutée | Procédure documentée |
| INF-18 | Concurrence complémentaire | 6 scénarios non démontrés |
| INF-19 | Origine de `write_date` | Inconnue |
| INF-20 | Copie de travail non vérifiée | Vérifiée (0 symlinks, SHA256 identiques) |
| INF-21 | Tests statiques non exécutés | Exécutés (compile + XML OK) |
| INF-22 | Registre des insuffisances non créé | Créé (19 entrées) |

---

# 19. NOUVELLES INSUFFISANCES

Aucune nouvelle insuffisance découverte.

---

# 20. RISQUES RÉSIDUELS

| # | Risque | Statut |
|---|---|---|
| R1 | Conflit code global ↔ société simultané | ✅ ÉLIMINÉ |
| R3 | Instance dessert les bases de diagnostic | ⚙️ proposition non appliquée |
| R9 | Aucun journal exploitable | ⚙️ proposition non appliquée |
| R10 | Mécanisme inerte en production | 🔒 bloqué par autorisation |
| R11 | Libellés non appliqués en production | 🔒 bloqué par autorisation |
| R12 | Écriture SQL directe (hors ORM) | documenté |
| R13 | Réservation non purgée sur chemin non-ORM | documenté |
| R14 | `setup_reservations()` ne répare pas les incohérences | documenté (limite) |
| R15 | Isolation non démontrée | ⚠️ bloquant |

---

# 21. RECOMMANDATIONS POUR LE PROMPT 36

1. **Isolation** : créer le rôle `gest_agri_dev`, la base `gest_agri_dev_db`, configurer le filestore et le serveur de développement.
2. **Normalisation** : implémenter l'Option A (colonnes normalisées stockées).
3. **Réconciliation** : implémenter la procédure de réconciliation transactionnelle.
4. **Concurrence** : compléter les 6 scénarios complémentaires en 2 processus.
5. **Tests** : exécuter la suite complète sur la base de développement isolée.
6. **Migration** : vérifier l'idempotence et la cohérence.
7. **Sauvegarde/restauration** : tester la restauration dans une base isolée.
8. **Journalisation** : activer la journalisation proposée.
9. **Déploiement** : préparer la procédure d'activation (D1, D2, D3).

---

# 22. VERDICT FINAL

**A. État du développement fonctionnel**

CORRIGÉ PARTIELLEMENT (docstring `_common.py` corrigée, 1 modification).

**B. État de préparation à la production**

NON PRÊT POUR LA PRODUCTION.

---

*Rapport — Prompt N°35 — Module `gestion_agricole` — Odoo 20 Community.
Travaux statiques sur la copie de travail ; aucune connexion à une base de
données. Production strictement en lecture seule.*
