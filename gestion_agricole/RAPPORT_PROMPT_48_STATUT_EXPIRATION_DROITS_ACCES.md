# RAPPORT PROMPT N°48 — STATUT D'EXPIRATION DES DROITS D'ACCÈS AUX EXPLOITATIONS

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. ANALYSE DE L'EXISTANT

Modèle `gest_agri.farm.access` :

- `date_start` et `date_end` (`fields.Date`, facultatifs) présents depuis le Prompt 47 et fonctionnels.
- Contrainte `_check_date_period` active (`date_end >= date_start`).
- Vues formulaire, liste et recherche existantes.
- Aucun champ `is_expired` ni équivalent n'existait.
- Tests existants : `test_security.py` (isolation, rôles, auto-gestion, unicité, notes, dates) et `test_patrimony.py`.

Aucun doublon créé, aucun champ existant modifié.

---

# 2. CHAMP `is_expired`

| Propriété | Valeur |
|---|---|
| Nom technique | `is_expired` |
| Type | `fields.Boolean` |
| Libellé | Habilitation expirée |
| Calcul | `_compute_is_expired` |
| Stocké | **Non** (`store=False` par défaut) |
| Lecture seule | Oui (champ calculé sans inverse) |
| Recherche | Oui, via `_search_is_expired` |
| Aide | Indique si la date de fin est dépassée ; information purement indicative |

---

# 3. CALCUL ET RECHERCHE

## 3.1 Calcul

```python
@api.depends("date_end")
def _compute_is_expired(self):
    today = fields.Date.context_today(self)
    for access in self:
        access.is_expired = bool(access.date_end and access.date_end < today)
```

- `date_end` vide → `False`.
- `date_end` < aujourd'hui → `True`.
- `date_end` = aujourd'hui → `False`.
- `date_end` > aujourd'hui → `False`.
- `date_start` n'intervient pas.

Le champ n'étant pas stocké, la valeur suit automatiquement le changement de
date, sans cron ni recalcul.

## 3.2 Recherche

```python
def _search_is_expired(self, operator, value):
    today = fields.Date.context_today(self)
    expired_domain = [("date_end", "<", today)]
    not_expired_domain = ["|", ("date_end", "=", False), ("date_end", ">=", today)]
    ...
```

Traductions :

| Recherche | Domaine appliqué |
|---|---|
| `is_expired = True` | `date_end < aujourd'hui` |
| `is_expired = False` | `date_end` vide OU `date_end >= aujourd'hui` |
| `is_expired != True` | non expirée |
| `is_expired != False` | expirée |
| `is_expired in [True]` / `not in` | prise en charge (optimiseur Odoo 20) |

Les opérateurs `in` / `not in` ont été ajoutés après un premier échec réel :
l'optimiseur de domaines d'Odoo 20 convertit certains tests booléens en `in`
avant d'appeler la méthode de recherche (voir §9).

---

# 4. MODIFICATIONS DES VUES

## 4.1 Formulaire `gest_agri.farm.access.form`

Dans le groupe « Période de validité », après `date_end` :

```xml
<field name="is_expired" readonly="1"/>
```

L'onglet « Notes internes » et tous les champs précédents sont conservés.

## 4.2 Recherche `gest_agri.farm.access.search`

Deux filtres ajoutés, sans modifier les filtres existants :

```xml
<filter name="expired" string="Habilitations expirées" domain="[('is_expired', '=', True)]"/>
<filter name="not_expired" string="Habilitations non expirées" domain="[('is_expired', '=', False)]"/>
```

Ils sont distincts des filtres `active` / `inactive`.

---

# 5. TESTS AJOUTÉS

| Test | Couverture |
|---|---|
| `test_farm_access_is_expired_compute_and_update` | Sans date de fin ; date passée ; date du jour ; date future ; modification de `date_end` (passé → aujourd'hui → vide) avec recalcul immédiat |
| `test_farm_access_is_expired_search` | Recherches `= True`, `= False`, `!= True`, `!= False` ; présence des dates vides parmi les non expirées |
| `test_expired_access_keeps_effective_rights` | Une habilitation expirée reste `active` et continue de donner accès à l'exploitation |

Dates calculées relativement à `fields.Date.context_today` (jamais de dates fixes).

Résultats : les trois tests ont démarré et n'apparaissent dans aucune erreur →
**réussis**.

---

# 6. FICHIERS MODIFIÉS ET RÉPLICATION

| Fichier | Modification |
|---|---|
| `models/patrimony/farm_access.py` | Champ `is_expired`, `_compute_is_expired`, `_search_is_expired` |
| `views/farm_views.xml` | Champ en formulaire + 2 filtres de recherche |
| `tests/test_security.py` | Imports `timedelta` / `fields` + 3 tests |

Réplication vérifiée dans `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/`
par `diff -q` : fichiers identiques.

---

# 7. MISE À JOUR ODOO

Vérifications préalables : base `odoo20`, utilisateur PostgreSQL `odoo20`, port 5433,
module `gestion_agricole` `installed`, exécution autonome sans HTTP ni cron,
`-d odoo20` uniquement, service partagé non redémarré.

Commande :
```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init -u gestion_agricole
```

Résultat : **EXIT=0**.

Vérifications en base :

| Contrôle | Résultat |
|---|---|
| Vue formulaire contient `is_expired` | ✅ |
| Vue recherche contient les filtres d'expiration | ✅ |
| Module | `installed`, version `20.0.1.0.0`, `write_date` `2026-11-11 11:22:24` |
| ACL du modèle | ✅ 4 règles inchangées |
| `security/ir.access.csv` | ✅ identique |

`is_expired` n'étant pas stocké, aucune colonne n'est créée dans
`gest_agri_farm_access` : c'est le comportement attendu.

---

# 8. RÉSULTATS COMPLETS DES TESTS

Commande :
```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
```

Résultat global :
```
0 failed, 27 error(s) of 124 tests when loading database 'odoo20'
```

| Catégorie | Nombre |
|---|---|
| Tests exécutés | 124 |
| Réussis | 97 |
| Échoués (`failed`) | 0 |
| En erreur (`errors`) | 27 |
| Non exécutés | 0 |

Les 27 erreurs sont **strictement** les tests de réservation
(`TestReservationUnicity` : 26, `TestAuditPrompt11` : 1), dues à l'absence de
`btree_gist`. Aucune erreur hors réservation. Aucune erreur liée à `is_expired`.

---

# 9. ERREUR RENCONTRÉE ET CORRECTION

Premier passage des tests : 28 erreurs, dont
`TestSecurity.test_farm_access_is_expired_search`.

Cause : l'optimiseur de domaines d'Odoo 20 appelle `_search_is_expired` avec
l'opérateur `in` (et non seulement `=`/`!=`), ce qui déclenchait le `ValueError`
de garde.

Correction : prise en charge explicite de `in` / `not in` dans
`_search_is_expired`, avec complément correct des états booléens. Après
correction : retour à 27 erreurs (uniquement réservation), test réussi.

---

# 10. DROITS EFFECTIFS ET ACL INCHANGÉS

- `active` non modifié : une habilitation expirée reste active.
- `_check_self_management`, `_invalidate_farm_access_cache`, `create`, `write`,
  `unlink` non modifiés.
- Champs calculés `res.users` (`gest_agri_farm_ids`, `gest_agri_managed_farm_ids`)
  non modifiés.
- ACL, règles d'enregistrement et domaines d'accès inchangés (4 règles identiques).
- Le test `test_expired_access_keeps_effective_rights` prouve qu'une habilitation
  expirée continue d'accorder les mêmes droits.

---

# 11. ABSENCE DE CRON ET DE DÉSACTIVATION AUTOMATIQUE

- Aucun `ir.cron` ajouté.
- Aucune tâche planifiée.
- Aucune désactivation automatique de `active`.
- Aucun traitement automatique des habilitations.
- `is_expired` est purement informatif et calculé à la lecture.

---

# 12. PROPOSITION POUR LE PROMPT 49

**Prompt 49** : Ajouter un indicateur calculé `is_active_period` (ou équivalent)
sur `gest_agri.farm.access` pour distinguer une habilitation « à venir », « en
cours » et « expirée », avec affichage et filtre — toujours sans modifier les
droits effectifs.

---

*Rapport — Prompt N°48 — Module `gestion_agricole` — Odoo 20 Community.
Douzième évolution fonctionnelle. Développement dans la copie de travail,
mise à jour et tests réels sur `odoo20`.*
