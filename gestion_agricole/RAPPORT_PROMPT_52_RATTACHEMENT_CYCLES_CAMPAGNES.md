# Rapport — Prompt 52

## Rattachement des cycles de culture aux campagnes agricoles

**Module :** `gestion_agricole` — Odoo 20 Community
**Base de validation :** `odoo20`
**Date :** 11 novembre 2026
**Périmètre :** évolution ciblée des modèles `gest_agri.crop.cycle` et
`gest_agri.crop.campaign`, sans nouvel addon.

---

## 1. Résumé des réalisations

- Ajout d'une relation facultative `campaign_id` sur `gest_agri.crop.cycle`
  (Many2one vers `gest_agri.crop.campaign`, indexée, `ondelete="restrict"`,
  `check_company=True`).
- Ajout de la relation inverse `crop_cycle_ids` et du compteur
  `crop_cycle_count` sur `gest_agri.crop.campaign`.
- Contrôles serveur de cohérence : exploitation, société, période du cycle,
  état et archivage de la campagne.
- Contrôles serveur sur les modifications de campagne (exploitation, date de
  début, date de fin) lorsqu'elle porte des cycles.
- Conservation des relations et des cycles lors de l'archivage, de la clôture
  et de l'annulation.
- Mise à jour des vues cycle (liste, formulaire, recherche) et campagne
  (liste, onglet « Cycles de culture »).
- ACL inchangées, multi-société préservé, aucun nouveau groupe.
- 29 nouveaux tests automatisés exécutés avec succès ; aucune régression.
- Règles de chevauchement des cycles strictement inchangées.

---

## 2. Fichiers créés et modifiés

### Copie de développement `/tmp/opencode/dev/gestion_agricole/`

| Fichier | Nature |
|---|---|
| `models/production/crop_cycle.py` | modifié |
| `models/production/crop_campaign.py` | modifié |
| `views/production_views.xml` | modifié |
| `tests/__init__.py` | modifié |
| `tests/test_crop_cycle_campaign.py` | créé |
| `tests/test_crop_campaign.py` | modifié (assertion de non-régression Prompt 51) |

Aucune modification de `security/ir.access.csv`, `data/sequences.xml`, des
menus, de `__manifest__.py`, ni des règles de chevauchement.

### Module chargé `/mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/`

Les six fichiers ci-dessus ont été répliqués à l'identique (voir §13).

---

## 3. Relation `campaign_id` (cycle → campagne)

```python
campaign_id = fields.Many2one(
    "gest_agri.crop.campaign",
    string="Campagne agricole",
    index=True,
    ondelete="restrict",
    check_company=True,
    domain="[('farm_id', '=', farm_id), ('state', 'in', ('draft', 'active')), "
    "('active', '=', True)]",
)
```

- Relation **facultative** : les cycles existants restent valides et les
  cycles non rattachés continuent de fonctionner.
- Index SQL dédié et clé étrangère `ON DELETE RESTRICT` créés en base
  (vérifié : `gest_agri_crop_cycle_campaign_id_fkey`, `confdeltype = r`).
- Domaine dynamique limité à l'exploitation du cycle et aux campagnes
  `draft`/`active` non archivées. Ce domaine est une aide à la saisie ; le
  contrôle serveur reste obligatoire et effectif.

## 4. Relation inverse `crop_cycle_ids` (campagne → cycles)

```python
crop_cycle_ids = fields.One2many(
    "gest_agri.crop.cycle", "campaign_id", string="Cycles de culture"
)
crop_cycle_count = fields.Integer(
    string="Nombre de cycles", compute="_compute_crop_cycle_count"
)
```

Le compteur inclut les cycles archivés (`active_test=False`) afin de refléter
fidèlement l'historique de la campagne.

---

## 5. Contrôles d'exploitation et de société

Contrôle `_check_campaign_compatibility` (contrainte `@api.constrains`) :

- `cycle.farm_id == campaign.farm_id`, sinon `ValidationError` explicite ;
- `cycle.company_id == campaign.company_id`, sinon `ValidationError` ;
- `check_company=True` sur `campaign_id` assure également la cohérence de
  société au niveau ORM (Odoo lève alors un `UserError` de cohérence société,
  ce que les tests acceptent pour le cas « autre société »).

Le contrôle est déclenché à la création et lors de la modification de
`campaign_id`, `plot_id`, `date_start`, `date_end_planned` ou
`date_end_actual`.

---

## 6. Contrôles des périodes

Règle de fin effective conservée : `date_end_actual or date_end_planned`.

- `cycle.date_start >= campaign.date_start` ;
- si `campaign.date_end` existe :
  - un cycle à fin ouverte (aucune fin effective) est refusé ;
  - la fin effective du cycle doit être `<= campaign.date_end` ;
- si la campagne n'a pas de `date_end`, aucune limite supérieure n'est
  imposée.

Toutes les incohérences de période lèvent une `ValidationError` explicite.

---

## 7. États de campagne et cycle

- Rattachement autorisé uniquement aux campagnes `draft` et `active`.
- Nouveau rattachement ou transfert vers `closed` / `cancelled` refusé
  (`UserError`).
- Campagne archivée (`active = False`) refusée pour tout nouveau rattachement
  (`UserError`).
- Les relations existantes vers une campagne archivée, clôturée ou annulée
  sont **conservées**.
- Détachement (`campaign_id = False`) autorisé sauf si la campagne courante
  est `closed` ou `cancelled` (`UserError`).
- Aucune transition d'état de cycle ni de campagne modifiée ; l'archivage, la
  clôture et l'annulation ne modifient pas l'état des cycles.

---

## 8. Vues et menus

### Cycle de culture

- **Formulaire** : champ « Campagne agricole » ajouté dans le groupe
  « Parcelle et exploitation », avec domaine dynamique et
  `no_create`.
- **Liste** : colonne « Campagne agricole ».
- **Recherche** : champ de recherche « Campagne agricole » et filtre de
  regroupement `group_campaign`.

### Campagne agricole

- **Formulaire** : nouvel onglet « Cycles de culture » listant référence,
  parcelle, type de culture, date de début, fin prévue, état et surface
  cultivée. La liste intégrée est en lecture seule (`create="false"
  edit="false"`) : toute création/modification passe par le formulaire du
  cycle et donc par ses ACL et ses règles métier.
- **Liste** : colonne « Cycles » alimentée par `crop_cycle_count`.
- Aucun menu créé ni modifié.

---

## 9. ACL et règles multi-société

- `security/ir.access.csv` inchangé : 6 règles existantes (3 par modèle).
- Aucun nouveau groupe, aucun élargissement de droits.
- Les règles d'enregistrement existantes restent seules applicables :
  - utilisateur : lecture limitée aux exploitations accessibles ;
  - responsable : création/modification limitées aux exploitations gérées ;
  - administrateur : CRUD limité à ses sociétés.
- Les accès via les relations Many2one/One2many respectent ces règles.
- Vérifié en base : les 6 ACL et leurs domaines sont identiques à ceux des
  Prompts 50 et 51.

---

## 10. Tests ajoutés et résultats individuels

Fichier : `tests/test_crop_cycle_campaign.py` — **29 tests**, tous réussis.

| # | Test | Résultat |
|---|---|---|
| 1 | `test_cycle_without_campaign` | OK |
| 2 | `test_cycle_with_campaign` | OK |
| 3 | `test_inverse_relation_and_count` | OK |
| 4 | `test_other_farm_campaign_rejected` | OK |
| 5 | `test_other_company_campaign_rejected` | OK |
| 6 | `test_cycle_start_before_campaign_rejected` | OK |
| 7 | `test_cycle_end_after_campaign_rejected` | OK |
| 8 | `test_open_end_in_campaign_with_end_rejected` | OK |
| 9 | `test_open_end_in_campaign_without_end_accepted` | OK |
| 10 | `test_effective_end_uses_actual_date` | OK |
| 11 | `test_closed_campaign_rejected` | OK |
| 12 | `test_cancelled_campaign_rejected` | OK |
| 13 | `test_archived_campaign_rejected` | OK |
| 14 | `test_draft_campaign_accepted` | OK |
| 15 | `test_active_campaign_accepted` | OK |
| 16 | `test_detach_allowed` (+ `test_detach_from_closed_campaign_rejected`) | OK |
| 17 | `test_campaign_start_change_incompatible` / `test_campaign_end_change_incompatible` | OK |
| 18 | `test_campaign_farm_change_incompatible` | OK |
| 19 | `test_archive_preserves_relations` | OK |
| 20 | `test_close_preserves_cycles` | OK |
| 21 | `test_cancel_preserves_cycles` | OK |
| 22 | `test_user_can_read_but_not_attach` / `test_manager_can_attach` | OK |
| 23 | `test_multi_company_isolation` | OK |
| 24 | `test_cycle_transitions_unchanged` | OK |
| 25 | `test_overlap_rules_unchanged` | OK |

Test complémentaire : `test_campaign_compatible_change_allowed` — OK.

### Résultat de la suite ciblée

```
gestion_agricole: 58 tests 4.80s 3448 queries
0 failed, 0 error(s) of 54 tests when loading database 'odoo20'
```

(58 exécutions incluant les tests de `TestCropCampaign` ; 54 cas chargés.)

### Résultat de la suite complète du module

```
gestion_agricole: 230 tests 16.89s 12215 queries
0 failed, 27 error(s) of 214 tests when loading database 'odoo20'
```

- **187 tests réussis**
- **0 test échoué**
- **27 erreurs**, strictement les mêmes que lors du Prompt 51 :
  - `TestReservationUnicity` : 26 erreurs (table
    `gest_agri_reference_reservation` absente, module de réservation non
    installé) ;
  - `TestAuditPrompt11.test_c2_unique_index_message_is_user_friendly` : 1
    erreur (absence de `btree_gist`).
- Aucune de ces erreurs n'est liée au Prompt 52.

---

## 11. Commandes exécutées

Mise à jour et tests complets :

```bash
cd /mnt/srv/share/odoo20/odoo && \
/etc/odoo20-venv/bin/python odoo-bin -c /etc/odoo20.conf -d odoo20 \
  --no-http --max-cron-threads=0 --stop-after-init \
  -u gestion_agricole --test-enable --test-tags /gestion_agricole
```

Tests ciblés :

```bash
cd /mnt/srv/share/odoo20/odoo && \
/etc/odoo20-venv/bin/python odoo-bin -c /etc/odoo20.conf -d odoo20 \
  --no-http --max-cron-threads=0 --stop-after-init \
  --test-enable --test-tags /gestion_agricole:TestCropCycleCampaign
```

```bash
cd /mnt/srv/share/odoo20/odoo && \
/etc/odoo20-venv/bin/python odoo-bin -c /etc/odoo20.conf -d odoo20 \
  --no-http --max-cron-threads=0 --stop-after-init \
  --test-enable --test-tags /gestion_agricole:TestCropCycleCampaign,/gestion_agricole:TestCropCampaign
```

Vérifications SQL :

```bash
PGPASSWORD=odoo20 psql -U odoo20 -h 127.0.0.1 -p 5433 -d odoo20 \
  -c "\d gest_agri_crop_cycle"
PGPASSWORD=odoo20 psql -U odoo20 -h 127.0.0.1 -p 5433 -d odoo20 \
  -c "SELECT conname, confdeltype FROM pg_constraint
      WHERE conrelid='gest_agri_crop_cycle'::regclass AND contype='f';"
```

Compilation syntaxique et XML :

```bash
python3 -m py_compile models/production/crop_cycle.py \
  models/production/crop_campaign.py \
  tests/test_crop_cycle_campaign.py tests/test_crop_campaign.py
python3 -c "import xml.etree.ElementTree as E; E.parse('views/production_views.xml')"
```

---

## 12. Résultat de la mise à jour sur `odoo20`

- Mise à jour du module `gestion_agricole` terminée sans erreur.
- Colonne `campaign_id` créée sur `gest_agri_crop_cycle`, index
  `gest_agri_crop_cycle__campaign_id_index` présent.
- Contrainte étrangère `gest_agri_crop_cycle_campaign_id_fkey` avec
  `ON DELETE RESTRICT` confirmée.
- Vues chargées en base :
  - `gest_agri.crop.cycle.form`, `.list`, `.search` contiennent
    `campaign_id` ;
  - `gest_agri.crop.campaign.form` contient l'onglet `crop_cycle_ids`
    (liste en lecture seule) ;
  - la liste des campagnes affiche `crop_cycle_count`.
- ACL : 6 règles inchangées, domaines identiques.
- Aucune extension PostgreSQL installée, aucun service redémarré, aucune
  autre base ni configuration modifiée.

---

## 13. Synchronisation des deux répertoires

Comparaison octet par octet des six fichiers modifiés :

```
diff -q /tmp/opencode/dev/gestion_agricole/<fichier> \
        /mnt/srv/share/odoo20/addons/kantmoh/gestion_agricole/<fichier>
```

Résultat : **aucune différence** (`SYNC_IDENTIQUE_OK`).

---

## 14. Règles de chevauchement des cycles

- La contrainte `_check_overlap` n'a pas été modifiée.
- L'index unique partiel `(plot_id, date_start) WHERE state <> 'cancelled'`
  n'a pas été modifié.
- Les intervalles restent inclusifs, les cycles annulés exclus du contrôle et
  les cycles archivés participants.
- Le test `test_overlap_rules_unchanged` confirme le comportement.
- La limite de concurrence déjà documentée (absence de `btree_gist`,
  INF-10/D1) reste inchangée et hors périmètre du Prompt 52.

---

## 15. Anomalies et réserves

1. **Erreurs historiques (27)** : réservation (26) et `btree_gist` (1),
   identiques au Prompt 51, non imputables au Prompt 52.
2. **Ordre des contrôles société** : en cas de campagne d'une autre société,
   `check_company` peut lever un `UserError` avant la `ValidationError` métier.
   Le refus est effectif dans les deux cas ; le test accepte explicitement les
   deux types.
3. **Concurrence des chevauchements de cycles** : garantie purement
   applicative, limite déjà connue et non modifiée.
4. **Affichage de la campagne** : le champ Many2one affiche le nom de la
   campagne ; l'exploitation est déjà affichée sur le cycle et le code est
   consultable dans le formulaire de la campagne. Aucun champ
   d'affichage supplémentaire n'a été introduit pour ne pas modifier les
   autres champs du cycle.
5. Les erreurs SQL volontairement provoquées par les tests existants
   (doublons, NOT NULL) apparaissent dans les journaux mais sont attendues et
   comptabilisées comme tests réussis.

---

## Conclusion

Le rattachement des cycles de culture aux campagnes agricoles est
opérationnel, contrôlé côté serveur, navigable dans les deux sens et couvert
par 29 tests réels réussis. Les acquis des Prompts 50 et 51 sont préservés :
aucune régression fonctionnelle, ACL inchangées, règles de chevauchement
intactes.
