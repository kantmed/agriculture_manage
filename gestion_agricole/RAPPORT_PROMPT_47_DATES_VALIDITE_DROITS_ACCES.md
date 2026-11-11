# RAPPORT PROMPT N°47 — DATES DE VALIDITÉ DES DROITS D'ACCÈS AUX EXPLOITATIONS

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. ANALYSE PRÉALABLE

Modèle examiné : `gest_agri.farm.access`.

- Aucun champ `date_start` n'existait.
- Aucun champ `date_end` n'existait.
- Aucun champ équivalent (date de début/fin, période, échéance) n'était présent.
- Contraintes existantes : unicité active `(farm_id, user_id) WHERE active IS TRUE`, contrôle de société, auto-gestion.
- Tests existants : `test_security.py` (isolation, rôles, auto-gestion, unicité) et `test_patrimony.py`.

Conclusion : création des deux champs, sans doublon.

---

# 2. CHAMPS CRÉÉS

| Attribut | `date_start` | `date_end` |
|---|---|---|
| Type | `fields.Date` | `fields.Date` |
| Libellé | Date de début | Date de fin |
| Obligatoire | Non | Non |
| Valeur par défaut | Vide | Vide |
| Aide | Début prévu de validité de l'habilitation. | Fin prévue de validité de l'habilitation. |

Aucune date automatique, aucune valeur calculée.

---

# 3. CONTRAINTE DE COHÉRENCE

```python
@api.constrains("date_start", "date_end")
def _check_date_period(self):
    for access in self:
        if (
            access.date_start
            and access.date_end
            and access.date_end < access.date_start
        ):
            raise ValidationError(
                self.env._(
                    "La date de fin de validité ne peut pas être antérieure "
                    "à la date de début."
                )
            )
```

Comportements garantis :

| `date_start` | `date_end` | Résultat |
|---|---|---|
| Vide | Vide | Accepté |
| Renseignée | Vide | Accepté |
| Vide | Renseignée | Accepté |
| 01/01/2026 | 31/12/2026 | Accepté |
| 01/01/2026 | 01/01/2026 | Accepté |
| 31/12/2026 | 01/01/2026 | Refusé (`ValidationError`) |

La contrainte s'applique à la création **et** à la modification (décorateur `@api.constrains`).

---

# 4. FICHIERS MODIFIÉS

| Fichier | Modification |
|---|---|
| `models/patrimony/farm_access.py` | Import `ValidationError` ; champs `date_start`/`date_end` ; contrainte `_check_date_period` |
| `views/farm_views.xml` | Section « Période de validité » dans la vue formulaire |
| `tests/test_security.py` | 2 tests ajoutés |

Fichiers répliqués à l'identique dans
`/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/` (vérifiés par `diff -q`).

---

# 5. MODIFICATION DE LA VUE

Dans `gest_agri.farm.access.form`, ajout d'un groupe clairement identifié
« Période de validité » contenant `date_start` et `date_end`, placé entre les
groupes principaux et le champ `description`.

L'onglet « Notes internes » du Prompt 46 est conservé. Les vues liste et
recherche n'ont pas été modifiées. La liste embarquée `access_ids` du formulaire
d'exploitation est inchangée.

---

# 6. TESTS AJOUTÉS

| Test | Couverture |
|---|---|
| `test_farm_access_dates_optional_and_coherent` | Sans dates ; uniquement `date_start` ; uniquement `date_end` ; deux dates cohérentes ; deux dates identiques |
| `test_farm_access_dates_incoherent_rejected_and_correction` | Refus à la création ; refus à la modification ; correction cohérente acceptée après erreur |

Les 8 points demandés sont couverts. Les deux tests ont démarré et n'apparaissent
dans aucune erreur → **réussis**.

---

# 7. CONTRÔLES STATIQUES

| Contrôle | Résultat |
|---|---|
| Compilation Python (`compileall`) | ✅ 0 erreur |
| Validation XML (7 fichiers) | ✅ bien formés |
| Analyse AST des fichiers modifiés | ✅ OK |
| Manifeste | ✅ inchangé |

---

# 8. MISE À JOUR ODOO

Vérifications : base `odoo20` / utilisateur `odoo20` / port 5433, module `installed`,
exécution autonome `--no-http --max-cron-threads=0 --stop-after-init`, `-d odoo20`
uniquement, service partagé non redémarré.

Commande exécutée :
```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init -u gestion_agricole
```

Résultat : **EXIT=0**.

Vérifications en base :

| Contrôle | Résultat |
|---|---|
| Colonne `gest_agri_farm_access.date_start` | ✅ présente, type `date` |
| Colonne `gest_agri_farm_access.date_end` | ✅ présente, type `date` |
| Module | `installed`, version `20.0.1.0.0`, `write_date` `2026-11-11 07:47:52` |
| ACL du modèle | ✅ 4 règles inchangées |

---

# 9. TESTS ODOO

Commande exécutée :
```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
```

Résultat global :
```
0 failed, 27 error(s) of 121 tests when loading database 'odoo20'
```

| Catégorie | Nombre |
|---|---|
| Tests exécutés | 121 |
| Réussis | 94 |
| Échoués (`failed`) | 0 |
| En erreur (`errors`) | 27 |
| Non exécutés | 0 |

Les 27 erreurs sont **exclusivement** les tests de réservation
(`test_reservation_unicity` : 26, `test_audit_prompt11` : 1), dues à l'absence
de `gest_agri_reference_reservation` (`btree_gist` non installé). Aucune erreur
hors réservation.

---

# 10. SÉCURITÉ INCHANGÉE

- Aucune modification de `security/ir.access.csv` ni des domaines d'accès.
- Aucune modification des groupes `user`, `manager`, `admin`.
- Aucune modification de `_check_self_management`, `_invalidate_farm_access_cache`,
  des méthodes `create`/`write`/`unlink` ni des champs calculés de `res.users`.
- Les 4 règles ACL du modèle restent identiques (vérifié en base).
- Les tests de sécurité existants continuent de passer.

---

# 11. ABSENCE D'ACTIVATION / EXPIRATION AUTOMATIQUE

- Aucun cron ajouté.
- Aucune modification de `active`.
- Aucune vérification de date dans les domaines d'accès ou les méthodes d'accès.
- Les dates sont **purement prévisionnelles** : une habilitation expirée reste
  active et continue de donner accès jusqu'à une évolution fonctionnelle dédiée.

---

# 12. DIFFICULTÉS RENCONTRÉES

Aucune. La contrainte et les tests fonctionnent dès la première exécution.

---

# 13. PROPOSITION POUR LE PROMPT 48

**Prompt 48** : Mettre en place l'**expiration automatique** des habilitations
`gest_agri.farm.access` à partir de `date_end` (champ calculé `is_expired` +
filtre de recherche), **sans encore** retirer les droits d'accès effectifs —
la désactivation effective fera l'objet d'un prompt distinct avec validation
métier explicite.

---

*Rapport — Prompt N°47 — Module `gestion_agricole` — Odoo 20 Community.
Onzième évolution fonctionnelle. Développement dans la copie de travail,
mise à jour et tests réels sur `odoo20`.*
