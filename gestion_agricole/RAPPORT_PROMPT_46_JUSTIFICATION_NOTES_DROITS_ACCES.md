# RAPPORT PROMPT N°46 — JUSTIFICATION ET NOTES DES DROITS D'ACCÈS AUX EXPLOITATIONS

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. ANALYSE PRÉALABLE DU MODÈLE

Modèle : `gest_agri.farm.access` — « Droit d'accès à une exploitation ».

Champs présents avant modification :

| Champ | Type | Rôle |
|---|---|---|
| `farm_id` | Many2one `gest_agri.farm` | Exploitation concernée (obligatoire) |
| `user_id` | Many2one `res.users` | Bénéficiaire (obligatoire) |
| `role` | Selection (`user`, `manager`, `admin`) | Rôle accordé |
| `company_id` | Many2one `res.company` (related, stored) | Société dérivée de l'exploitation |
| `description` | Text | Description libre |
| `active` | Boolean | Archivage |

Aucun champ de **justification** ni de **notes** n'existait. La contrainte
d'unicité `(farm_id, user_id) WHERE active IS TRUE` et les règles de sécurité
n'ont pas été touchées.

**Dates de validité : aucun champ de date de début ou de fin n'existe.**
Cette lacune est signalée (voir §8) ; elle n'a pas été comblée dans ce prompt,
conformément à la consigne.

---

# 2. CHAMP `notes` AJOUTÉ

| Attribut | Valeur |
|---|---|
| Nom technique | `notes` |
| Type | `fields.Text` |
| Libellé | `Notes internes` |
| Obligatoire | Non |
| Valeur par défaut | Vide |
| Aide | « Motif, observations et précisions complémentaires concernant cette habilitation. » |
| Contrainte / tracking | Aucun |

Le champ `description` existant est conservé tel quel ; `notes` le complète sans
le remplacer.

---

# 3. MODIFICATION DES VUES

Vue formulaire `gest_agri.farm.access.form` : ajout d'un onglet dédié
« Notes internes » après le champ `description`, au moyen d'un notebook minimal.
La structure existante (titre, groupes, ribbon) est inchangée.

Aucun ajout dans la liste, la recherche, ni dans la liste embarquée
`access_ids` du formulaire d'exploitation : un texte libre n'y est pas pertinent.

Aucune règle de sécurité ni domaine d'accès modifié : le champ est visible et
modifiable dans les mêmes conditions que l'habilitation elle-même.

---

# 4. FICHIERS MODIFIÉS

| Fichier | Modification |
|---|---|
| `models/patrimony/farm_access.py` | Ajout du champ `notes` |
| `views/farm_views.xml` | Onglet « Notes internes » dans la vue formulaire |
| `tests/test_security.py` | 2 tests ajoutés |

Fichiers répliqués à l'identique dans
`/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/` (vérifiés par `diff -q`).

---

# 5. TESTS AJOUTÉS

| Test | Vérifications |
|---|---|
| `test_farm_access_notes_default_and_modification` | Valeur vide par défaut, modification, conservation après `browse`, remise à vide |
| `test_farm_access_notes_creation_and_security_preserved` | Création avec notes ; lecture de ses propres notes par l'utilisateur concerné ; refus de lecture par un autre utilisateur (`AccessError`) |

Résultats : les deux tests ont démarré et n'apparaissent dans aucune erreur →
**réussis**.

---

# 6. CONTRÔLES STATIQUES

| Contrôle | Résultat |
|---|---|
| Compilation Python (`compileall`) | ✅ 0 erreur |
| Validation XML (7 fichiers) | ✅ bien formés |
| Analyse AST du fichier de tests | ✅ OK |
| Manifeste | ✅ inchangé |

---

# 7. MISE À JOUR ODOO

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
| Colonne `gest_agri_farm_access.notes` | ✅ présente, type `text` |
| Vue formulaire | ✅ contient « Notes internes » |
| Module | `installed`, version `20.0.1.0.0`, `write_date` `2026-11-11 07:41:30` |
| Règles ACL du modèle | ✅ 4 règles inchangées (administration `crud`, gestion responsable `cud`, lecture responsable `r`, lecture utilisateur `r`) |

---

# 8. TESTS ODOO

Commande exécutée :
```
odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
```

Résultat global :
```
0 failed, 27 error(s) of 119 tests when loading database 'odoo20'
```

| Catégorie | Nombre |
|---|---|
| Tests exécutés | 119 |
| Réussis | 92 |
| Échoués (`failed`) | 0 |
| En erreur (`errors`) | 27 |
| Non exécutés | 0 |

Les 27 erreurs sont **exclusivement** les tests de réservation
(`test_reservation_unicity` : 26, `test_audit_prompt11` : 1), dues à l'absence
de `gest_agri_reference_reservation` (`btree_gist` non installé). Aucune erreur
hors réservation.

---

# 9. SITUATION DES DATES DE VALIDITÉ

Le modèle ne comporte **ni date de début ni date de fin de validité**, ni de
logique d'expiration automatique. Ce point est signalé comme lacune
fonctionnelle. Il n'a pas été traité ici : une évolution distincte devra définir
les champs (`date_start`, `date_end`), les règles d'activation/expiration et
leur impact sur `gest_agri_farm_ids` / `gest_agri_managed_farm_ids`.

---

# 10. CONSERVATION DES RÈGLES DE SÉCURITÉ

- Aucune modification de `security/ir.access.csv`.
- Aucune modification des domaines d'accès existants.
- Aucune modification des méthodes `_check_self_management`, `create`, `write`, `unlink`.
- Les 4 règles ACL du modèle sont inchangées (vérifié en base).
- Le test `test_farm_access_notes_creation_and_security_preserved` confirme que
  l'isolation entre utilisateurs reste effective.

---

# 11. AMÉLIORATIONS À PRÉVOIR ULTÉRIEUREMENT

1. Ajouter `date_start` / `date_end` et une logique d'expiration des habilitations.
2. Prévoir un historique des modifications d'habilitation (traçabilité des
   changements de rôle et de périmètre).
3. Éventuellement, un motif structuré (Selection) en complément des notes libres.

---

# 12. CONFIRMATION DE NON-INTERVENTION

- Seule la base `odoo20` mise à jour ; aucune autre base touchée.
- `/etc/odoo20.conf` non modifié ; rôles et permissions PostgreSQL inchangés.
- Aucune permission système modifiée.
- Aucun service Odoo partagé redémarré ; Odoo 16 non touché.
- `btree_gist` non installé ; les 27 erreurs historiques restent isolées.

---

# 13. PROPOSITION POUR LE PROMPT 47

**Prompt 47** : Ajouter les dates de validité (`date_start`, `date_end`) au modèle
`gest_agri.farm.access`, avec contrainte de cohérence (`date_end >= date_start`)
et affichage dans la vue formulaire — **sans** modifier encore la logique
d'activation/expiration des droits, qui fera l'objet d'un prompt ultérieur.

---

*Rapport — Prompt N°46 — Module `gestion_agricole` — Odoo 20 Community.
Dixième évolution fonctionnelle. Développement dans la copie de travail,
mise à jour et tests réels sur `odoo20`.*
