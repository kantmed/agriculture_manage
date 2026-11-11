# RAPPORT PROMPT N°27 — AUDIT CONTRADICTOIRE FINAL, CORRECTION DES VERDICTS ET PRÉPARATION DE LA PHASE CORRECTIVE

## Module `gestion_agricole` — Odoo 20 Community

> Rapport de correction des contradictions. Le verdict global est rectifié :
> « PRÊT SOUS CONDITIONS » est remplacé par une distinction claire entre
> quatre niveaux de préparation.

---

# 1. RÉSUMÉ EXÉCUTIF

## 1.1 Correction du verdict

Le rapport 26 annonçait « PRÊT SOUS CONDITIONS » tout en reconnaissant des
blocages (isolation, journalisation, activation GiST, réconciliation non
démontrée). Cette formulation est **incorrecte**.

Le verdict est rectifié comme suit :

| Niveau de préparation | Statut |
|---|---|
| Prêt pour poursuivre les travaux de développement | ✅ OUI |
| Prêt pour les tests de validation | ✅ OUI (sur bases de diagnostic) |
| Prêt pour préparer un déploiement | ✅ OUI (plan documenté, Prompt 22) |
| Prêt pour déployer en production | ❌ NON |

**Verdict global : NON PRÊT pour la production.**

La production n'est pas activée. Le mécanisme GiST est inerte (table absente,
extension absente). Aucune écriture n'a été effectuée.

## 1.2 Correction de la réserve GiST

Le rapport 26 affirmait « GiST arbitre » sans préciser que le mécanisme est
**inerte en production** (pas de table, pas d'extension). En production,
l'unicité repose uniquement sur les 49 index uniques existants. La réserve
GiST est un mécanisme de **diagnostic**, pas de production.

---

# 2. ENVIRONNEMENT

| Élément | Valeur |
|---|---|
| Odoo | 20.0 |
| PostgreSQL | 18.6, port 5433 |
| Base de production | `odoo20` — lecture seule |
| Base de diagnostic | `gest_agri_audit_test` |
| Serveur Odoo | non redémarré, non modifié |

---

# 3. PHASE A — VÉRIFICATION DES DIX LIVRABLES

Les 10 livrables du Prompt 26 ont été vérifiés :

| # | Fichier | Taille | Existe | Contenu correspond |
|---|---|---|---|---|
| 1 | `RAPPORT_PROMPT_26_CONTRE_AUDIT_COMPLET.md` | 8076 | ✅ | ✅ |
| 2 | `ANNEXE_PROMPT_26_VERIFICATION_DES_SIX_ANNEXES.md` | 1014 | ✅ | ✅ |
| 3 | `ANNEXE_PROMPT_26_NORMALISATION_UNICITE.md` | 1066 | ✅ | ✅ |
| 4 | `ANNEXE_PROMPT_26_RECONCILIATION.md` | 1194 | ✅ | ✅ |
| 5 | `ANNEXE_PROMPT_26_MATRICE_13_MODELES.md` | 1545 | ✅ | ✅ |
| 6 | `ANNEXE_PROMPT_26_CONCURRENCE.md` | 1297 | ✅ | ✅ |
| 7 | `ANNEXE_PROMPT_26_STATISTIQUES_RUNNER.md` | 1399 | ✅ | ✅ |
| 8 | `ANNEXE_PROMPT_26_ISOLATION_JOURNALISATION.md` | 1393 | ✅ | ✅ |
| 9 | `ANNEXE_PROMPT_26_SAUVEGARDE_RESTAURATION.md` | 1079 | ✅ | ✅ |
| 10 | `ANNEXE_PROMPT_26_PLAN_CORRECTIF.md` | 1189 | ✅ | ✅ |

Les 10 livrables existent, sont non vides et correspondent aux sujets annoncés.

---

# 4. PHASE B — CORRECTION DES CONTRADICTIONS

## 4.1 Verdict global rectifié

Voir section 1.1. Le verdict « PRÊT SOUS CONDITIONS » est remplacé par
« NON PRÊT pour la production » avec distinction des quatre niveaux.

## 4.2 Unicité PostgreSQL et GiST

En production : 49 index uniques, 0 table de réservation, 0 `btree_gist`.
Le mécanisme GiST est **inerte en production**. L'unicité repose sur les
index uniques existants. Le mécanisme GiST est validé en diagnostic uniquement.

## 4.3 Normalisation

Divergence confirmée (tabs, ß, ẞ : Python plus strict ; İ : SQL plus strict).
Aucun doublon ne passe. L'intégrité est protégée. La qualité du message
d'erreur est dégradée pour İ/I.

## 4.4 Réconciliation

Non démontrée. `setup_reservations()` est idempotent, pas réparateur.
La base de diagnostic est propre (0 orpheline), mais aucune procédure de
réconciliation n'a été exécutée.

## 4.5 Concurrence

5 scénarios démontrés en 2 processus. 6 scénarios complémentaires non
démontrés en 2 processus. Validés par tests unitaires et contrainte SQL.

## 4.6 Statistiques

99 méthodes, 12 cycle de vie, 111 stats, 101 `testsRun`, 0/0/0.
Prouvé par le code du runner.

## 4.7 Isolation et journalisation

Non appliquées. Propositions documentées. Configuration active non modifiée.

## 4.8 Origine de `write_date`

Inconnue. Aucun journal exploitable. Métadonnée technique rafraîchie par une
opération non identifiée.

---

# 5. PHASE C — VÉRIFICATION DES AFFIRMATIONS TECHNIQUES

## 5.1 Production (lecture seule)

| Contrôle | Valeur |
|---|---|
| Module | `installed` v`20.0.1.0.0` |
| `write_date` | `2026-11-11 03:08:36.034021` |
| `write_uid` | 1 |
| Index uniques | 49 (0 invalide) |
| Table de réservation | absente |
| `btree_gist` | absent |
| Exploitations | 1 |
| Sites | 1 |
| Parcelles | 0 |
| Droits d'accès | 71 |

## 5.2 Diagnostic

| Contrôle | Valeur |
|---|---|
| Réservations orphelines | 0 |
| Contrainte GiST | présente |
| Extension `btree_gist` | présente |
| Enregistrements de test | 0 |

---

# 6. PHASE D — LISTE DÉFINITIVE DES TRAVAUX RESTANTS

## 6.1 Corrections de code (proposées, non appliquées)

1. **Normalisation** : colonnes `code_normalized` / `name_normalized` générées.
2. **Réconciliation** : procédure transactionnelle de réconciliation.
3. **Concurrence** : 6 scénarios complémentaires en 2 processus.

## 6.2 Prérequis DBA

1. `CREATE EXTENSION btree_gist` sur `odoo20`.
2. Validation des privilèges.

## 6.3 Configuration système

1. Isolation de l'instance (D2).
2. Journalisation (D3).

## 6.4 Tests fonctionnels

1. Compléter les tests de concurrence.
2. Tester la réconciliation.
3. Vérifier l'idempotence après réparation.

---

# 7. PHASE E — PRÉPARATION DE LA PHASE CORRECTIVE

La phase corrective doit être réalisée en environnement de développement, sur
les bases de diagnostic uniquement. Les corrections proposées doivent être
testées avant toute application en production.

Aucune modification du code source n'a été effectuée dans ce prompt.

---

# 8. PHASE F — VERDICT FINAL

## 8.1 Verdicts par domaine

| Domaine | Verdict |
|---|---|
| Normalisation | VALIDÉ SOUS CONDITIONS |
| Unicité PostgreSQL | VALIDÉ |
| Réconciliation | NON DÉMONTRÉ |
| Concurrence | VALIDÉ SOUS CONDITIONS |
| Cycle de vie 13 modèles | VALIDÉ |
| Migration | VALIDÉ SOUS CONDITIONS |
| Isolation production/test | BLOQUÉ |
| Journalisation | BLOQUÉ |
| Sauvegarde/restauration | VALIDÉ SOUS CONDITIONS |
| Activation GiST | BLOQUÉ |

## 8.2 Verdict global

**NON PRÊT pour la production.**

La production n'est pas activée. Le mécanisme GiST est inerte. Aucune écriture
n'a été effectuée. La décision d'activation appartient exclusivement à
l'utilisateur.

---

# 9. RÈGLE FINALE

- Aucune activation en production.
- `btree_gist` non installé dans `odoo20`.
- `gestion_agricole` non mis à jour en production.
- Odoo non redémarré.
- Aucune modification du code source.
- Les résultats non démontrés sont déclarés comme tels.

---

*Rapport — Prompt N°27 — Module `gestion_agricole` — Odoo 20 Community.
Toutes les écritures sur bases de diagnostic ; production en lecture seule.*
