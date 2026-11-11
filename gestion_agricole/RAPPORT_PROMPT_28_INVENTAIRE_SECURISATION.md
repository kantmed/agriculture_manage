# RAPPORT PROMPT N°28 — INVENTAIRE ET SÉCURISATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. Environnement

| Élément | Valeur |
|---|---|
| Odoo | 20.0, `/mnt/srv/share/odoo20/odoo` |
| Python | 3.12.0, `/etc/odoo20-venv/bin/python` |
| PostgreSQL | 18.6, port 5433 |
| Base de production | `odoo20` — lecture seule |
| Base de diagnostic | `gest_agri_audit_test` |
| Serveur Odoo | PID 328398 (session interactive), port 8071 |

### 2. État Git

- Branche : `main`, à jour avec `origin/main`.
- Fichier modifié : `tests/test_reservation_unicity.py` (fix cleanup Prompt 23, +15/-4 lignes).
- Fichiers non suivis : 29 rapports/annexes (Prompts 14-27) + config models.
- Aucun `git reset --hard` ou `git clean` effectué.

### 3. Empreintes SHA256 des fichiers critiques

| Fichier | SHA256 |
|---|---|
| `models/configuration/reservation.py` | `1b50ade8afd72001c75a0c47375acb6930bd5f5be63f2e02314beb3dd485cceb` |
| `models/configuration/_common.py` | `720e36a360040136f4c5b27012320e62e59f06f2a7f4bd3bb1ef922a9b01a7ff` |
| `__manifest__.py` | `0e0568e8eacd27d78c825af3897bdc57977d15aded9a4537ea1f3a1505999a1a` |

### 4. Sauvegarde du code source

- Emplacement : `/tmp/opencode/dev_backup/gestion_agricole_backup_20261111_052600/`
- Fichiers : 41 fichiers Python
- Manifeste : présent
- Empreinte de `reservation.py` dans la sauvegarde : identique à l'original ✅

### 5. Démonstration d'isolation

- Processus de production (PID 314241) : **non actif** (absent de `ps`).
- Seul processus Odoo actif : PID 328398 (session interactive de test, utilisateur `kantmoh`).
- Port 8071 : servi par PID 328398 (session de test, pas la production).
- **Conclusion** : l'environnement de développement est isolé de la production. La production n'est pas servie par un processus actif.

### 6. Inventaire des modèles concernés

13 modèles de référence utilisant `ReferenceReservationMixin` :
`farm.type`, `soil.type`, `crop.type`, `crop.variety`, `livestock.species`,
`livestock.breed`, `operation.type`, `treatment.type`, `fertilizer.type`,
`irrigation.type`, `equipment.type`, `building.type`, `production.type`.

### 7. État de production (lecture seule)

| Élément | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| Index uniques | 49 (0 invalide) |
| Table de réservation | absente |
| `btree_gist` | absent |
| Exploitations | 1 |
| Sites | 1 |

### 8. État de la base de diagnostic

| Élément | Valeur |
|---|---|
| `btree_gist` | présent |
| Table de réservation | présente |
| Contrainte EXCLUDE | présente |
| Réservations orphelines | 0 |
| Enregistrements de test | 0 |

### 9. Conclusion

L'environnement de développement est isolé de la production. La sauvegarde du
code source est créée et vérifiée. Les empreintes des fichiers critiques sont
relevées. La phase corrective peut être engagée, mais aucune modification du
code source n'a été effectuée dans ce prompt (conformément aux conditions de
sécurité).

---

*Rapport d'inventaire — Prompt N°28 — Phase A — Module `gestion_agricole`.*
