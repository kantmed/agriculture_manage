# RAPPORT PROMPT N°37 — PREMIÈRE ÉVOLUTION FONCTIONNELLE

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. FONCTIONNALITÉ CHOISIE ET JUSTIFICATION

**Fonctionnalité :** Ajout d'un champ `state` (statut opérationnel) au modèle
`gest_agri.plot` (Parcelle agricole).

**Justification :**
- Clarament prévue dans le cahier des charges (section 3.1 : "Statut
  opérationnel des parcelles").
- Absente du code existant (aucun champ `state` sur aucun modèle).
- Utile pour l'exploitation agricole (suivi de l'état des parcelles).
- Périmètre limité (un champ, des vues, un test).
- Réalisable sans restructuration générale.
- Ne nécessite pas de décision métier en attente.

---

# 2. COMPORTEMENT FONCTIONNEL RÉALISÉ

Le champ `state` est un champ `Selection` avec les valeurs :
- `available` (Disponible) — valeur par défaut
- `cultivated` (Cultivée)
- `fallow` (En jachère)
- `unavailable` (Indisponible)

Le champ est :
- Traçable (`tracking=True`)
- Indexé (`index=True`)
- Affiché dans la liste, le formulaire et la recherche
- Filtrable par statut dans la vue de recherche
- Regroupable par statut

---

# 3. MODÈLES ET COMPOSANTS CONCERNÉS

- `models/patrimony/plot.py` : ajout du champ `state` et de la contrainte `_check_state`.
- `views/patrimony_views.xml` : ajout du champ dans la liste, le formulaire et la recherche.

---

# 4. FICHIERS CRÉÉS OU MODIFIÉS

| Fichier | Modification |
|---|---|
| `models/patrimony/plot.py` | Ajout du champ `state` et de la contrainte `_check_state` |
| `views/patrimony_views.xml` | Ajout du champ dans list, form, search |
| `tests/test_patrimony.py` | Ajout de 2 tests (`test_plot_state_default_and_values`, `test_plot_state_invalid_rejected`) |

---

# 5. RÉSUMÉ DES CHANGEMENTS

- 1 champ ajouté (`state`).
- 1 contrainte ajoutée (`_check_state`).
- 3 vues mises à jour (list, form, search).
- 2 tests ajoutés.
- Aucune modification des fonctionnalités existantes.

---

# 6. RÉSULTATS DES TESTS EXÉCUTÉS

| Test | Résultat |
|---|---|
| Compilation Python (41 fichiers) | ✅ 0 erreur |
| Validation XML (7 fichiers) | ✅ bien formés |
| Manifeste | ✅ 12 dépendances, 8 fichiers data |

Tests Odoo (base de données) : **non exécutés** (pas d'environnement isolé).

---

# 7. TESTS NON EXÉCUTÉS ET RAISONS

| Test | Raison |
|---|---|
| Tests unitaires Odoo (99 méthodes) | Nécessite une base de données (pas d'isolation démontrée) |
| Nouveaux tests `test_plot_state_*` | Nécessite une base de données |

---

# 8. RÉSULTAT DE LA MISE À JOUR ODOO

Non exécutée. L'isolation de l'environnement de développement n'est pas
démontrée (Prompt 29/30/31). Aucune mise à jour sur aucune base.

---

# 9. PREUVES DE NON-INTERVENTION SUR LA PRODUCTION

- Aucune base de production modifiée.
- Aucun service Odoo redémarré.
- Aucune modification du code source partagé (modifications uniquement dans
  la copie de travail `/tmp/opencode/dev/gestion_agricole/`).
- Aucun déploiement réalisé.

---

# 10. RÉGRESSIONS ÉVENTUELLES

Aucune régression identifiée. Les modifications sont additives (nouveau champ,
nouvelle contrainte, mise à jour des vues). Les fonctionnalités existantes
ne sont pas modifiées.

---

# 11. LIMITES RESTANTES

- Les tests Odoo nécessitant une base de données ne sont pas exécutés.
- L'isolation de l'environnement de développement n'est pas démontrée.
- La migration du schéma (ajout du champ `state`) n'a pas été testée.
- Les traductions ne sont pas mises à jour (le champ utilise des labels
  français directement).

---

# 12. PROPOSITION D'UNE SEULE PETITE MISSION SUIVANTE

**Prompt 38** : Ajouter un champ `status` (statut) au modèle `gest_agri.farm`
(Exploitation agricole), avec les mêmes valeurs et la même logique, pour
cohérence avec le champ `state` ajouté aux parcelles.

---

*Rapport — Prompt N°37 — Module `gestion_agricole` — Odoo 20 Community.
Première évolution fonctionnelle. Modifications uniquement dans la copie de
travail. Production strictement en lecture seule.*
