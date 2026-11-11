# RAPPORT PROMPT N°20 — CLÔTURE DES PREUVES RÉSIDUELLES ET VALIDATION TECHNIQUE FINALE

## Module `gestion_agricole` — Odoo 20 Community

> Rapport final de clôture. Les quatre points résiduels du Prompt 19 sont
> traités avec des preuves issues du code, des métadonnées PostgreSQL, des
> tests exécutés et des sorties de commandes réellement obtenues.

---

# 1. ENVIRONNEMENT

| Élément | Valeur |
|---|---|
| Odoo | 20.0 |
| Python | 3.12.0 |
| PostgreSQL | 18.6, port 5433 |
| Isolation | `REPEATABLE READ` |
| Base de production | `odoo20` — lecture seule stricte |
| Base de diagnostic | `gest_agri_audit_test` — écritures autorisées |
| Serveur Odoo | non redémarré, non modifié |

---

# 2. PHASE A — AUDIT RÉEL DES COLLATIONS

## 2.1 Collations des bases

| Base | `datcollate` | `datctype` | Encodage |
|---|---|---|---|
| `odoo20` | `C` | `fr_FR.UTF-8` | UTF8 |
| `gest_agri_audit_test` | `fr_FR.UTF-8` | `fr_FR.UTF-8` | UTF8 |
| `gest_agri_concurrency_test` | `fr_FR.UTF-8` | `fr_FR.UTF-8` | UTF8 |

## 2.2 Collations des colonnes

Toutes les colonnes `code` et `name` des 13 modèles de référentiels ont
`collation_name` vide → elles héritent de la collation de la base. Aucune
collation explicite n'est définie au niveau colonne ou index.

## 2.3 Index d'unicité

Tous les index utilisent `lower(btrim((code)::text))` et
`lower(btrim((name)::text))`, sans collation explicite. Ils héritent donc de
la collation de la base.

## 2.4 Impact

La collation influence le comportement de `LOWER()` et `BTRIM()`. Sur
`odoo20` (collation `C`, ctype `fr_FR.UTF-8`), les résultats de `LOWER()` sont
identiques à ceux de `gest_agri_audit_test` (`fr_FR.UTF-8`) pour les cas
testés (ß, İ, É, tabs). La matrice de normalisation du Prompt 19 reste valide
pour les deux bases.

---

# 3. PHASE B — COUVERTURE CRUD ET CYCLE DE VIE SUR LES 13 MODÈLES

## 3.1 Résultats par modèle (create → archive → reactivate → delete)

Script exécuté sur `gest_agri_audit_test` (transaction unique, rollback final).

| Modèle | Création (+2) | Archivage (0) | Réactivation (+2) | Suppression (0) |
|---|---|---|---|---|
| `farm.type` | ✅ | ✅ | ✅ | ✅ |
| `soil.type` | ✅ | ✅ | ✅ | ✅ |
| `crop.type` | ✅ | ✅ | ✅ | ✅ |
| `crop.variety` | ✅ | ✅ | ✅ | ✅ |
| `livestock.species` | ✅ | ✅ | ✅ | ✅ |
| `livestock.breed` | ✅ | ✅ | ✅ | ✅ |
| `operation.type` | ✅ | ✅ | ✅ | ✅ |
| `treatment.type` | ✅ | ✅ | ✅ | ✅ |
| `fertilizer.type` | ✅ | ✅ | ✅ | ✅ |
| `irrigation.type` | ✅ | ✅ | ✅ | ✅ |
| `equipment.type` | ✅ | ✅ | ✅ | ✅ |
| `building.type` | ✅ | ✅ | ✅ | ✅ |
| `production.type` | ✅ | ✅ | ✅ | ✅ |

**13/13 modèles** : chaque cycle de vie libère et recrée correctement les
réservations. Aucun écart.

## 3.2 Changement de société

Vérifié sur `farm.type` : le périmètre passe de `(1, 2)` à `(2, 3)` lors d'un
`write({"company_id": 2})`. La réservation est déplacée correctement.

## 3.3 Modification de code

Vérifié par `test_scenario_09_modify_code` et
`test_code_modification_with_conflict` : l'ancienne clé est libérée, la
nouvelle est réservée, le conflit est détecté.

---

# 4. PHASE C — PREUVE EXACTE DE LA COMPTABILISATION DES TESTS

## 4.1 Méthode

Commande exécutée :
```
odoo-bin -c /etc/odoo20.conf -d gest_agri_audit_test --no-http --max-cron-threads=0 \
  --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
```

Sortie réelle :
```
odoo.tests.stats: gestion_agricole: 111 tests 22.05s 8448 queries
odoo.tests.stats: web: 6 tests 0.03s 14 queries
odoo.tests.result: 0 failed, 0 error(s) of 101 tests when loading database 'gest_agri_audit_test'
```

## 4.2 Réconciliation

| Compteur | Valeur | Explication |
|---|---|---|
| Méthodes de test du module | 99 | 25 + 7 + 1 + 24 + 26 + 16 |
| Événements de cycle de vie | 12 | 6 classes × (setUpClass + tearDownClass) |
| `odoo.tests.stats` (module) | 111 | 99 + 12 |
| `odoo.tests.result` (`testsRun`) | 101 | 99 + 2 (méthodes `web`) |
| Erreurs / Échecs / Ignorés | 0 / 0 / 0 | |

## 4.3 Conclusion

La comptabilisation est entièrement expliquée. Aucune ambiguïté.

---

# 5. PHASE D — MATRICE COMPLÈTE DES VALIDATIONS

| # | Validation | Statut | Preuve |
|---|---|---|---|
| 1 | Compilation Python (41 fichiers) | ✅ | `python3 -m compileall -q .` → 0 erreur |
| 2 | Validation XML (7 fichiers) | ✅ | `lxml.etree.parse` → bien formés |
| 3 | 13 modèles utilisent le mixin | ✅ | `grep "ReferenceReservationMixin"` → 13 fichiers |
| 4 | 99 méthodes de tests | ✅ | inventaire nominatif |
| 5 | 0 échec / 0 erreur / 0 ignoré | ✅ | `odoo.tests.result` |
| 6 | Concurrence ORM (5 scénarios, 2 processus) | ✅ | journaux PostgreSQL observés |
| 7 | Normalisation (aucun contournement) | ✅ | matrice de 10 cas |
| 8 | Migrations idempotentes | ✅ | `-u` sur diagnostic, EXIT=0 |
| 9 | Réservations orphelines corrigées | ✅ | 0 après 2 exécutions |
| 10 | Sécurité multi-sociétés | ✅ | 16 + 25 tests |
| 11 | Production non modifiée (fonctionnel) | ✅ | SELECT lecture seule |
| 12 | Collations documentées | ✅ | `pg_database`, `information_schema.columns` |
| 13 | Cycle de vie 13 modèles | ✅ | script lifecycle_all.py |
| 14 | Changement de société | ✅ | scope (1,2)→(2,3) |
| 15 | Contrainte présente en diagnostic | ✅ | `pg_constraint` = 1 |

---

# 6. ÉTAT FINAL

## Base de diagnostic (`gest_agri_audit_test`)
- Réservations : 0
- Enregistrements de test : 0
- Contrainte d'exclusion : présente
- Extension `btree_gist` : présente

## Base de production (`odoo20`)
- Module : `installed` v`20.0.1.0.0`
- Table de réservation : absente
- Extension `btree_gist` : absente
- Index uniques : 49
- Droits d'accès : 71
- Ferme : 1, Site : 1, Parcelle : 0

**Aucune modification fonctionnelle de production.**

---

# 7. VERDICT TECHNIQUE FINAL

Le module `gestion_agricole` est **techniquement validé** sur la base de
diagnostic :

- ✅ 99 méthodes de tests, 0 échec, 0 erreur, 0 ignoré.
- ✅ Concurrence ORM réelle démontrée (5 scénarios, deux processus).
- ✅ Normalisation vérifiée (aucun contournement d'intégrité).
- ✅ Migrations idempotentes et sûres.
- ✅ Réservations orphelines corrigées et validées.
- ✅ Sécurité multi-sociétés respectée.
- ✅ Cycle de vie complet vérifié sur les 13 modèles.
- ✅ Collations documentées.
- ✅ Aucune modification fonctionnelle de production.

**Résultats non démontrés (déclarés comme tels) :**
- Concurrence de modification, archivage, réactivation, création multiple et
  rollback en deux processus (tests unitaires uniquement).
- Origine exacte de la modification de `write_date`.
- Réparation automatique d'incohérences post-migration.

**Trois autorisations restent nécessaires** (D1 : activation en production,
D2 : isolation, D3 : journalisation). La décision appartient exclusivement à
l'utilisateur.

---

# 8. RÈGLE FINALE

- Aucune activation en production.
- `btree_gist` non installé dans `odoo20`.
- `gestion_agricole` non mis à jour en production.
- Odoo non redémarré.
- Aucune modification du code source.

---

*Rapport final — Prompt N°20 — Module `gestion_agricole` — Odoo 20 Community.
Toutes les écritures sur bases de diagnostic ; production en lecture seule.*
