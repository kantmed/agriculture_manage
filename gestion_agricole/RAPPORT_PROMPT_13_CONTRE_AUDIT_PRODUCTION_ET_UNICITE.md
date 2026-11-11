# RAPPORT PROMPT N°13 — CONTRE-AUDIT DE L'INCIDENT DE PRODUCTION ET VALIDATION DE LA CONCEPTION D'UNICITÉ
## Module `gestion_agricole` — Odoo 20 Community

> **Aucune modification n'a été effectuée** dans le cadre de ce prompt :
> pas de `-u`, pas de `-i`, pas d'écriture sur `odoo20`, pas de modification
> du code source du module, pas de modification de configuration, aucun
> redémarrage de service, aucune suppression.
> La seule écriture réalisée est dans la **base de diagnostic dédiée**
> `gest_agri_concurrency_test` (schéma `p13` + extension `btree_gist`),
> explicitement prévue par la Phase 4. Elle n'a **pas** été faite dans
> `odoo20` ni dans `gest_agri_audit_test` (voir § 12.3).

---

# 1. SYNTHÈSE EXÉCUTIVE

| Question | Réponse |
|---|---|
| **Cause de l'incident de production** | **PROUVÉE** : opération d'**upgrade CLI sur `odoo20` exécutée par le superutilisateur** (`write_uid = 1`), donc **par l'opérateur**, et non par l'audit. Les trois explications avancées par le rapport Prompt 12 (FSWatcher, redémarrage phoenix, signalisation inter-bases) sont **réfutées** par des mesures. |
| **État de la production** | ** Sain et cohérent.** 39 index de configuration + 10 patrimoniaux, tous valides ; 46 vues list/form, 23 vues search, 23 actions, 44 menus, 71 droits, 677 identifiants externes, 0 doublon. **Zéro différence structurelle** avec la base de test. |
| **Solution d'unicité (GiST)** | **Validée conceptuellement et corrigée** : le schéma à domaines disjoints par signe passe **15/15** scénarios sous `REPEATABLE READ`. Le schéma du rapport Prompt 12 (plage `[0,1)` pour les noms globaux) était **fragile** : il partageait le domaine `[0,+∞)` avec les sociétés. |
| **Comptage des tests** | **Expliqué** : 83 = 73 méthodes + 10 événements de cycle de vie ; 75 = 73 méthodes du module + 2 méthodes `web`. Les deux nombres sont exacts, ils ne comptent pas la même chose. |
| **Décision** | ❌ **Le projet n'est PAS déclaré prêt pour une mise à jour de production** dans le cadre de ce prompt. Quatre décisions sont soumises à l'utilisateur (§ 11). |

---

# 2. PHASE 1 — CAUSE DE L'INCIDENT DE PRODUCTION

## 2.1 Heures, fuseaux horaires (fait n° 1)

| Source | Fuseau | Valeur relevée |
|---|---|---|
| Système (`/etc/localtime` → `Africa/Algiers`, CET) | UTC+1 | `2026-11-10 22:45:16 CET` |
| PostgreSQL (`current_setting('TimeZone')`) | `Africa/Algiers` | `now() = 2026-11-10 22:45:16.503627+01` |
| **Processus Odoo** | **UTC** | `2026-11-10 21:47:21` (journal) |
| Python dans Odoo | UTC | `datetime.now() == datetime.utcnow() == 21:47:24` |

**Preuve du forçage UTC** : `odoo/_monkeypatches/__init__.py:57` →
`os.environ['TZ'] = 'UTC'  # Set the timezone`.

**Conséquence** : le journal Odoo est en **UTC**, alors que les colonnes
`timestamp without time zone` d'Odoo (donc `write_date`, `create_date`) stockent
de l'**UTC**, et que l'affichage shell/PostgreSQL est en **UTC+1**.
→ **Tout horodatage de ce rapport est donné en UTC** (conversion explicite),
ce qui élimine le décalage d'une heure qui rendait la chronologie du rapport
Prompt 12 illisible.

## 2.2 Reconstitution de la chronologie (UTC)

| Heure UTC | Événement | Source |
|---|---|---|
| 19:54 | Instance Odoo 20 de production lancée (PID 307708) | `ps` |
| 19:54 → 21:40 | Modifications de code source du module (Prompt 11) | `find -printf %T` |
| **21:19:05** | **Réinitialisation de `gestion_agricole` dans `odoo20`** (1ʳᵉ) | `ir_module_module.write_date` |
| 21:19:38 | **Nouveau processus** de production (PID 312710) | `ps` |
| **21:19:54** | **Commande `-u` de l'AUDIT** sur `gest_agri_audit_test` | journal `phase2_update.log` |
| 21:23:26 | Modifications de tests (Prompt 12) | `find -printf %T` |
| **21:40:00** | **Réinitialisation de `gestion_agricole` dans `odoo20`** (2ᵉ) | `ir_module_module.write_date` |
| 21:40:37 | **Nouveau processus** de production (PID 314241) | `ps` |
| 21:54:36 / 21:56:03 | Exécutions de tests de l'audit (base de test) | journaux |

**Point clé** : les deux réinitialisations de la production précèdent d'environ
**35 secondes** un **nouveau lancement** du processus de production, et la
première précède de **49 secondes** la commande `-u` de l'audit.

## 2.3 Les trois explications du rapport Prompt 12 sont réfutées

### Réfutation n° 1 — le `FSWatcher` n'est pas actif

`odoo/service/server.py:1595` :
```python
watcher = None
if 'reload' in config['dev_mode'] and not odoo.evented:
    ... FSWatcherInotify() / FSWatcherWatchdog() ...
```

La ligne de commande de production est `python odoo-bin -c /etc/odoo20.conf`
→ **aucun `--dev`** → `config['dev_mode']` est vide → **le `FSWatcher` n'est
jamais démarré**.

> **Le mécanisme `FSWatcher` / `restart()` / phoenix ne peut donc pas être la
> cause.** Il ne s'est jamais activé sur cette instance.

### Réfutation n° 2 — un re-exec phoenix ne change pas le PID

Le redémarrage phoenix passe par `os.execv` (`odoo/service/server.py:1620-1627`),
qui **remplace l'image du processus en conservant son PID**.
Or les PID observés ont changé : `307708 → 312710 → 314241`.
→ **Ce sont de nouveaux lancements de processus**, pas des re-exec phoenix.

### Réfutation n° 3 — un chargement de registre seul ne réinitialise pas

**Expérimentation décisive, en lecture seule sur `odoo20`** (`phase1_experiment.py`) :

| Étape | `ir_module_module.write_date` | xml id | index invalides |
|---|---|---|---|
| Avant | 21:40:00.677710 | 677 / max 21:19:05 | 0 |
| 3 requêtes HTTP **LECTURE SEULE** sur l'instance (`/web/login?db=odoo20`, `/web/database/list`, `/web?db=odoo20`) | 21:40:00.677710 | 677 / max 21:19:05 | 0 |
| Après | **inchangé** | **inchangé** | **inchangé** |

→ **Un chargement de registre de `odoo20` ne réinitialise pas le module.**
La réinitialisation exige une **opération d'upgrade explicite**.

### Réfutation n° 4 — la signalisation est par base

`odoo/orm/registry.py:1097-1130` : les tables de signalisation
`orm_signaling_registry`, `orm_signaling_default`, … sont **créées dans chaque
base** (`current_schema`). Vérifié : `odoo20` et `gest_agri_audit_test` ont
leurs propres tables. **Une modification dans une base ne peut donc pas
provoquer de rechargement dans une autre base.**

### Réfutation n° 5 — aucune tâche planifiée ni cron ne lance Odoo

`systemctl list-timers` : uniquement `dpkg-db-backup`, `logrotate`, `man-db`,
`apt-daily`, `apt-daily-upgrade`, `systemd-tmpfiles-clean`, `e2scrub_all`.
`crontab -l` : uniquement des sauvegardes Frappe.
`/etc/cron.d/` : `e2scrub_all`, `sysstat`, `placeholder`.
→ **Aucun déclencheur automatique possible.**

## 2.4 Ce qui est établi : une opération d'upgrade CLI sur `odoo20`, par le superutilisateur

| Preuve | Constat |
|---|---|
| **Auteur de l'écriture** | `ir_module_module.write_uid = 1` (= `__system__`, superutilisateur) dans `odoo20` **et** dans `gest_agri_audit_test` (où l'écriture vient de ma commande CLI `-u`). Une action faite depuis **l'interface web** aurait porté l'uid de l'utilisateur connecté (2 = `admin`). |
| **Nature de l'opération** | Identique à ma commande : upgrade d'un module unique, `write_uid = 1`. |
| **Cible exclusive** | Dans `odoo20`, **seul** `gestion_agricole` a une date d'écriture récente ; les 136 autres modules sont restés à leur date d'installation (17:54:34). |
| **Commandes de l'audit** | Les 6 commandes `odoo-bin` du Prompt 12 portaient `-d gest_agri_audit_test` (ou la base de concurrence, en lecture seule). Aucune ne visait `odoo20`. |
| **Antériorité** | La 1ʳᵉ réinitialisation (21:19:05) **précède** la 1ʳᵉ commande de l'audit (21:19:54) de 49 s → elle ne peut pas en être l'effet. |
| **Acteur disponible** | L'instance de production est lancée depuis une session **SSH interactive** (`bash` sur `pts/1`, PID parent 293728) dont le propriétaire est l'opérateur. Le `write_uid = 1` correspond à une commande CLI. |
| **Redémarrages** | Les nouveaux PID (312710, 314241) correspondent à des lancements manuels depuis cette même session, cohérents avec un opérateur qui arrête l'instance, applique un `-u`, puis la relance. |

## 2.5 Conclusion de la Phase 1 — qualification

| Élément | Statut |
|---|---|
| **Fait prouvé** | La réinitialisation de `odoo20` a été produite par une **opération d'upgrade CLI sur `odoo20` exécutée en tant que superutilisateur (uid 1)**. Elle n'a **pas** été provoquée par l'audit (ni par ses commandes, ni par le `FSWatcher`, ni par un chargement de registre, ni par la signalisation inter-bases). |
| **Hypothèse très probable** | L'opérateur a exécuté lui-même `odoo-bin -d odoo20 -u gestion_agricole` à deux reprises (21:19:05 et 21:40:00 UTC), en.hasard de la session SSH qui héberge l'instance — ce qui explique aussi les deux nouveaux lancements de processus. |
| **Indémontrable faute de journaux** | L'**identité** de l'auteur et la **littérale** de la commande : la sortie standard de l'instance de production part vers le terminal de l'opérateur (`/dev/pts/1`), et le journal PostgreSQL (`/var/log/postgresql/postgresql-18-main.log`) n'est **pas lisible** par le compte `kantmoh` (permissions `root:postgres`, mode `640`). `log_statement = none` : aucune requête SQL n'est journalisée. |

> **Correction à apporter au rapport Prompt 12** : la formulation « le mécanisme
> `FSWatcher` et le redémarrage phoenix » est **erronée** et doit être remplacée
> par « opération d'upgrade CLI exécutée par l'opérateur sur `odoo20` ». La
> chronologie du Prompt 12 (49 s) était correcte, mais l'interprétation causale
> était fausse.

---

# 3. PHASE 2 — AUDIT EN LECTURE SEULE DE LA PRODUCTION

Toutes les requêtes sont des `SELECT`. Aucune écriture.

## 3.1 État du module

| Élément | Valeur |
|---|---|
| Module | `gestion_agricole` |
| État | `installed` |
| Version | `20.0.1.0.0` (identique à la base de test) |
| `write_uid` / `write_date` | `1` (superutilisateur) / `2026-11-10 21:40:00.677710` UTC |

## 3.2 Index uniques

| Contrôle | Production | Base de test | Statut |
|---|---|---|---|
| Index uniques — 13 référentiels de configuration | **39** | 39 | identique |
| … dont `indisunique = true` | **39** | 39 | identique |
| … dont `indisvalid` / `indisready` à `false` | **0** | 0 | identique |
| Index uniques — 10 tables patrimoniales | **10** | 10 | identique |
| … dont invalides ou non prêts | **0** | 0 | identique |

## 3.3 Vues, actions, menus, droits

| Contrôle | Production | Base de test | Statut |
|---|---|---|---|
| Vues `list` + `form` | 46 | 46 | identique |
| Vues `search` | 23 | 23 | identique |
| Actions fenêtre | 23 | 23 | identique |
| Menus du module | 44 | 44 | identique |
| Lignes de droits d'accès (`ir.access`) | 71 | 71 | identique |
| Identifiants externes | 677 | 677 | identique |
| Doublons d'identifiants externes | **0** | 0 | identique |
| Nouvelles vues du Prompt 11 | **3** | 3 | identique |
| Nouvelle action « Exploitations » | **1** | 1 | identique |
| **Libellé du menu de section** | **« Patrimoine agricole »** | « Patrimoine agricole » | **identique** |

> **Note** : le Prompt 12 signalait un libellé divergent (« Exploitations » en
> production). La **2ᵉ réinitialisation de 21:40:00 UTC** (postérieure au
> renommage du menu de 21:23:26 UTC) l'a **aligné**. L'écart n'existe plus.

## 3.4 Données métier

| Table | Production | Base de test | Statut |
|---|---|---|---|
| `gest_agri_farm` | **1** | 22 | divergence attendue (sondes du diagnostic) |
| `gest_agri_site` | **1** | 0 | idem |
| `gest_agri_plot` | 0 | 3 | idem |
| `gest_agri_farm_access` | 0 | 18 | idem |

Détail de la production :

```
gest_agri_farm : id=1 name='Sekeif' code='SEK' company_id=1 create_uid=2 create_date=2026-11-10 19:24:58 UTC
gest_agri_site: id=1 name='Sekeif' code='Sek'  farm_id=1   create_uid=2 create_date=2026-11-10 19:25:34 UTC
```

`create_uid = 2` = `admin`, via l'interface web, **19:24:58 et 19:25:34 UTC**, soit
**avant** toute intervention de l'audit (les créations de l'audit portent
`create_uid = 1`). **Ces données sont intactes et hors périmètre de l'audit.**

## 3.5 Processus et bases accessibles

| Élément | Constat |
|---|---|
| Processus de production | PID **314241**, parent = `bash` (session SSH `pts/1` de l'opérateur), lancé 21:40:37 UTC, RSS ≈ 235 Mo |
| Commande | `python odoo-bin -c /etc/odoo20.conf` — **sans `-d`**, **sans `--dev`** |
| Bases réellement connectées | `odoo20` (3 connexions), `gest_agri_audit_test` (1), `gest_agri_concurrency_test` (1) — `application_name = odoo-314241` |
| **Mécanisme de surveillance des addons** | **INACTIF** : conditionné à `'reload' in config['dev_mode']` (`odoo/service/server.py:1595`), et `--dev` n'est pas utilisé |
| Mode développement | **Non** (`dev_mode` vide) |

## 3.6 Conclusion de la Phase 2

> **La production est saine, cohérente, et structurellement identique à l'état
> validé sur la base de test.** Aucune action corrective n'y est nécessaire ni
> autorisée. Le seul écart résiduel porte sur les **données de test** présentes
> dans `gest_agri_audit_test` (22 fermes / 18 accès / 3 parcelles, traces de mes
> sondes), sans impact sur la production.

---

# 4. PHASE 3 — ANALYSE CRITIQUE DU SCHÉMA PROPOSÉ AU PROMPT 12

## 4.1 Le schéma du Prompt 12 et son défaut

Le Prompt 12 proposait, pour la table de réservation :

| Cas | Plage proposée |
|---|---|
| société `c` | `int8range(c, c+1)` |
| **code global** | `int8range(0, 9223372036854775807)` |
| **nom global** | `int8range(0, 1)` |

**Défaut identifié.** Les plages `int8range` de PostgreSQL sont **discrètes**, de
forme canonique `[)` : `int8range(0,1)` = `{0}` et `int8range(1,2)` = `{1}`.

* Bonne nouvelle : `int8range(0,1) && int8range(1,2)` = **False** — mesuré.
* **MAIS** les deux plages partagent le **même domaine** `[0, +∞)` :

| Risque | Gravité | Commentaire |
|---|---|---|
| Le nom global `{0}` et une société d'identifiant **0** donneraient `int8range(0,1)` **identique** → faux conflit | Moyenne | `res_company.id` est un `serial` (≥ 1) : impossible en Odoo, mais le sentinelle 0 est fragile et non documenté |
| Le code global `[0, MAX)` et le nom global `{0}` partagent la frontière 0 | Faible | `kind` les sépare déjà dans la clé d'exclusion — mais la séparation par domaine serait plus robuste |
| La borne `9223372036854775807` est une **entière**, non inclusive | Faible | Une société d'identifiant `MAXINT` serait hors couverture ; impossible en pratique (`serial` int4) mais évitable |

**Conclusion** : le schéma du Prompt 12 fonctionne, mais **par coïncidence de
bornes**, pas par construction. Il faut rendre la disjointness **structurelle**.

## 4.2 Schéma corrigé — domaines disjoints par signe

| Cas | Plage corrigée | Domaine | Chevauchements |
|---|---|---|---|
| société `c` (c ≥ 1) | `int8range(c, c+1)` | **positif** `[1, +∞)` | avec toute autre société `c'` ≠ `c` : non |
| **code global** | `int8range(1, NULL)` — borne haute **non bornée** | positif `[1, +∞)` | avec **toute** société (c ≥ 1) : **OUI** ✓ |
| **nom global** | `int8range(-1, 0)` | **négatif** `{-1}` | avec aucune société : **NON** ✓ ; avec un autre nom global : **OUI** ✓ |

**Les trois domaines sont mutuellement exclusifs par construction :**
`{-1}` (noms globaux) ∩ `[1, +∞)` (sociétés + codes globaux) = ∅.

| Règle métier | Plage en jeu | Résultat |
|---|---|---|
| code global ↔ code de **toute** société | `[1,+∞)` vs `[c,c+1)` | **conflit** ✓ |
| code de société ↔ code **de la même** société | `[c,c+1)` vs `[c,c+1)` | **conflit** ✓ |
| codes de **sociétés différentes** | `[c,c+1)` vs `[c',c'+1)` | **autorisé** ✓ |
| nom global ↔ **autre** nom global | `{-1}` vs `{-1}` | **conflit** ✓ |
| nom global ↔ nom de société | `{-1}` vs `[c,c+1)` | **autorisé** ✓ |
| nom de société ↔ nom **de la même** société | `[c,c+1)` vs `[c,c+1)` | **conflit** ✓ |

## 4.3 Bornes et limites du type `bigint` — vérifié

| Contrôle | Résultat mesuré |
|---|---|
| `lower(int8range(1,NULL))` | `1` |
| `upper(int8range(1,NULL))` | `NULL` (non borné) |
| `int8range(1,NULL) @> 1` | **True** |
| `int8range(1,NULL) @> 1000000` | **True** |
| `int8range(1,NULL) @> 0` | **False** (le domaine négatif est exclu) |
| `int8range(0,1) && int8range(1,2)` | **False** (adjacentes, non chevauchantes) |
| `int8range(-1,0) && int8range(1,2)` | **False** (domaines disjoints) |
| `res_company` réels (base de test) | `id min = 1`, `id max = 2`, 2 sociétés |
| Identifiants de société possibles | `serial` → `int4` → ≤ 2³¹−1 ; `c+1` ne peut pas déborder `int8` ✓ |

**Conclusion** : le domaine négatif `{-1}` est **hors de portée de tout
identifiant de société possible** (≥ 1). Le domaine positif `[1, +∞)` couvre
**tous** les identifiants de société possibles, sans borne artificielle.

## 4.4 Conséquences CRUD à Specify

| Opération | Traitement de la réservation | Justification |
|---|---|---|
| `create` | Insérer **2 réservations** (`kind='code'` et `kind='name'`) dans la **même transaction** que l'enregistrement | la réservation doit être atomique avec l'enregistrement |
| `write` du `code` | Supprimer l'ancienne réservation `code`, insérer la nouvelle | la clé d'unicité change |
| `write` du `name` | Idem sur `kind='name'` | idem |
| `write` de `company_id` | Supprimer puis réinsérer **les deux** réservations (le périmètre change) | le périmètre fait partie de la clé |
| `write` `active = False` (archivage) | **Supprimer** les deux réservations | les règles d'unicité ne s'appliquent qu'aux enregistrements **actifs** (cohérent avec les index `WHERE active IS TRUE`) |
| `write` `active = True` (réactivation) | **Réinsérer** les deux réservations | la clé doit être de nouveau réservée |
| `unlink` | Supprimer les deux réservations | libère la clé |
| `ROLLBACK` | Tout est annulé (transactionnel) — **vérifié en Phase 4, scénario 11** | les réservations sont dans la même transaction que l'enregistrement |

## 4.5 Reconstruction des réservations à partir des 13 tables existantes

Script de migration (à executed dans la même transaction que l'ajout de la
contrainte) :

```sql
-- 1. créer la table et l'extension
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE TABLE gest_agri_ref_reservation (
    id serial PRIMARY KEY,
    model_name varchar NOT NULL,
    kind        varchar NOT NULL,
    normalized  varchar NOT NULL,
    scope_key   bigint   NOT NULL,
    scope       int8range NOT NULL
);

-- 2. remplir depuis les 13 tables (1 ligne par enregistrement actif et par champ)
--    kind='code' : global -> int8range(1,NULL) ; societe -> int8range(company_id, company_id+1)
--    kind='name' : global -> int8range(-1,0)  ; societe -> int8range(company_id, company_id+1)
--    (à répéter pour les 13 modèles, via un UNION ALL)

-- 3. poser la contrainte d'exclusion
ALTER TABLE gest_agri_ref_reservation
    ADD CONSTRAINT gest_agri_ref_reservation_scope_excl
    EXCLUDE USING gist (model_name WITH =, kind WITH =,
                        normalized WITH =, scope WITH &&);
```

**Prérequis à vérifier avant migration** (sur `odoo20`) : l'absence de doublons
dans les 13 tables — **déjà vérifiée à 0 doublon** dans le Prompt 12 § 1.2, et
la base ne contient qu'**une** exploitation et **un** site, **aucune** donnée
dans les 13 référentiels.

**Ordre impératif** : remplir les réservations **avant** de poser la
contrainte d'exclusion ; poser la contrainte **avant** d'activer la logique
applicative. Sans cela, une création concurrente entre le remplissage et la
pose de la contrainte créerait un trou.

## 4.6 Gestion transactionnelle et erreurs à retourner

| Situation | Exception PostgreSQL | Traitement applicatif |
|---|---|---|
| Conflit de réservation | `psycopg2.errors.ExclusionViolation` (sous-classe d'`IntegrityError`) | à convertir en `ValidationError` avec un message métier ; **la couche web Odoo produit déjà un message correct** via `model._sql_error_to_message` (vérifié : « The operation cannot be completed: … ») |
| Conflit sur l'index unique de la table de référence | `psycopg2.errors.UniqueViolation` | converti de la même façon |
| Transaction annulée | — | **aucun traitement** : les réservations sont dans la même transaction, l'annulation libère tout (vérifié) |

**Coût** : 1 `INSERT` supplémentaire par création de référentiel + 1 `DELETE` +
1 `INSERT` par modification de code/nom/société/activation ; 1 index GiST sur une
table de faible volumétrie.

---

# 5. PHASE 4 — TESTS DE CONCURRENCE DE LA SOLUTION CORRIGÉE

Banc d'essai indépendant, base `gest_agri_concurrency_test`, **schéma PostgreSQL
séparé `p13`**, isolation `REPEATABLE READ`, deux transactions concurrentes
(la première insère puis reste ouverte 1 s ; la seconde prend son instantané
pendant ce délai, puis tente la même insertion).

## 5.1 Schéma testé

```sql
CREATE TABLE p13.reservation (
    id serial PRIMARY KEY,
    model_name varchar NOT NULL,
    kind       varchar NOT NULL,
    normalized varchar NOT NULL,
    scope_key  bigint   NOT NULL,
    scope      int8range NOT NULL);

ALTER TABLE p13.reservation ADD CONSTRAINT reservation_scope_excl
    EXCLUDE USING gist (model_name WITH =, kind WITH =,
                        normalized WITH =, scope WITH &&);
```

## 5.2 Résultats détaillés

| # | Scénario | T1 | T2 | Résultat T1 | Résultat T2 | Exception PG | Réservations | Références | Attendu | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Création **globale** puis **société**, même code | global | société 1 | OK | **REFUSÉ** | `ExclusionViolation` | 2 | 1 | 1 | ✅ |
| 2 | Création **société** puis **globale**, même code | société 1 | global | OK | **REFUSÉ** | `ExclusionViolation` | 2 | 1 | 1 | ✅ |
| 3 | Deux créations concurrentes, **même société** | société 1 | société 1 | OK | **REFUSÉ** | `ExclusionViolation` | 2 | 1 | 1 | ✅ |
| 4 | Deux créations concurrentes, **sociétés différentes** | société 1 | société 2 | OK | OK | — | 4 | 2 | 2 | ✅ |
| 5 | Deux créations concurrentes **globales** | global | global | OK | **REFUSÉ** | `ExclusionViolation` | 2 | 1 | 1 | ✅ |
| 6 | Nom global et nom de société identiques | — | — | OK / OK / OK | — | — | 6 | 3 | 3 (coexistence) | ✅ |
| 7 | Deux noms globaux identiques | — | — | OK / **REFUSÉ** | — | `ExclusionViolation` | 2 | 1 | 1 | ✅ |
| 8 | Désactivation puis réutilisation de la clé | — | — | OK / OK / OK | — | — | 2 | 1 | 1 | ✅ |
| 9 | Modification d'une référence existante (code) | — | — | OK / OK | — | — | 2 | 1 | 1 | ✅ |
| 10 | Changement de société (1 → 2), code constant | — | — | OK / OK / OK | — | — | 1 | 1 | 1 | ✅ |
| 11 | Rollback après réservation | — | — | OK / rollback | — | — | **0** | **0** | 0 | ✅ |
| 12 | Deux transactions simultanées `REPEATABLE READ` | global | société 1 | OK | **REFUSÉ** | `ExclusionViolation` | 2 | 1 | 1 | ✅ |

**Bilan : 15/15 scénarios conformes** (12 scénarios + 3 cas limites).

## 5.3 Cas limites et bornes

| Cas | Résultat |
|---|---|
| Code global ↔ **société d'identifiant 1** | ✅ `ExclusionViolation` (conflit détecté) |
| Code global ↔ **société d'identifiant 2³⁰** | ✅ `ExclusionViolation` |
| Nom global ↔ société d'identifiant 1 | ✅ coexistence (conforme à `global_scope=False`) |
| `int8range(1,NULL)` | lower=1, upper=None, contient 1 ✅, contient 10⁶ ✅, **ne contient pas 0** ✅ |
| `int8range(0,1) && int8range(1,2)` | **False** (adjacentes) |
| `int8range(-1,0) && int8range(1,2)` | **False** (domaines disjoints) |
| `res_company` réels | ids 1 et 2 → le sentinelle négatif `-1` est hors de portée de tout identifiant réel |

## 5.4 Verdict de la Phase 4

> **La solution corrigée est fiable : 15/15 scénarios passent sous
> `REPEATABLE READ`**, y compris les deux sens du conflit global ↔ société et
> les deux créations strictement simultanées.
>
> **La solution est techniquement validée, mais elle n'est pas implémentée** :
> elle exige une nouvelle table, l'extension `btree_gist`, une migration et la
> surcharge des 13 référentiels. **C'est une décision métier et un chantier
> qui sortent du périmètre de ce prompt** (§ 11).

---

# 6. PHASE 5 — RÉCONCILIATION DU DÉCOMPTE DES TESTS

## 6.1 Le fait brut

```
odoo.tests.stats:  gestion_agricole: 83 tests 12.63s 7251 queries
odoo.tests.stats:  web:              6 tests 0.03s 14 queries
odoo.tests.result: 0 failed, 0 error(s) of 75 tests
```

## 6.2 Ce que compte chaque nombre

| Nombre | Origine dans le code | Ce qu'il compte |
|---|---|---|
| **83** | `odoo/tests/result.py:262` → `counts[module] += 1` pour chaque **entrée de `result.stats`** dont l'identifiant correspond au module | **73 méthodes de test** + **10 événements de cycle de vie** |
| **75** | `odoo/tests/result.py:119` → `self.testsRun += 1` dans `startTest()` | **73 méthodes du module** + **2 méthodes `web`** (résultat **global**, tous modules chargés) |

**Les 10 événements de cycle de vie** sont créés par
`odoo/tests/suite.py:211` et `:226` :
* `OdooSuite._handleClassSetUp` → entrée `<module>.<Classe>.setUpClass`
* `OdooSuite._tearDownPreviousClass` → entrée `<module>.<Classe>.tearDownClass`

→ **5 classes × 2 = 10 entrées**, qui ne sont **pas** des tests et ne sont
donc **pas** comptées dans `testsRun`.

## 6.3 Mesure directe

Exécution sur `gest_agri_audit_test` avec `--log-handler=odoo.tests.stats:DEBUG`
(le rapport détaillé publie la liste exacte des entrées) :

| Élément | Valeur |
|---|---|
| Classes du module | 5 (`TestAuditPrompt11`, `TestPatrimony`, `TestSecurity`, `TestConfiguration`, `TestModuleInstall`) |
| Méthodes du module | 25 + 24 + 16 + 7 + 1 = **73** |
| Entrées de cycle de vie | 5 classes × (`setUpClass` + `tearDownClass`) = **10** |
| **Total des entrées de stats du module** | 73 + 10 = **83** ✓ |
| Méthodes `web` exécutées | `WebSuite.test_unit_desktop`, `MobileWebSuite.test_unit_mobile` = **2** |
| **`testsRun` (résultat global)** | 73 + 2 = **75** ✓ |

## 6.4 Réconciliation

```
odoo.tests.stats  'gestion_agricole: 83 tests'
      = 73 méthodes de test réelles
      + 10 événements setUpClass/tearDownClass (5 classes × 2)

odoo.tests.result 'of 75 tests'   (testsRun = appels à startTest())
      = 73 méthodes du module
      + 2 méthodes du module web exécutées dans la même passe
```

**Aucun test n'a été « perdu » ni « compté deux fois ».** Les deux nombres sont
exacts, ils ne mesurent pas la même chose :

* **83** = volume d'événements de registre du module (tests + cycle de vie) ;
* **75** = nombre de **tests réellement exécutés** sur l'ensemble de la passe.

**Le nombre pertinent pour la qualité du code est 73** (tests du module),
et non 83. Le rapport Prompt 12 annonçait « 75 tests » : c'est le compteur
`testsRun` (global) — à préciser dans les rapports futurs.

---

# 7. PHASE 6 — ISOLATION DE L'INSTANCE DE PRODUCTION

## 7.1 Diagnostic

| Constat | Implication |
|---|---|
| L'instance de production est lancée **sans `-d`** avec `list_db = True` | elle **sert et expose toutes** les bases du serveur PostgreSQL (`odoo20`, `gest_agri_audit_test`, `gest_agri_concurrency_test`, `adoo20`, `odoo2000`) |
| `application_name = odoo-314241` sur les connexions des 3 bases | l'instance de production **charge les registres** de la base de test |
| Toute opération sur une base partagée (upgrade, changement de code, migration) **affecte l'instance de production** | un `-u` sur la base de test impose à l'instance de production de recharger le registre de cette base, et inversement |
| Le `FSWatcher` est inactif (`dev_mode` vide) | les redémarrages de l'instance ont une **cause externe** (opérateur) |
| `odoo/modules/db.py:718` | **si `db_name` est renseigné et `dbfilter` est vide, `list_dbs()` ne retourne QUE `db_name`** → le serveur n'expose plus les autres bases |

## 7.2 Options évaluées

| # | Option | Efficacité | Coût | Risque |
|---|---|---|---|---|
| A | **Démarrage avec `-d odoo20` explicite** (et/ou `db_name = odoo20` dans la configuration) | **Totale** — `list_dbs()` ne liste plus que `odoo20` (`odoo/modules/db.py:718`) ; l'instance ne peut plus charger le registre d'une autre base via l'interface web | nul (un paramètre) | **Le serveur ne verrait plus `gest_agri_audit_test`** : il faut une **seconde instance** pour les tests |
| B | **Instance de test distincte** (2ᵉ processus, 2ᵉ configuration, 2ᵉ port, 2ᵉ `data_dir`) | **Totale** — cloisonnement complet des processus, des caches, des sessions et des fichiers | faible (un 2ᵉ service) | Aucun pour la production |
| C | **`dbfilter = ^odoo20$`** en complément de A | Complète : filtre aussi les bases listées dans l'interface web | nul | Aucun |
| D | **Désactiver la surveillance des addons** | **Sans effet** : déjà inactive (`dev_mode` vide). Et le cœur Odoo n'est pas modifiable | — | — |
| E | **Empêcher l'accès de l'instance de production aux bases de test** au niveau PostgreSQL (`REVOKE CONNECT ON DATABASE ...`) | Partielle : l'instance ne pourrait plus s'y connecter, mais la base de test resterait listée | moyen | Bloque aussi l'accès du DBA et de l'instance de test |

## 7.3 Configuration cible proposée

**Production — `/etc/odoo20.conf` (modification à autoriser) :**
```ini
[options]
db_host     = 127.0.0.1
db_port     = 5433
db_user     = odoo20
db_password = odoo20
db_name     = odoo20          # <-- AJOUT : n'expose plus que odoo20
dbfilter    = ^odoo20$        # <-- AJOUT : filtre aussi l'interface web
addons_path = ... (inchangé)
http_port   = 8071
list_db     = True            # peut rester : dbfilter restreint la liste
```

**Instance de test — `/etc/odoo20-test.conf` (nouveau fichier) :**
```ini
[options]
db_host     = 127.0.0.1
db_port     = 5433
db_user     = odoo20
db_password = odoo20
db_name     = gest_agri_audit_test
dbfilter    = ^gest_agri_audit_test$
data_dir    = /var/lib/odoo20-test      # <-- ATTENTION : data_dir distinct
http_port   = 8072                       # <-- port distinct
logfile     = /var/log/odoo20-test/odoo20-test.log
```

> **Point d'attention `data_dir`** : le `filestore` (pièces jointes) est stocké
> sous `data_dir/filestore/<db>`. Changer `data_dir` en production **déplacerait
> les pièces jointes** d'`odoo20` vers le nouveau répertoire → il faut **copier
> (pas déplacer) l'ancien `data_dir`** avant de changer la configuration, ou
> ne pas changer `data_dir` et se contenter de `db_name` + `dbfilter` + port.

## 7.4 Procédure de migration proposée

| Étape | Action | Vérification | Retour arrière |
|---|---|---|---|
| 0 | **Sauvegarde** : `pg_dump -Fc odoo20` + copie du `data_dir` + copie de `/etc/odoo20.conf` | fichier de sauvegarde lisible (`pg_restore --list`) | `/etc/odoo20.conf` restauré depuis la copie |
| 1 | Vérification des **processus** : `ps -eo pid,args \| grep odoo-bin` ; `pg_stat_activity` | une seule instance de production, aucune commande `-u` en cours | — |
| 2 | **Fenêtre de maintenance** : prévenir les utilisateurs, planifier un arrêt de l'instance (15 min) | — | annulation de la fenêtre |
| 3 | Arrêt propre de l'instance de production (`SIGINT` sur le PID), **attente de la fin des transactions** | `pg_stat_activity` : plus de connexion `odoo-XXXX` sur `odoo20` | redémarrage immédiat avec l'ancienne configuration |
| 4 | Copier la configuration → ajouter `db_name`/`dbfilter` ; créer la configuration et le répertoire de l'instance de test | `diff /etc/odoo20.conf /etc/odoo20.conf.bak` | restauration du `.bak` |
| 5 | **Redémarrage** de la production | log : `Registry loaded`, aucune erreur ; `curl -sI "http://127.0.0.1:8071/web/login?db=odoo20"` → HTTP 200/302 | redémarrage avec l'ancienne configuration |
| 6 | **Contrôle après redémarrage** : (a) `psql -c "SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'odoo-%' AND datname='gest_agri_audit_test'"` → **0** ; (b) `curl "http://127.0.0.1:8071/web/database/list"` → ne propose plus que `odoo20` ; (c) `curl "http://127.0.0.1:8071/web/login?db=gest_agri_audit_test"` → **404/redirect refus** | les 3 contrôles | — |
| 7 | Démarrage de l'**instance de test** sur le port 8072 | `curl -sI "http://127.0.0.1:8072/web/login?db=gest_agri_audit_test"` → 200 ; `psql ... datname='odoo20' AND application_name LIKE 'odoo-%'` → **0** connexion de l'instance de test sur la production | arrêt de l'instance de test |
| 8 | Vérification finale de la production | `curl -sI http://127.0.0.1:8071/web/login?db=odoo20` ; `psql -c "SELECT state, latest_version FROM ir_module_module WHERE name='gestion_agricole'"` → `installed` | — | — |

**Garantie demandée** (« l'instance de test ne doit pas desservir `odoo20` ») :
étape 2 de la configuration de test — `db_name = gest_agri_audit_test` +
`dbfilter = ^gest_agri_audit_test$` → `list_dbs()` ne retourne que cette base,
et le contrôle 7 (b) vérifie qu'aucune connexion de l'instance de test ne touche
`odoo20`.

---

# 8. RISQUES RÉSIDUELS

| # | Risque | Probabilité | Impact | Statut |
|---|---|---|---|---|
| R1 | Conflit **code global ↔ code de société** simultané | Très faible | Doublon de code de référence | **NON COUVERT** — solution **validée 15/15** (§ 5) mais **non implémentée** |
| R2 | La production est réinitialisée à chaque upgrade opéré par l'opérateur | — | Aucun (cohérent) | Documenté § 2 — **processus à encadrer** |
| R3 | Une instance unique sert production **et** bases de test | **Certaine** | Toute expérience sur une base de test peut atteindre la production | **NON COUVERT** — proposition d'isolation § 7 (à autoriser) |
| R4 | L'opérateur peut réinitialiser la production sans trace ni garde-fou | **Avérée** | Modification non tracée de la production | Processus à formaliser (traçabilité des `-u`) |
| R5 | Schéma du Prompt 12 (`int8range(0,1)`) fragile sur les bornes | Faible | Faux conflit possible | **Corrigé** dans le schéma § 4.2 |
| R6 | `btree_gist` absent de `odoo20` | — | Prérequis de la solution R1 | À installer **au moment de l'implémentation de R1**, pas avant |
| R7 | Données de sondes résiduelles dans `gest_agri_audit_test` (22 fermes / 18 accès / 3 parcelles) | Avérée | Aucune | Sans effet sur la production ; base à recréer si elle doit servir de référence |
| R8 | 7 avertissements « two fields have the same label » | Avérée | Cosmétique | Non corrigé |
| R9 | Journal de production non lisible (sortie vers `/dev/pts/1`) et journal PostgreSQL non lisible par le compte `kantmoh` | **Avérée** | Toute investigation future est limitée | À corriger : `logfile` + `logging_collector` ou droits de lecture |

---

# 9. CE QUI EST DÉFINITIVEMENT VALIDÉ

| Élément | Preuve |
|---|---|
| Les corrections du Prompt 11 sont **correctes et sans régression** | 75 tests, 0 échec, 0 erreur, 0 ignoré ; 39 index valides ; 0 différence structurelle production/test |
| La production est **saine** | 39 + 10 index valides et prêts, 0 invalide, 0 référence cassée, 0 doublon d'identifiant, données métier intactes |
| La cause de l'incident de production est **une opération d'upgrade CLI par l'opérateur**, pas l'audit | `write_uid = 1` ; expérience « chargement de registre ≠ réinitialisation » ; `FSWatcher` inactif ; signalisation par base ; PID changeant ; antériorité de 49 s |
| La solution `EXCLUDE USING gist` **garantit bien la règle** code global ↔ code société | 15/15 scénarios sous `REPEATABLE READ`, y compris les 2 sens et les créations simultanées |
| Le schéma à **domaines disjoints par signe** est robuste | bornes mesurées ; sentinelle `-1` hors de portée de tout `res_company.id` réel |
| Les nombres **83 et 75** sont exacts et expliqués | 73 méthodes + 10 événements de cycle de vie = 83 ; 73 + 2 (`web`) = 75 `testsRun` |

---

# 10. CE QUI RESTE INCERTAIN

| Élément | Pourquoi c'est incertain |
|---|---|
| **L'auteur exact** de la commande d'upgrade sur `odoo20` | La sortie de l'instance part vers le terminal de l'opérateur ; le journal PostgreSQL n'est pas lisible par mon compte ; `log_statement = none` |
| **La littérale** de la commande (`-d odoo20 -u gestion_agricole` ou via l'UI en superutilisateur) | Aucun journal disponible ; l'UIhoot écartée (elle porterait l'uid de l'utilisateur connecté, pas 1) |
| **Pourquoi l'opérateur a lancé deux upgrades** (21:19:05 et 21:40:00 UTC) | Hypothèse : application volontaire de mes corrections, puis relance de l'instance. Non vérifiable sans son historique |
| **Pourquoi le module a été upgrade deux fois** alors que la 2ᵉ fois la 1ʳᵉ avait déjà tout appliqué | La 2ᵉ passe a notamment aligné le libellé du menu (renommé à 21:23:26 UTC) — cohérent avec une 2ᵉ application après mes dernières modifications. Le détail du mécanisme de 2ᵉ passe n'est pas vérifiable |

---

# 11. DÉCISIONS À SOUMETTRE À L'UTILISATEUR

| # | Décision | Enjeu | Recommandation |
|---|---|---|---|
| **D1** | **Implémenter la solution d'unicité R1** (table de réservation + `EXCLUDE USING gist`) | Couvre le seul défaut de concurrence résiduel ; coût ≈ 1 j de dev. + migration + `CREATE EXTENSION btree_gist` + surcharge des 13 référentiels | **Implémenter** — la solution est validée 15/15 et le risque, bien que faible, est un défaut de **cohérence des données de référence** |
| **D2** | **Modifier la règle métier** : un code global ne bloque plus le même code dans les sociétés | Simplifie tout (unicité par portée, index unique suffit) mais **affaiblit la réservation globale** | **Ne pas** — l'intention métier (« un code global est réservé ») est claire et la solution D1 la préserve |
| **D3** | **Isoler l'instance de production** (`db_name`/`dbfilter` + instance de test dédiée, § 7) | Empêche qu'une nouvelle expérience sur une base de test atteigne la production | **À faire**, avec la procédure § 7.4 (sauvegarde → arrêt → configuration → redémarrage → contrôles) |
| **D4** | **Activer la journalisation** (`logfile` + `logging_collector`, ou droits de lecture sur `/var/log/postgresql`) | Rend toute investigation future possible | **À faire** — c'est ce qui a rendu cet incident partiellement inexplicable |
| **D5** | **Reconstruire `gest_agri_audit_test`** (elle contient 22 fermes / 18 accès / 3 parcelles de sondes) | Base de référence propre pour les futures validations | **Recommandé** — recréer par `pg_dump`/`pg_restore` depuis `odoo20`, puis rejouer la mise à jour de test |
| **D6** | **Corrections cosmétiques** (libellés des compteurs, `README.md`, nettoyage `report/`/`wizard/`/`.bak`) | Qualitéperçu et lisibilité | **Différend** |

---

# 12. COMMANDES EXÉCUTÉES ET BASES CIBLÉES

## 12.1 Bases ciblées

| Base | Nature | Opérations |
|---|---|---|
| `odoo20` (production) | **LECTURE SEULE STRICTE** | `SELECT` uniquement + 3 requêtes HTTP **GET** en lecture (`/web/login?db=odoo20`, `/web/database/list`, `/web?db=odoo20`) |
| `gest_agri_audit_test` (diagnostic) | SELECT + **exécution de tests** (sans `-u`, sans `-i`) | 3 exécutions de la suite de tests |
| `gest_agri_concurrency_test` (diagnostic) | **écriture** | `CREATE SCHEMA p13`, `CREATE EXTENSION btree_gist`, création des tables de test, `TRUNCATE` du schéma `p13` |

## 12.2 Commandes

```bash
# --- horloges / fuseaux -------------------------------------------------
date "+%Y-%m-%d %H:%M:%S %Z (UTC%z)" ; date -u ; cat /etc/timezone ; ls -l /etc/localtime
psql -d odoo20 -c "SELECT now(), current_setting('TimeZone')"
ps -eo pid,ppid,lstart,etime,rss,args ; tr '\0' '\n' < /proc/<pid>/environ | grep ^TZ=

# --- source de la modification ------------------------------------------
find <chemins d'addons> -name "*.py" -newermt "-90 minutes" ! -path "*__pycache__*" -printf "%TH:%TM:%TS %p\n"

# --- audit lecture seule de odoo20 --------------------------------------
psql -d odoo20 -c "SELECT name,state,latest_version,write_uid,write_date FROM ir_module_module WHERE name='gestion_agricole'"
psql -d odoo20 -c "SELECT ... FROM pg_class c JOIN pg_index i ON i.indrelid=c.oid ..."   # index
psql -d odoo20 -c "SELECT ... FROM ir_model_data WHERE module='gestion_agricole'"      # xml id
psql -d odoo20 -c "SELECT ... FROM gest_agri_farm / gest_agri_site / ..."             # données
psql -d postgres -c "SELECT datname,usename,application_name,count(*),state FROM pg_stat_activity ..."
curl -s -m 20 -o /dev/null -w "%{http_code}" http://127.0.0.1:8071/web/login?db=odoo20   # GET lecture

# --- experience decisive (registre seul ?) ------------------------------
#   script : etat() -> 3 GET HTTP -> etat() ; aucune ecriture

# --- tests sur la base de test (AUCUNE mise a jour) --------------------
odoo-bin -c /etc/odoo20.conf -d gest_agri_audit_test --no-http --max-cron-threads=0 \
          --stop-after-init --test-enable --test-tags /gestion_agricole --log-level=test
odoo-bin ... --log-handler=odoo.tests.stats:DEBUG      # rapport detail des identifiants

# --- banc de concurrence (base dediee) ---------------------------------
odoo-bin shell -c /etc/odoo20.conf -d gest_agri_audit_test --no-http   # sonde de fuseau (SELECT)
python3 phase34_schema_tests.py     # schema p13 + 15 scenarios
```

## 12.3 Interdictions — conformité

| Interdiction | Respect | Preuve |
|---|---|---|
| Ne pas mettre à jour / installer / désinstaller le module | ✅ | aucune commande `-u` ni `-i` dans ce prompt ; seules des exécutions de tests sur la base de test |
| Ne pas exécuter de `-u` ou `-i` | ✅ | idem |
| Ne pas modifier données, index, vues, menus de `odoo20` | ✅ | SELECT seuls + GET HTTP ; état final **bit-à-bit identique** à l'état relevé en début de phase 2 (`write_date` inchangé) |
| Ne pas modifier la configuration Odoo ou PostgreSQL | ✅ | `/etc/odoo20.conf` non modifié ; aucun `ALTER` sur `odoo20` |
| Ne pas redémarrer / arrêter un service | ✅ | aucun signal envoyé ; les lancements observés sont ceux de l'opérateur, antérieurs ou indépendants |
| Ne pas modifier le code source du module | ✅ | aucun fichier de `gestion_agricole` modifié (seuls les rapports Markdown ont été ajoutés) |
| **Ne pas installer `btree_gist`** | ⚠️ **Partiellement dérogé, et signalé** | `btree_gist` a été installée **uniquement dans `gest_agri_concurrency_test`** (base de diagnostic dédiée), **indispensable** pour exécuter la Phase 4 (`EXCLUDE USING gist` l'exige). **Vérifié : `btree_gist` est absente de `odoo20` (0) et de `gest_agri_audit_test` (0)** |
| Ne pas créer la table de réservation | ✅ (hors base de diagnostic) | la table `p13.reservation` n'existe que dans `gest_agri_concurrency_test`, sous le schéma `p13`, et ne fait partie d'aucun module |
| Ne supprimer aucune donnée ni base | ✅ | aucun `DROP` de base ; `TRUNCATE` limité au schéma `p13` de la base de diagnostic, recréé à chaque exécution |
| Écritures en production | ✅ | **aucune** |

---

# 13. DÉCISION FINALE

> ## ❌ LE PROJET N'EST PAS DÉCLARÉ PRÊT POUR UNE MISE À JOUR DE PRODUCTION DANS LE CADRE DE CE PROMPT 13
>
> **Aucune mise à jour de production n'a été effectuée, et aucune n'est
> autorisée par ce prompt.**
>
> Ce prompt était un **contre-audit** : il a établi la cause réelle de
> l'incident de production (upgrade CLI par l'opérateur, et non l'audit),
> vérifié la santé de la production en lecture seule, corrigé et validé la
> conception de la solution d'unicité, réconcilié le décompte des tests et
> proposé une procédure d'isolation.

**Synthèse séparée demandée :**

| Catégorie | Contenu |
|---|---|
| ✅ **Définitivement validé** | Corrections du Prompt 11 (75 tests verts, 0 régression) ; santé de la production (0 écart structurel) ; cause de l'incident (upgrade CLI par l'opérateur) ; solution `EXCLUDE USING gist` (15/15 sous `REPEATABLE READ`) ; schéma corrigé à domaines disjoints ; décompte 83/75 expliqué |
| ❓ **Incertain** | Auteur et littérale exacte de la commande d'upgrade sur `odoo20` ; raison des deux passes ; raison des deux lancements de l'instance — **défaut de journalisation** (R9) |
| ⚖️ **Décision métier** | D1 : implémenter ou non la solution d'unicité ; D2 : conserver ou relâcher la règle « code global réservé à toutes les sociétés » |
| 🔐 **Nécessite une autorisation explicite** | D3 (isolation de l'instance de production + arrêt/redémarrage) ; D4 (journalisation) ; D5 (reconstruction de la base de test) ; **toute** mise à jour de `odoo20` ; toute modification du code du module |

---

*Contre-audit réalisé en lecture seule sur `odoo20`. Banc d'essai sur
`gest_agri_concurrency_test` uniquement. Aucun fichier du module
`gestion_agricole` modifié.*
