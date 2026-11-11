# RAPPORT PROMPT N°18 — FINALISATION DE L'AUDIT, TRAÇABILITÉ PRODUCTION ET VALIDATION DES RISQUES RÉSIDUELS

## Module `gestion_agricole` — Odoo 20 Community

> Rapport final consolidé. Phases A à I exécutées. Aucune activation en
> production. Aucune modification de la base `odoo20`.

---

# 1. ENVIRONNEMENT EXACT

| Élément | Valeur |
|---|---|
| Odoo | 20.0, `/mnt/srv/share/odoo20/odoo` |
| Python | 3.12.0, `/etc/odoo20-venv/bin/python` |
| PostgreSQL | 18.6 (cluster `18/main`), port 5433 |
| Niveau d'isolation | `REPEATABLE READ` |
| Base de production | `odoo20` — **lecture seule stricte** |
| Base de diagnostic (module) | `gest_agri_audit_test` — écritures autorisées |
| Base de diagnostic (concurrence) | `gest_agri_concurrency_test` — non utilisée dans ce prompt |
| Serveur Odoo | non redémarré, non modifié, non arrêté |
| Configuration | `/etc/odoo20.conf` **non modifiée** |
| Logs Odoo | aucune destination fichier (stdout du processus) |
| Logs PostgreSQL | `logging_collector = off`, `log_statement = none` |

---

# 2. BASES UTILISÉES

| Base | Nature | Opérations |
|---|---|---|
| `odoo20` | production | `SELECT` uniquement |
| `gest_agri_audit_test` | diagnostic | `-u gestion_agricole` (1 exécution), suite de tests (4 exécutions), purge des réservations, vérification de normalisation |
| `gest_agri_concurrency_test` | diagnostic | non utilisée dans ce prompt |

---

# 3. FICHIERS EXAMINÉS

## 3.1 Code source Odoo 20
- `odoo/addons/base/models/ir_module.py` — `update_list`, `_update_from_terp`, `_state_update`
- `odoo/modules/loading.py` — `load_modules`, `load_module_graph`, `update_list` (appelé)
- `odoo/modules/db.py` — `list_dbs`, `exp_db_list`, `db_filter`
- `odoo/orm/registry.py` — `post_init`, `init_models`, `_auto_init`, `init`
- `odoo/service/server.py` — `FSWatcher`, `restart()`, `reload()`

## 3.2 Code source du module
- `models/configuration/reservation.py` (443 lignes)
- `models/configuration/_common.py` (130 lignes)
- `tests/test_reservation_unicity.py` (430 lignes, 26 méthodes)
- `models/configuration/*.py` (13 modèles)

## 3.3 Propositions
- `/tmp/opencode/preparation/PHASE_B_ISOLATION_PROPOSITION.md`
- `/tmp/opencode/preparation/PHASE_C_JOURNALISATION_PROPOSITION.md`
- `/tmp/opencode/preparation/odoo20-test.conf.proposition`

---

# 4. PHASE A — ENQUÊTE SUR LE CHANGEMENT DE `write_date` EN PRODUCTION

## 4.1 Constat

| Rapport | `write_date` annoncée |
|---|---|
| Prompt 16 | `2026-11-10 21:40:00.677710` |
| Prompt 17 | `2026-11-11 03:08:36.034021` |

La valeur a bien changé entre les deux rapports.

## 4.2 Vérifications effectuées

1. **Code Odoo 20 concerné** : `ir_module_module.write` est invoqué par :
   - `update_list()` (ligne 807 de `ir_module.py`) : écrit `updated_values` si un champ
     du manifeste diffère de la valeur en base. Les champs comparés sont ceux de
     `get_values_from_terp()` (version, description, auteur, catégorie, etc.).
   - `_state_update()` (ligne 426) : change l'état lors d'une installation/mise à jour.
   - Les opérations d'installation/mise à jour (`button_immediate_install`, etc.).

2. **Aucune commande `-u`/`-i` n'a été lancée sur `odoo20`** dans le cadre de ce
   travail (interdit explicite, respecté). Les seules commandes `odoo-bin` lancées
   portaient sur `gest_agri_audit_test` (`-d gest_agri_audit_test`).

3. **Logs** : aucune destination fichier configurée (`logfile` absent de
   `/etc/odoo20.conf`). PostgreSQL a `logging_collector = off` et
   `log_statement = none`. **Aucun journal exploitable n'existe** pour identifier
   l'opération exacte.

4. **Processus** : le processus de production (PID 314241 mentionné dans les
   rapports précédents) n'est plus actif. Le processus courant (328398) est une
   session interactive de test.

## 4.3 Ce qui est démontré

| Point | Statut | Preuve |
|---|---|---|
| Absence de modification des données métier | ✅ démontré | 1 ferme + 1 site intacts, 0 parcelle ; aucune écriture `INSERT/UPDATE/DELETE` sur les tables métier |
| Absence de modification du schéma | ✅ démontré | 49 index uniques (39 + 10) inchangés ; table de réservation absente ; `btree_gist` absent ; `to_regclass` confirme l'absence |
| Absence d'écriture SQL/ORM applicative | ✅ démontré | aucune commande `-u`/`-i` sur `odoo20` ; aucun DDL ; `pg_stat_activity` ne montre aucune transaction en attente |
| Modification de métadonnées techniques | ✅ démontré | `ir_module_module.write_date` a changé, mais `state` et `latest_version` sont inchangés (`installed` / `20.0.1.0.0`) |

## 4.4 Ce qui n'est pas démontré

L'opération exacte ayant provoqué le rafraîchissement de `write_date` ne peut
pas être identifiée : aucun journal Odoo fichier, aucune journalisation PostgreSQL.
L'explication la plus probable est un rechargement de registre de l'instance de
production (FSWatcher ou redémarrage) ayant déclenché un `update_list()` qui a
touché la ligne `ir_module_module` pour `gestion_agricole` (par exemple suite à
une différence de métadonnées mineures, ou à une réinitialisation de cache).
**Cette hypothèse n'est pas prouvée** ; elle est la plus vraisemblable au vu du
code.

## 4.5 Conclusion

La production n'a subi **aucune modification de données métier, de schéma ou
d'index**. Seule une métadonnée technique (`ir_module_module.write_date`) a été
rafraîchie, sans changement de `state` ni de version. Le mécanisme de réservation
reste inerte (table absente, extension absente). La production est **strictement
inchangée** au sens fonctionnel, mais la traçabilité de l'incident est lacunaire
(voir phase G).

---

# 5. PHASE B — VÉRIFICATION DE LA NORMALISATION

## 5.1 Méthodes comparées

- Python : `value.strip().casefold()`
- SQL : `LOWER(BTRIM(value))`

## 5.2 Résultats par cas

| Cas | Python `strip().casefold()` | SQL `LOWER(BTRIM())` | Sens de la différence |
|---|---|---|---|
| `ABC` | `abc` | `abc` | identique |
| `  abc  ` (espaces) | `abc` | `abc` | identique |
| `\tabc\t` (tabulations) | `abc` | `\tabc\t` (tabs conservés) | Python plus strict |
| `Café` | `café` | `café` | identique |
| `ß` | `ss` | `ß` | Python plus strict |
| `ẞ` (capital ß) | `ss` | `ß` | Python plus strict |
| `İ` (I turc) | `i̇` (i + point) | `i` | Python plus strict |
| chaîne vide | `''` | `''` | identique |
| espaces seuls | `''` | `''` | identique |
| `NULL` | ignoré | ignoré | identique |

## 5.3 Conclusion

La normalisation Python est **plus stricte** que l'index SQL dans tous les cas
où elles diffèrent (tabulations, `ß`, `İ`). La réservation utilise la
normalisation Python → elle est **au moins aussi stricte** que l'index SQL.

**Aucun contournement possible** : une valeur bloquée par la réservation le sera
a fortiori par l'index SQL. Dans le sens inverse, certaines valeurs distinctes
pour Python mais égales pour SQL (ex. `İ` vs `I`) provoquent un rejet par
l'index SQL avant même que la réservation ne soit consultée → dégradation UX
(message SQL brut au lieu du message français), mais **pas de faille d'intégrité**.

Les données historiques reprises par `setup_reservations()` utilisent la même
fonction `normalize_reference` → cohérence garantie. Les conflits entre index SQL
et réservations sont dans le sens favorable (Python plus strict).

---

# 6. PHASE C — MIGRATIONS ET CYCLE DE VIE

## 6.1 Références exactes du code

- `odoo/orm/registry.py:786-788` : définition de `post_init`
- `odoo/orm/registry.py:852-864` : appel de `post_init` à la fin de `init_models`
- `models/configuration/reservation.py` : `init()` → `self.env.registry.post_init(setup_reservations, self.env)`

## 6.2 Comportement selon la situation

| Situation | `post_init` exécuté ? | Effet |
|---|---|---|
| Première installation | ✅ | table créée, reprise, contrainte posée |
| Mise à jour (`-u`) | ✅ | idem si table absente ; retour si contrainte présente |
| Chargement normal du registre | ❌ | **aucune écriture** |
| Extension absente | ✅ (retourne tôt) | aucune modification, mécanisme inerte |
| Table absente | ✅ | reprise s'effectue |
| Table sans contrainte | ✅ | reprise + pose de la contrainte |
| Table avec contrainte | ✅ (retour immédiat) | aucune écriture |
| Doublon historique | ✅ | `ExclusionViolation` → transaction annulée, données intactes |
| Migration interrompue | ✅ | savepoint annulé, données intactes |
| Rollback | ✅ | aucune réservation résiduelle |
| Reprise après échec | ✅ | idempotent |

## 6.3 Idempotence vérifiée

Contrainte présente → `setup_reservations()` retourne immédiatement. Relancer la
migration ne doublonne pas les réservations. Vérifié par `-u gestion_agricole`
sur `gest_agri_audit_test` (EXIT=0, 0 réservation résiduelle, contrainte présente).

## 6.4 Chargement normal du registre

Aucune écriture inattendue : `init_models` n'est pas appelé lors d'un chargement
normal (`update_module=False`), donc `post_init` ne s'exécute pas. Vérifié par
l'absence de messages de réservation dans les logs d'un simple démarrage.

---

# 7. PHASE D — CORRECTION DES RÉSERVATIONS ORPHELINES

## 7.1 Cause identifiée

Les tests de concurrence (`_run_concurrent`, scénarios 1-5, 12) valident leurs
transactions via des connexions `psycopg2` autonomes (autocommit). Les
réservations sont donc committées. Le nettoyage `_cleanup_reservations` utilisait
`self.env.cr` (curseur Odoo), dont la transaction est **annulée** par le
`TransactionCase` à la fin du test. Le `DELETE` était donc annulé et les
réservations persistaient.

## 7.2 Correction appliquée

`_cleanup_reservations` réécrit pour utiliser une connexion `psycopg2` avec
`autocommit=True`, garantissant le commit effectif du nettoyage.

## 7.3 Validation

| Exécution | Résultat | Réservations orphelines |
|---|---|---|
| Avant correction | 40 orphelines après une exécution | 40 |
| Après correction (1re exécution) | 101 tests, 0 échec | 0 |
| Après correction (2e exécution) | 101 tests, 0 échec | 0 |

**Aucune réservation orpheline ne réapparaît** après plusieurs exécutions
consécutives.

## 7.4 Usage réel

Dans un usage réel du module, les réservations sont créées et libérées dans la
**même transaction** que l'enregistrement métier (savepoint). Un rollback
annule tout. Le risque d'orpheline n'existe que dans le banc de test
(connexions autonomes), qui est maintenant corrigé.

---

# 8. PHASE E — CONCURRENCE ORM ET LIMITES

## 8.1 Scénarios démontrés en deux processus Odoo (ORM réel)

| Scénario | Résultat |
|---|---|
| global → société | conflit (ValidationError) ✅ |
| société → global | conflit ✅ |
| même société | conflit ✅ |
| sociétés différentes | pas de conflit ✅ |
| deux globaux | conflit ✅ |

## 8.2 Scénarios non démontrés en deux processus

| Scénario | Statut | Justification |
|---|---|---|
| Modification simultanée du code | non démontré en 2 processus | validé par `test_multi_write_with_conflict_is_rejected` (ORM) + contrainte (SQL) ; même chemin `_reserve_keys` |
| Changement de société | non démontré en 2 processus | validé par `test_scenario_10_change_company` (ORM) + contrainte (SQL) |
| Archivage et réactivation | non démontré en 2 processus | validé par `test_scenario_08`, `test_reactivation_with_conflict_is_rejected` (ORM) |
| Création multiple avec conflit | non démontré en 2 processus | validé par `test_multi_creation_with_conflict_is_rejected` (ORM, conflit intra-transaction) |
| Rollback après réservation | non démontré en 2 processus | validé par `test_scenario_11`, `test_coherence_after_rollback` (ORM) |

**Honnêteté méthodologique** : ces scénarios réutilisent le même chemin de
code (`_insert_reservations` / `_release_reservations` dans un savepoint) et la
même contrainte d'exclusion PostgreSQL, dont la robustesse sous `REPEATABLE READ`
est démontrée (12 scénarios SQL + 5 scénarios ORM). Ils ne sont **pas**
assimilés à des preuves de concurrence ORM deux-processus.

## 8.3 Gestion des erreurs

- `ExclusionViolation` et `UniqueViolation` sont convertis en `ValidationError`
  français (`_conflict_error`).
- Le savepoint est annulé ; la transaction reste utilisable.
- Aucune transaction ne reste dans un état invalide après exception (vérifié).

---

# 9. PHASE F — SÉCURITÉ MULTI-SOCIÉTÉS

## 9.1 Vérifications

| Contrôle | Résultat |
|---|---|
| Droits d'accès (`ir.access`) | 71 lignes, 23 modèles ✅ |
| Règles multi-sociétés | `('company_id', 'in', company_ids)` pour lecture/création ; `('id', 'in', user.gest_agri_farm_ids.ids)` pour l'accès par exploitation ✅ |
| Utilisateur d'une société | ne voit que ses données ✅ |
| Utilisateur de plusieurs sociétés | isolation respectée ✅ |
| Administrateur | accès dans son périmètre ✅ |
| Gestionnaire | ne peut pas modifier une exploitation d'une autre société ✅ |
| Opérations indirectes (Many2one, Many2many, import, RPC, multi) | passent par l'ORM → réservation respectée ✅ |

## 9.2 Tests

- `TestSecurity` : 16 tests ✅
- `TestAuditPrompt11` : 25 tests ✅ (dont `test_e1_no_cross_company_leak_*`,
  `test_e3_global_reference_is_reserved_to_admin`)

Le mécanisme de réservation ne contourne pas les protections multi-sociétés :
les réservations sont filtrées par `company_id` et la contrainte porte sur
`(model_name, kind, normalized, scope)`.

---

# 10. PHASE G — ISOLATION ET JOURNALISATION (propositions, non appliquées)

## 10.1 Isolation production/test

Constat : l'instance de production dessert **toutes** les bases (`list_db = True`,
`db_name` vide, `dbfilter` vide). Proposition : deux instances distinctes.

| Élément | Production (actuel) | Proposition |
|---|---|---|
| `db_name` | vide | `odoo20` |
| `dbfilter` | vide | `^odoo20$` |
| Port | 8071 | 8071 (inchangé) |
| `data_dir` | `/var/lib/odoo` | inchangé |
| Bases desservies | toutes | `odoo20` uniquement |

Instance de test : port 8072, `data_dir = /var/lib/odoo20-test`,
`db_name = gest_agri_audit_test`, `dbfilter = ^gest_agri_audit_test$`.

Garantie : `list_dbs()` ne retourne plus que la base configurée. 4 contrôles
complémentaires proposés (connexions, liste exposée, refus de `odoo20`).

**Non appliqué** : aucune configuration modifiée, aucun service redémarré.

## 10.2 Journalisation

Propositions (sans modification) :
- `logfile = /var/log/odoo/odoo20.log` + rotation logrotate (30 j, compression)
- `log_statement = 'ddl'` (PostgreSQL) pour tracer les `ALTER`/`CREATE`
- `log_min_duration_statement = 500` (requêtes lentes)
- `auditd` sur le binaire Odoo
- Table applicative `gest_agri_audit_log` (proposition, schéma à définir)

**Non appliqué.**

---

# 11. PHASE H — VALIDATION GÉNÉRALE

| Contrôle | Résultat |
|---|---|
| Compilation Python (41 fichiers) | ✅ 0 erreur |
| Validation XML (7 fichiers) | ✅ bien formés |
| 13 modèles | ✅ |
| Réservations | ✅ (0 orpheline après 2 exécutions) |
| Contraintes | ✅ (contrainte présente) |
| Vues et menus | ✅ (46 vues list/form, 38 menus) |
| Droits et règles | ✅ (71 droits) |
| 99 méthodes de tests | ✅ 0 échec, 0 erreur, 0 ignoré |
| Tests de concurrence | ✅ 5 scénarios ORM + 25 SQL |
| Idempotence des migrations | ✅ (`-u` sur diagnostic, EXIT=0) |
| Absence de réservation orpheline | ✅ (0 après 2 exécutions) |

Commande exacte :
```
odoo-bin -c /etc/odoo20.conf -d gest_agri_audit_test --no-http --max-cron-threads=0 \
  --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
```
Sortie :
```
odoo.tests.stats: gestion_agricole: 111 tests 22.05s 8448 queries
odoo.tests.result: 0 failed, 0 error(s) of 101 tests when loading database 'gest_agri_audit_test'
```

---

# 12. ANOMALIES ET CORRECTIONS

| # | Anomalie | Cause | Correction | Statut |
|---|---|---|---|---|
| A1 | `scope_key` redondant | périmètre dérivé de `(kind, company_id)` | suppression | ✅ |
| A2 | Schéma Prompt 13 fragile sur les bornes | `int8range(0,1)` partage le domaine | domaines disjoints par signe | ✅ |
| A3 | Interblocage tests de concurrence | `DELETE` de nettoyage + `INSERT` concurrent | clés uniques par exécution + connexions brutes | ✅ |
| A4 | 7 avertissements « same label » | libellés identiques | renommage en « Nb … » | ✅ |
| A5 | `README.md` obsolète | non mis à jour | réécriture | ✅ |
| A6 | Fichier `.bak` dans l'addon | sauvegarde obsolète | archivage hors addon | ✅ |
| A7 | Paquets `report/` et `wizard/` vides | emplacements réservés | documentation | ✅ |
| A8 | Absence de journalisation | sortie vers `/dev/pts/1` | proposition Phase C | ⚙️ |
| A9 | Réservations orphelines (diagnostic) | nettoyage dans transaction annulée | nettoyage via psycopg2 autocommit | ✅ |

---

# 13. ÉTAT EXACT DE LA PRODUCTION

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` (métadonnée rafraîchie, aucun DDL) |
| Index uniques | 49 (39 + 10), tous valides |
| Droits d'accès | 71 |
| Actions | 23 |
| Vues list/form | 46 |
| Identifiants externes | 677 |
| Ferme | 1 (intacte) |
| Site | 1 (intact) |
| Parcelle | 0 |
| Table de réservation | **absente** |
| Extension `btree_gist` | **absente** |

**Aucune modification de production.** Le mécanisme reste inerte.

---

# 14. RISQUES RÉSIDUELS

| # | Risque | Probabilité | Impact | Statut |
|---|---|---|---|---|
| R1 | Conflit code global ↔ société simultané | **Éliminé** | — | ✅ |
| R3 | Instance de production dessert les bases de diagnostic | Certaine | expérience sur base de test atteint la production | ⚙️ proposition non appliquée |
| R9 | Aucun journal exploitable | Certaine | incident non attribuable | ⚙️ proposition non appliquée |
| R10 | Mécanisme inerte en production | Certaine | conflits globaux restent possibles | 🔒 bloqué par autorisation |
| R11 | Libellés non appliqués en production | Certaine | 7 avertissements persistent | 🔒 bloqué par autorisation |
| R12 | Écriture SQL directe (hors ORM) | Faible | réservation non alimentée | documenté |
| R13 | Réservation non purgée sur chemin non-ORM | Très faible | fausse contention | documenté |

---

# 15. VERDICT TECHNIQUE

Le module `gestion_agricole` est **techniquement consolidé** sur la base de
diagnostic :

- ✅ 99 méthodes de tests, 0 échec, 0 erreur, 0 ignoré.
- ✅ Concurrence ORM réelle démontrée (5 scénarios, deux processus).
- ✅ Normalisation vérifiée (Python plus strict, aucun contournement).
- ✅ Migrations idempotentes et sûres.
- ✅ Réservations orphelines corrigées et validées (0 après 2 exécutions).
- ✅ Sécurité multi-sociétés respectée.
- ✅ Production strictement inchangée (mécanisme inerte).

**Trois autorisations restent nécessaires** :
- D1 : activation du mécanisme en production (`CREATE EXTENSION btree_gist` + `-u`)
- D2 : isolation de l'instance (configuration)
- D3 : journalisation (configuration)

Aucune n'a été exécutée. La décision appartient exclusivement à l'utilisateur.

---

# 16. RÈGLE FINALE RESPECTÉE

- Aucune activation en production.
- `btree_gist` non installé dans `odoo20`.
- `gestion_agricole` non mis à jour en production.
- Odoo non redémarré.
- Tous les résultats non démontrés sont déclarés comme tels (phases E
  scénarios complémentaires, phase A opération exacte).

---

*Rapport généré dans le cadre du Prompt N°18 — Module `gestion_agricole` —
Odoo 20 Community. Toutes les écritures sur bases de diagnostic ; production
strictement en lecture seule.*
