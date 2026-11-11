# ANNEXE 6 — STATISTIQUES DU RUNNER

## Code source

- `odoo/tests/result.py:78` : `self.testsRun = 0`
- `odoo/tests/result.py:119` : `self.testsRun += 1` (dans `startTest`)
- `odoo/tests/suite.py:204-220` : `_handleClassSetUp` / `_tearDownPreviousClass`
  collectent les stats pour `setUpClass` et `tearDownClass`
- `odoo/tests/result.py:298` : `self.stats[test_id] += Stat(...)`

## Six classes

| Classe | Méthodes `test_*` | `setUpClass` | Événements stats |
|---|---|---|---|
| `TestAuditPrompt11` | 25 | oui | 2 |
| `TestConfiguration` | 7 | oui | 2 |
| `TestModuleInstall` | 1 | non (hérité) | 2 |
| `TestPatrimony` | 24 | oui | 2 |
| `TestReservationUnicity` | 26 | oui | 2 |
| `TestSecurity` | 16 | oui | 2 |
| **Total** | **99** | **5 explicites** | **12** |

## Réconciliation

| Compteur | Valeur | Explication |
|---|---|---|
| Méthodes de test du module | 99 | 25 + 7 + 1 + 24 + 26 + 16 |
| Événements de cycle de vie | 12 | 6 classes × (setUpClass + tearDownClass) |
| `odoo.tests.stats` (module) | 111 | 99 + 12 |
| `odoo.tests.result` (`testsRun`) | 101 | 99 + 2 (méthodes `web`) |
| Erreurs / Échecs / Ignorés | 0 / 0 / 0 | |

## Sortie réelle

```
odoo.tests.stats: gestion_agricole: 111 tests 22.05s 8448 queries
odoo.tests.stats: web: 6 tests 0.03s 14 queries
odoo.tests.result: 0 failed, 0 error(s) of 101 tests when loading database 'gest_agri_audit_test'
```
