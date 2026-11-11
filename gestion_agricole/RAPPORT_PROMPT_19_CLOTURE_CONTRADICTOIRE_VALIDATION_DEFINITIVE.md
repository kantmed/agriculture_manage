# RAPPORT PROMPT N°19 — CLÔTURE CONTRADICTOIRE ET VALIDATION DÉFINITIVE DES PREUVES

## Module `gestion_agricole` — Odoo 20 Community

> Rapport de clôture contradictoire. Toutes les affirmations des rapports
> précédents ont été re-vérifiées. Les conclusions excessives ont été corrigées.
> Verdict fondé exclusivement sur des preuves vérifiables.

---

# 1. ENVIRONNEMENT

| Élément | Valeur |
|---|---|
| Odoo | 20.0, `/mnt/srv/share/odoo20/odoo` |
| Python | 3.12.0 |
| PostgreSQL | 18.6, port 5433 |
| Isolation | `REPEATABLE READ` |
| Base de production | `odoo20` — lecture seule stricte |
| Base de diagnostic | `gest_agri_audit_test` — écritures autorisées |
| Serveur Odoo | non redémarré, non modifié |

---

# 2. PHASE A — RECTIFICATION DE LA TRAÇABILITÉ PRODUCTION

## 2.1 État actuel de la production (lecture seule)

| Champ | Valeur |
|---|---|
| `state` | `installed` |
| `latest_version` | `20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` |
| `write_uid` | `1` (superutilisateur) |
| `create_date` | `2026-11-10 12:28:33.934242` |
| `create_uid` | `2` |

## 2.2 Ce que les éléments disponibles permettent d'affirmer

| # | Affirmation | Statut | Preuve |
|---|---|---|---|
| 1 | Absence de modification des données métier constatée | ✅ démontré | 1 ferme + 1 site intacts, 0 parcelle, aucune écriture applicative |
| 2 | Absence de modification du schéma constatée | ✅ démontré | 49 index uniques, table de réservation absente, `btree_gist` absent |
| 3 | Absence de modification des index constatée | ✅ démontré | `pg_indexes` : 49 index uniques, inchangés |
| 4 | Modification d'une métadonnée technique constatée | ✅ démontré | `ir_module_module.write_date` a changé, `write_uid = 1` |
| 5 | Origine exacte de la modification non déterminée | ✅ démontré | aucun journal Odoo fichier, PostgreSQL `logging_collector = off`, `log_statement = none` |

## 2.3 Rectification

La phrase « Aucune écriture SQL/ORM applicative n'a eu lieu » est **retirée**.
Elle est remplacée par la distinction ci-dessus.

`pg_stat_activity` n'est **pas** un historique des transactions passées ; il ne
permet pas d'identifier l'opération responsable.

L'hypothèse FSWatcher / rechargement de registre / `update_list()` **n'est pas
démontrée**. Elle reste une hypothèse plausible au vu du code Odoo 20
(`update_list()` écrit `updated_values` si un champ du manifeste diffère), mais
aucun journal ne la confirme.

**« L'origine exacte de la modification de `write_date` n'est pas déterminable
avec les journaux et éléments actuellement disponibles. »**

## 2.4 Verdict production

La production n'a subi **aucune modification fonctionnelle** (données, schéma,
index). Seule une métadonnée technique (`ir_module_module.write_date`) a été
rafraîchie par une opération non identifiée. Le mécanisme de réservation reste
inerte (table absente, extension absente). Le terme « strictement inchangée »
est remplacé par « aucune modification fonctionnelle constatée ; une métadonnée
technique a été modifiée par une opération non identifiée ».

---

# 3. PHASE B — NORMALISATION PYTHON / POSTGRESQL

## 3.1 Matrice de comparaison (base diagnostic, collation `fr_FR.UTF-8`)

| Cas | Valeurs | Python `strip().casefold()` | SQL `LOWER(BTRIM())` | Réservation | Index SQL | Conclusion |
|---|---|---|---|---|---|---|
| 1 | `ABC` / `abc` | `abc` / `abc` | `abc` / `abc` | conflit | conflit | identique |
| 2 | espaces `  abc  ` | `abc` | `abc` | conflit | conflit | identique |
| 3 | tabulations `\tabc\t` | `abc` | `\tabc\t` (tabs conservés) | conflit | pas de conflit | **Python plus strict** |
| 4 | `é` / `É` | `é` / `é` | `é` / `é` | conflit | conflit | identique |
| 5 | `ß` / `ss` | `ss` / `ss` | `ß` / `ss` | conflit | pas de conflit | **Python plus strict** |
| 6 | `ẞ` / `SS` | `ss` / `ss` | `ß` / `ss` | conflit | pas de conflit | **Python plus strict** |
| 7 | `İ` / `I` | `i̇` / `i` (distincts) | `i` / `i` (égaux) | pas de conflit | conflit | **SQL plus strict** |
| 8 | chaîne vide | `''` | `''` | ignoré | ignoré | identique |
| 9 | espaces seuls | `''` | `''` | ignoré | ignoré | identique |
| 10 | `NULL` | ignoré | ignoré | ignoré | ignoré | identique |

## 3.2 Rectification

L'affirmation « Python est plus strict dans tous les cas » est **incorrecte**.
Pour le cas `İ` / `I`, c'est le SQL qui est plus strict (l'index bloque, la
réservation laisse passer → erreur SQL brute au lieu du message français).

## 3.3 Verdict

- **Intégrité des données** : ✅ protégée. Le couple réservation + index SQL
  bloque tous les doublons dans les deux sens. Python plus strict pour tabs/ß,
  SQL plus strict pour İ. Aucun doublon ne passe.
- **Cohérence des clés** : ✅ la réservation utilise `normalize_reference()`
  de manière cohérente.
- **Qualité du message** : ⚠️ dégradation pour le cas `İ` / `I` (message SQL
  brut au lieu du message français). Non bloquant pour l'intégrité.
- **Collation** : les résultats dépendent de la collation. Vérifiés sur
  `gest_agri_audit_test` (`fr_FR.UTF-8`) et `odoo20` (collation `C`, ctype
  `fr_FR.UTF-8`). Comportements identiques pour les cas testés.

---

# 4. PHASE C — RÉCONCILIATION DES STATISTIQUES

## 4.1 Inventaire exact par classe

| Classe | Méthodes découvertes | Exécutées | Réussies | Échecs | Erreurs | Ignorées |
|---|---|---|---|---|---|---|
| `TestAuditPrompt11` | 25 | 25 | 25 | 0 | 0 | 0 |
| `TestConfiguration` | 7 | 7 | 7 | 0 | 0 | 0 |
| `TestModuleInstall` | 1 | 1 | 1 | 0 | 0 | 0 |
| `TestPatrimony` | 24 | 24 | 24 | 0 | 0 | 0 |
| `TestReservationUnicity` | 26 | 26 | 26 | 0 | 0 | 0 |
| `TestSecurity` | 16 | 16 | 16 | 0 | 0 | 0 |
| **Total** | **99** | **99** | **99** | **0** | **0** | **0** |

## 4.2 Explication des compteurs

| Compteur | Valeur | Signification |
|---|---|---|
| Méthodes de test du module | **99** | Les 99 méthodes listées ci-dessus |
| `odoo.tests.stats` (ligne module) | **111** | 99 méthodes + 12 événements de cycle de vie (`setUpClass`/`tearDownClass` des 6 classes) |
| `odoo.tests.result` (`testsRun`) | **101** | 99 méthodes du module + 2 méthodes du module `web` (test de vues) |
| Événements de cycle de vie | **12** | Non comptés dans `testsRun` |

**Les événements de cycle de vie ne sont pas des tests exécutés.** Ils sont des
hooks appelés par le runner. La ligne `111` de `odoo.tests.stats` les inclut
dans son total, ce qui explique la différence avec `testsRun = 101`.

## 4.3 Conclusion

Les statistiques sont réconciliées : **99 méthodes de test**, **0 échec**,
**0 erreur**, **0 ignoré**. Le chiffre pertinent pour la qualité du code est
**99 méthodes**.

---

# 5. PHASE D — COHÉRENCE DES RÉSERVATIONS

## 5.1 Vérification sur les 13 modèles

Testé via création ORM de 1 enregistrement par modèle (transaction unique,
rollback final). Résultats :

| Modèle | Création | +2 réservations | Archivage libère | Changement société déplace |
|---|---|---|---|---|
| `farm.type` | ✅ | ✅ | — | ✅ |
| `soil.type` | ✅ | ✅ | ✅ (42→40) | — |
| `crop.type` | ✅ | ✅ | — | — |
| `crop.variety` | ✅ | ✅ | — | — |
| `livestock.species` | ✅ | ✅ | — | — |
| `livestock.breed` | ✅ | ✅ | — | — |
| `operation.type` | ✅ | ✅ | — | — |
| `treatment.type` | ✅ | ✅ | — | — |
| `fertilizer.type` | ✅ | ✅ | — | — |
| `irrigation.type` | ✅ | ✅ | — | — |
| `equipment.type` | ✅ | ✅ | — | — |
| `building.type` | ✅ | ✅ | — | — |
| `production.type` | ✅ | ✅ | — | — |

Aucune ligne « PROBLEM » émise. Chaque enregistrement actif possède ses
deux réservations (code + nom).

## 5.2 Idempotence vs cohérence

`setup_reservations()` retourne immédiatement si la contrainte d'exclusion
existe déjà. Ce comportement garantit l'**idempotence** de la migration, mais
**pas la cohérence** : si une table existante avec contrainte contient des
réservations manquantes ou incohérentes, elles ne sont **pas réparées**
automatiquement.

**Limite explicite** : `setup_reservations()` n'est pas un outil de réparation.
Il est un outil de migration initiale. Toute incohérence post-migration
nécessite une intervention manuelle (ou un futur outil de réconciliation).

## 5.3 Réservations orphelines des tests

`_cleanup_reservations()` :
- utilise des identifiants de test uniques (token UUID) ✅
- ne supprime que les réservations du scénario concerné (filtre par
  `normalized = ANY(...)`) ✅
- ne peut pas supprimer les réservations d'un autre test (clés uniques) ✅
- fonctionne après succès, échec et exception (utilise `psycopg2` autocommit) ✅
- ne laisse aucune réservation résiduelle après plusieurs exécutions ✅ (0 après 2 runs)

Aucune purge globale n'a été utilisée.

---

# 6. PHASE E — CONCURRENCE ORM : PORTÉE EXACTE

## 6.1 Scénarios démontrés en deux processus (ORM réel)

| # | Scénario | Résultat | Preuve |
|---|---|---|---|
| 1 | global → société | conflit (ValidationError) | journal PostgreSQL observé |
| 2 | société → global | conflit | journal observé |
| 3 | même société | conflit | journal observé |
| 4 | sociétés différentes | pas de conflit | journal observé |
| 5 | deux globaux | conflit | journal observé |

Les opérations passent réellement par `create` du mixin → `_reserve_keys` →
`_insert_reservations` → `INSERT INTO gest_agri_reference_reservation` →
contrainte d'exclusion PostgreSQL. Vérifié par le journal d'erreur du
processus B.

## 6.2 Scénarios non démontrés en deux processus

| Scénario | Type de preuve disponible | Type de preuve manquant |
|---|---|---|
| Modification simultanée du code | test unitaire ORM + contrainte SQL | concurrence 2 processus |
| Changement de société | test unitaire ORM + contrainte SQL | concurrence 2 processus |
| Archivage | test unitaire ORM + contrainte SQL | concurrence 2 processus |
| Réactivation | test unitaire ORM + contrainte SQL | concurrence 2 processus |
| Création multiple | test unitaire ORM (intra-transaction) | concurrence 2 processus |
| Rollback après réservation | test unitaire ORM | concurrence 2 processus |

**Ces scénarios ne sont pas démontrés en concurrence réelle à deux
transactions indépendantes.** Ils sont validés par des tests unitaires ORM et
par la contrainte PostgreSQL (tests SQL bruts), qui prouvent la robustesse de
la contrainte sous `REPEATABLE READ`. Ils ne sont **pas** assimilés à des
preuves de concurrence ORM.

## 6.3 Conclusion

- Concurrence de création : ✅ démontrée (5 scénarios, 2 processus).
- Concurrence de modification : ⚠️ non démontrée en 2 processus (tests unitaires).
- Concurrence d'archivage/réactivation : ⚠️ non démontrée en 2 processus.
- Robustesse de la contrainte PostgreSQL sous `REPEATABLE READ` : ✅ démontrée
  (12 scénarios SQL + 5 scénarios ORM).

---

# 7. PHASE F — CYCLE DE VIE ET PRÉREQUIS BTREE_GIST

## 7.1 Réponses aux questions

1. **Le module exécute-t-il `CREATE EXTENSION` ?** Non. Vérifié :
   `grep -rn "CREATE EXTENSION" models/` → 0 occurrence. Le module ne fait que
   vérifier la présence (`_extension_present`).

2. **Qui doit installer `btree_gist` ?** Le DBA, manuellement, avant la mise à
   jour du module : `CREATE EXTENSION btree_gist;`.

3. **Privilèges nécessaires** : droits du propriétaire de la base (extension de
   confiance en PG ≥ 13). Odoo se connecte en tant que `odoo20` (propriétaire).

4. **Extension absente** : `setup_reservations()` journalise `INFO` et retourne
   sans créer la table ni la contrainte. `_reservation_active()` retourne
   `False` → le mixin ne réserve rien → mécanisme inerte.

5. **Première installation** : si l'extension est présente, table créée + reprise
   + contrainte posée. Sinon, mécanisme inerte.

6. **Mise à jour** : idem. Si la contrainte existe déjà, retour immédiat.

7. **Chargement normal du registre** : `init_models` n'est pas appelé →
   `post_init` ne s'exécute pas → aucune écriture.

8. **Table existe sans contrainte** : reprise + pose de la contrainte.

9. **Contrainte existe déjà** : retour immédiat (idempotence).

10. **Doublons historiques** : `ExclusionViolation` → transaction annulée,
    données intactes, contrainte non posée.

## 7.2 Références code

- `odoo/orm/registry.py:786-788` : `post_init` définition
- `odoo/orm/registry.py:852-864` : appel à la fin de `init_models`
- `reservation.py:83-90` : `_extension_present`
- `reservation.py:223-233` : vérification et retour si extension absente
- `reservation.py:220-222` : retour si contrainte présente

**Aucune installation de `btree_gist` dans `odoo20`.**

---

# 8. PHASE G — SÉCURITÉ ET ISOLATION

## 8.1 ACL et règles multi-sociétés

| Contrôle | Résultat |
|---|---|
| Droits d'accès | 71 lignes, 23 modèles ✅ |
| Règles multi-sociétés | `('company_id', 'in', company_ids)` ✅ |
| Utilisateur mono-société | ne voit que ses données ✅ |
| Utilisateur multi-sociétés | isolation respectée ✅ |
| Administrateur | accès dans son périmètre ✅ |
| Gestionnaire | ne peut pas modifier une exploitation d'une autre société ✅ |

## 8.2 Tests

- `TestSecurity` : 16 tests ✅
- `TestAuditPrompt11` : 25 tests ✅

Le mécanisme de réservation ne contourne pas les protections multi-sociétés.

---

# 9. ÉTAT EXACT DE LA PRODUCTION

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` (métadonnée rafraîchie) |
| `write_uid` | `1` |
| Index uniques | 49 (39 + 10) |
| Droits d'accès | 71 |
| Actions | 23 |
| Vues list/form | 46 |
| Identifiants externes | 677 |
| Ferme | 1 (intacte) |
| Site | 1 (intact) |
| Table de réservation | **absente** |
| Extension `btree_gist` | **absente** |

**Aucune modification fonctionnelle.** Une métadonnée technique a été rafraîchie
par une opération non identifiée.

---

# 10. RISQUES RÉSIDUELS

| # | Risque | Statut |
|---|---|---|
| R1 | Conflit code global ↔ société simultané | ✅ **ÉLIMINÉ** (preuve ORM réelle) |
| R3 | Instance dessert les bases de diagnostic | ⚙️ proposition non appliquée |
| R9 | Aucun journal exploitable | ⚙️ proposition non appliquée |
| R10 | Mécanisme inerte en production | 🔒 bloqué par autorisation |
| R11 | Libellés non appliqués en production | 🔒 bloqué par autorisation |
| R12 | Écriture SQL directe (hors ORM) | documenté |
| R13 | Réservation non purgée sur chemin non-ORM | documenté |

---

# 11. VERDICT TECHNIQUE FINAL

## Ce qui est démontré

- ✅ 99 méthodes de tests, 0 échec, 0 erreur, 0 ignoré.
- ✅ Concurrence ORM réelle démontrée (5 scénarios, deux processus).
- ✅ Normalisation vérifiée (aucun contournement d'intégrité ; dégradation UX
  pour `İ`/`I`).
- ✅ Migrations idempotentes et sûres.
- ✅ Réservations orphelines corrigées et validées (0 après 2 exécutions).
- ✅ Sécurité multi-sociétés respectée.
- ✅ Aucune modification fonctionnelle de production.

## Ce qui n'est pas démontré

- ⚠️ Concurrence de modification, archivage, réactivation, création multiple et
  rollback en deux processus (tests unitaires uniquement).
- ⚠️ Origine exacte de la modification de `write_date`.
- ⚠️ Réparation automatique d'incohérences post-migration.

## Conclusions rectifiées

1. La production n'est **pas** « strictement inchangée » au sens absolu : une
   métadonnée technique a été rafraîchie par une opération non identifiée. Elle
   n'a subi **aucune modification fonctionnelle**.
2. Python n'est **pas** universellement plus strict que SQL (cas `İ`/`I`).
3. `setup_reservations()` garantit l'idempotence, **pas** la cohérence.
4. Les scénarios de concurrence complémentaires ne sont **pas** démontrés en
   deux processus.

**Trois autorisations restent nécessaires** (D1, D2, D3). La décision appartient
exclusivement à l'utilisateur.

---

# 12. RÈGLE FINALE

- Aucune activation en production.
- `btree_gist` non installé dans `odoo20`.
- `gestion_agricole` non mis à jour en production.
- Odoo non redémarré.
- Tous les résultats non démontrés sont déclarés comme tels.

---

*Rapport de clôture contradictoire — Prompt N°19 — Module `gestion_agricole` —
Odoo 20 Community. Toutes les écritures sur bases de diagnostic ; production en
lecture seule.*
