# RAPPORT PROMPT N°22 — PRÉPARATION DU DÉPLOIEMENT SÉCURISÉ DE GESTION_AGRICOLE SUR ODOO 20

## Module `gestion_agricole` — Odoo 20 Community

> Rapport de préparation documentaire. Aucun déploiement réalisé. Aucune
> écriture en production. Aucune modification de fichier actif.

---

# 1. RÉSUMÉ EXÉCUTIF

Trois volets préparatoires :

- **D1** — Activation du mécanisme de réservation GiST en production.
- **D2** — Isolation de l'instance Odoo et des bases de diagnostic.
- **D3** — Journalisation fiable et exploitable.

Livrables produits :
- Ce rapport (`RAPPORT_PROMPT_22_PREPARATION_DEPLOIEMENT_SECURISE.md`).
- `/tmp/odoo20-production-proposed.conf` (modèle, secrets masqués).
- `/tmp/odoo20-test-proposed.conf` (modèle, secrets masqués).

**Aucune action de déploiement n'a été exécutée.** La décision d'activation
appartient exclusivement à l'utilisateur.

---

# 2. ÉTAT INITIAL RÉEL

## 2.1 Processus Odoo

| Élément | Valeur (vérifié) |
|---|---|
| Processus Odoo 20 | PID 328398, utilisateur `kantmoh`, commande `python odoo-bin -c /etc/odoo20.conf` |
| Port d'écoute | 8071 (0.0.0.0) |
| Processus Odoo 16 | PID 766 (instance séparée, non concernée) |
| PostgreSQL | port 5433, version 18.6 |

## 2.2 Configuration active (`/etc/odoo20.conf`)

| Paramètre | Valeur |
|---|---|
| `db_host` | 127.0.0.1 |
| `db_port` | 5433 |
| `db_user` | odoo20 |
| `db_password` | présent (masqué) |
| `db_name` | vide (non défini) |
| `dbfilter` | vide (non défini) |
| `list_db` | True |
| `data_dir` | /var/lib/odoo |
| `logfile` | absent (sortie stdout) |
| `log_level` | info |
| `http_interface` | 0.0.0.0 |
| `http_port` | 8071 |
| `admin_passwd` | présent (masqué) |
| `addons_path` | 6 chemins (dont kantmoh) |

## 2.3 PostgreSQL

| Élément | Valeur |
|---|---|
| Version | 18.6 (Debian 18.6-1.pgdg12+2) |
| Extensions installées | `plpgsql` 1.0, `pg_trgm` 1.6 |
| `btree_gist` | disponible (v1.8), **non installé** |
| Bases présentes | `odoo20`, `gest_agri_audit_test`, `gest_agri_concurrency_test`, `adoo20`, `odoo2000` |
| `log_statement` | none |
| `logging_collector` | off |
| `log_connections` | (vide) |
| `log_disconnections` | off |
| `log_min_duration_statement` | -1 |
| `log_line_prefix` | `%m [%p] %q%u@%d` |

## 2.4 Données de production (lecture seule)

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` |
| `write_uid` | 1 |
| Index uniques | 49 (39 + 10), 0 invalide |
| ACL | 71 |
| Actions | 23 |
| Vues list/form | 46 |
| Identifiants XML | 677 |
| Exploitations | 1 |
| Sites | 1 |
| Parcelles | 0 |
| Table de réservation | absente |
| Extension `btree_gist` | absente |

Comparaison avec les rapports 19-21 : **aucune différence**.

---

# 3. D1 — PRÉPARATION DE L'ACTIVATION GISt

## 3.1 Code actuel

- `models/configuration/reservation.py` (443 lignes) : détection via
  `_extension_present()` (SELECT sur `pg_extension`), retour silencieux si
  absente.
- `models/configuration/_common.py` (130 lignes) : `normalize_reference`,
  `reference_scope`.
- 13 modèles utilisent `ReferenceReservationMixin`.
- Hook `post_init` : `self.env.registry.post_init(setup_reservations, self.env)`.
- Index : 39 de configuration + 10 patrimoniaux (déjà en production).

## 3.2 Prérequis DBA

| Élément | Détail |
|---|---|
| Privilèges | Propriétaire de la base (`odoo20` est propriétaire) |
| Compatibilité | PostgreSQL 18.6, extension `btree_gist` v1.8 disponible |
| Commande (documentaire) | `CREATE EXTENSION btree_gist;` |
| Risques | Verrou sur la base pendant l'installation (brève) |
| Durée | Non estimable sans test ; attendue < 1 min |
| Fenêtre de maintenance | Recommandée (pas obligatoire, mais prudente) |

**Non exécuté en production.**

## 3.3 Précontrôles avant migration (SELECT uniquement)

Requêtes de détection des doublons historiques :

```sql
-- Doublons de code par société
SELECT company_id, lower(btrim(code)), count(*)
FROM gest_agri_soil_type
WHERE active IS TRUE AND company_id IS NOT NULL
GROUP BY company_id, lower(btrim(code)) HAVING count(*) > 1;

-- Doublons de code global
SELECT lower(btrim(code)), count(*)
FROM gest_agri_soil_type
WHERE active IS TRUE AND company_id IS NULL
GROUP BY lower(btrim(code)) HAVING count(*) > 1;

-- Conflit global ↔ société
SELECT g.code, c.company_id
FROM gest_agri_soil_type g
JOIN gest_agri_soil_type c ON lower(btrim(g.code)) = lower(btrim(c.code))
WHERE g.active IS TRUE AND g.company_id IS NULL
  AND c.active IS TRUE AND c.company_id IS NOT NULL;
```

(À répéter pour les 13 tables et les deux champs `code` et `name`.)

## 3.4 Procédure de migration proposée (documentaire)

1. Validation de la sauvegarde (voir §5).
2. Contrôle des prérequis PostgreSQL (`btree_gist` disponible).
3. Contrôle des doublons historiques (requêtes ci-dessus).
4. Vérification des privilèges DBA.
5. Installation de `btree_gist` (par le DBA).
6. Mise à jour contrôlée du module (`-u gestion_agricole`).
7. Création de la table de réservation (automatique via `post_init`).
8. Backfill des réservations existantes (automatique).
9. Création de la contrainte d'exclusion (automatique).
10. Validation des réservations (`SELECT count(*) FROM gest_agri_reference_reservation`).
11. Validation des index (`pg_index.indisvalid`).
12. Tests fonctionnels (création, modification, archivage).
13. Contrôle des journaux.
14. Décision de réouverture.

**Condition d'arrêt** : toute erreur `ExclusionViolation`, `UniqueViolation` ou
`Permission denied` annule la transaction. Restaurer depuis la sauvegarde.

## 3.5 Limites à résoudre avant activation

| Point | Classification | Détail |
|---|---|---|
| Divergence Python `casefold()` / SQL `LOWER()` | Important | Pas de contournement d'intégrité ; dégradation UX pour `İ`/`I` |
| Collation production (`C`) vs diagnostic (`fr_FR.UTF-8`) | Important | Comportements identiques pour les cas testés |
| `setup_reservations()` ne répare pas les incohérences | Important | Idempotence seulement ; pas de réparation automatique |
| Écritures SQL directes hors ORM | Acceptable avec procédure | Documenté ; hors périmètre ORM |
| Réservations orphelines (chemins non-ORM) | Acceptable avec procédure | Corrigé dans les tests ; risque faible en production |
| Concurrence non démontrée sur certains chemins | Amélioration ultérieure | Tests unitaires + contrainte SQL suffisants |

**Aucun point n'est classé bloquant.** Les points importants nécessitent une
procédure et une surveillance, mais ne bloquent pas l'activation.

---

# 4. D2 — ISOLATION DE L'INSTANCE ODOO

## 4.1 État actuel

- `db_name` vide → `list_dbs()` interroge PostgreSQL et retourne **toutes**
  les bases (`odoo20`, `gest_agri_audit_test`, `gest_agri_concurrency_test`,
  `adoo20`, `odoo2000`).
- `dbfilter` vide → aucune restriction.
- `list_db = True` → toutes les bases sont exposées.
- Un seul processus Odoo dessert toutes les bases.

## 4.2 Architecture cible proposée

### Production
- `db_name = odoo20`
- `dbfilter = ^odoo20$`
- `list_db = False`
- Port 8071 conservé
- `data_dir = /var/lib/odoo`
- Journalisation dédiée

### Diagnostic
- `db_name = gest_agri_audit_test`
- `dbfilter = ^gest_agri_audit_test$`
- Port 8072
- `data_dir = /var/lib/odoo20-test`
- Journalisation dédiée
- Processus distinct

## 4.3 Fichiers modèles

Créés :
- `/tmp/odoo20-production-proposed.conf`
- `/tmp/odoo20-test-proposed.conf`

Secrets masqués (`<SECRET_A_CONFIGURER>`). Aucune installation dans `/etc`.

## 4.4 Procédure de bascule future (documentaire)

1. Sauvegarde préalable (`pg_dump -Fc odoo20`).
2. Vérification des ports (8072 libre).
3. Création des répertoires (`/var/lib/odoo20-test`, `/var/log/odoo20-test`).
4. Modification de `/etc/odoo20.conf` (ajout `db_name`, `dbfilter`).
5. Création de `/etc/odoo20-test.conf`.
6. Arrêt propre de la production (`kill -INT <pid>`).
7. Démarrage de la production avec la nouvelle config.
8. Démarrage de l'instance de test.
9. Vérification HTTP (port 8071 → uniquement odoo20 ; port 8072 → uniquement gest_agri_audit_test).
10. Vérification des connexions PostgreSQL.
11. Contrôle des journaux.
12. Critères de réussite : 4 contrôles (connexions, liste exposée, refus odoo20, HTTP 404).
13. Retour arrière : restaurer `/etc/odoo20.conf` depuis la sauvegarde.

**Aucune bascule réelle effectuée.**

---

# 5. D3 — JOURNALISATION ET TRAÇABILITÉ

## 5.1 Audit de la journalisation actuelle

| Paramètre | Valeur actuelle |
|---|---|
| `logfile` | absent (stdout du processus) |
| `log_level` | info |
| Rotation | aucune |
| `log_statement` (PG) | none |
| `logging_collector` (PG) | off |
| `log_connections` (PG) | (vide) |
| `log_disconnections` (PG) | off |
| `log_min_duration_statement` (PG) | -1 |
| `log_line_prefix` (PG) | `%m [%p] %q%u@%d` |

## 5.2 Proposition Odoo

Ajouter à `/etc/odoo20.conf` :
```
logfile = /var/log/odoo/odoo20.log
log_level = info
```

Rotation via logrotate (30 jours, compression, `copytruncate`).

Permissions : `/var/log/odoo` → `kantmoh:kantmoh`, mode 750.

Traçabilité applicative : table `gest_agri_audit_log` (proposition, schéma à
définir) alimentée par `setup_reservations()` et les opérations de réservation.

## 5.3 Proposition PostgreSQL

```
log_statement = 'ddl'          # trace les modifications de schema
log_connections = on
log_disconnections = on
log_min_duration_statement = 500
log_line_prefix = '%m [%p] %q%u@%d '
```

Accès au journal PostgreSQL : ajouter `kantmoh` au groupe `postgres` (lecture
seule) ou copier les logs avec `chmod 644` dans un répertoire lisible.

## 5.4 Conservation et protection

| Élément | Propriétaire | Mode | Durée |
|---|---|---|---|
| `/var/log/odoo/odoo20.log` | kantmoh:kantmoh | 640 | 30 jours |
| `/var/log/postgresql/*.log` | postgres:postgres | 640 | 30 jours (rotation existante) |
| `/var/log/odoo20-test/` | kantmoh:kantmoh | 750 | 30 jours |

Masquage des secrets : ne jamais logger de mots de passe, jetons ou données
personnelles. Odoo ne logge pas les mots de passe par défaut.

---

# 6. SAUVEGARDE ET RETOUR ARRIÈRE

## 6.1 Sauvegarde (documentaire)

```bash
# Sauvegarde logique
pg_dump -Fc -U odoo20 -h 127.0.0.1 -p 5433 odoo20 > /backup/odoo20_$(date +%Y%m%d_%H%M%S).dump

# Vérification
pg_restore --list /backup/odoo20_*.dump | head

# Test de restauration dans une base isolée
createdb -U odoo20 -h 127.0.0.1 -p 5433 odoo20_restore_test
pg_restore -U odoo20 -h 127.0.0.1 -p 5433 -d odoo20_restore_test /backup/odoo20_*.dump
```

Ne réalise aucune sauvegarde pendant cette mission.

## 6.2 Retour arrière

| Scénario | Décision | État de la base | Restauration nécessaire ? |
|---|---|---|---|
| Échec avant création de l'extension | Arrêt | inchangée | non |
| Échec pendant le backfill | Arrêt, rollback automatique | transaction annulée | non |
| Échec pendant la création de la contrainte | Arrêt, rollback automatique | transaction annulée | non |
| Échec de mise à jour du module | Arrêt | transaction annulée | non (sauf corruption) |
| Erreur après migration | Évaluation | données modifiées | possible |
| Erreur fonctionnelle après réouverture | Évaluation | données modifiées | possible |

Ne jamais supprimer manuellement des tables ou contraintes sans évaluer les
dépendances.

## 6.3 Critères d'autorisation

- [ ] Sauvegarde vérifiée (test de restauration réussi).
- [ ] Doublons historiques contrôlés (requêtes SELECT exécutées).
- [ ] Privilèges DBA confirmés.
- [ ] Fenêtre de maintenance planifiée.
- [ ] Procédure de retour arrière documentée et comprise.
- [ ] Autorisation explicite de l'utilisateur.
- [ ] Isolation de l'instance appliquée (D2) — recommandé avant D1.
- [ ] Journalisation activée (D3) — recommandé avant D1.

---

# 7. MATRICE DES RISQUES

| Risque | Probabilité | Impact | Criticité | Mesure | Responsable |
|---|---|---|---|---|---|
| Incompatibilité de collation | Faible | Moyen | Important | Matrice de 10 cas vérifiée | DBA |
| Doublons historiques | Faible | Élevé | Important | Requêtes SELECT pré-migration | DBA |
| Privilèges insuffisants pour `btree_gist` | Faible | Moyen | Important | Vérification préalable | DBA |
| Échec du backfill | Faible | Moyen | Important | Transaction atomique, rollback | Odoo |
| Conflit d'exclusion | Faible | Moyen | Important | Tests de concurrence | Odoo |
| Rollback incomplet | Très faible | Élevé | Important | Savepoint + transaction | Odoo |
| Instance accessible à plusieurs bases | Certaine (actuel) | Élevé | **Bloquant** | Isolation D2 | Admin |
| Perte de journalisation | Certaine (actuel) | Moyen | Important | Journalisation D3 | Admin |
| Écriture SQL directe | Faible | Faible | Acceptable | Documentation | Utilisateur |
| Réservation orpheline | Très faible | Faible | Acceptable | Tests corrigés | Odoo |
| Concurrence non testée sur certains chemins | Moyen | Faible | Amélioration | Tests supplémentaires | Odoo |
| Sauvegarde non restaurable | Faible | Élevé | Important | Test de restauration | DBA |
| Interruption de service | Faible | Élevé | Important | Fenêtre de maintenance | Admin |

---

# 8. DÉCISIONS PROPOSÉES

| Décision | Statut proposé | Justification |
|---|---|---|
| D1 — Activation GiST en production | **SOUS CONDITIONS** | Mécanisme validé sur diagnostic ; prérequis DBA et sauvegarde nécessaires ; points importants à surveiller |
| D2 — Isolation de l'instance | **AUTORISABLE** | Proposition documentée, procédure de retour arrière prévue, aucune modification appliquée |
| D3 — Journalisation | **AUTORISABLE** | Proposition documentée, compromis traçabilité/performance explicités |

**Aucune décision ne signifie une exécution.** L'utilisateur doit autoriser
explicitement chaque action.

---

# 9. LIMITES ET INCONNUES

- La durée exacte de l'installation de `btree_gist` n'est pas mesurée.
- L'origine de la modification de `write_date` reste inconnue.
- La réparation automatique des incohérences post-migration n'existe pas.
- Les scénarios de concurrence complémentaires ne sont pas démontrés en
  deux processus.
- Les collations diffèrent entre production (`C`) et diagnostic (`fr_FR.UTF-8`),
  bien que les résultats soient identiques pour les cas testés.

---

# 10. CONCLUSION

Ce rapport fournit un plan de déploiement sûr, reproductible, réversible et
compréhensible. Aucune action n'a été exécutée. La décision finale appartient
exclusivement à l'utilisateur.

**Ne déploie rien. Ne modifie rien en production. Ne mets pas à jour Odoo.
N'installe pas `btree_gist` en production. Ne redémarre aucun service. Ne
modifie aucun fichier de configuration actif.**

---

*Rapport de préparation — Prompt N°22 — Module `gestion_agricole` — Odoo 20
Community. Aucune écriture en production. Aucun déploiement.*
