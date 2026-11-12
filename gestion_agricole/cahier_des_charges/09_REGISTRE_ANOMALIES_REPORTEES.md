# REGISTRE DES ANOMALIES REPORTÉES À LA PHASE FINALE

## Module `gestion_agricole` — Odoo 20 Community

Les anomalies des audits précédents (Prompts 11 à 35) sont conservées.

### Registre des insuffisances (INF-01 à INF-22)

| ID | Insuffisance | État actuel | Condition de résolution |
|---|---|---|---|
| INF-01 | Isolation du processus Odoo | Non démontrée | Environnement distinct |
| INF-02 | Rôle PostgreSQL `gest_agri_dev` | Non créé | Création après autorisation |
| INF-03 | Base `gest_agri_dev_db` | Non créée | Création après autorisation |
| INF-04 | Privilèges PUBLIC | Non complètement vérifiés | Audit ACL réel |
| INF-05 | Règles pg_hba.conf | Non vérifiées | Validation DBA |
| INF-06 | Propriété des objets restaurés | Non démontrée | Vérification post-restauration |
| INF-07 | Sauvegarde PostgreSQL | Procédure non validée | Dump et contrôle |
| INF-08 | Restauration réelle | Non démontrée | Test de restauration |
| INF-09 | Filestore | Cohérence non démontrée | Copie synchronisée et contrôle |
| INF-10 | Extension btree_gist | Disponible mais non installée en production | Validation dans la base de développement |
| INF-11 | Privilèges par défaut | Non validés | Analyse selon le rôle créateur |
| INF-12 | Tests de concurrence | Insuffisants | Campagne multiprocessus |
| INF-13 | Tests ORM complets | Non démontrés | Exécution en environnement isolé |
| INF-14 | Non-régression | Non démontrée | Campagne finale |
| INF-15 | Restauration après incident | Non démontrée | Test documenté |
| INF-16 | Normalisation non unique | Divergence documentée | Option A (colonnes normalisées) |
| INF-17 | Réconciliation non exécutée | Procédure documentée | Implémentation et test |
| INF-18 | Concurrence complémentaire | 6 scénarios non démontrés | Tests en 2 processus |
| INF-19 | Origine de `write_date` | Inconnue | Pas de solution (pas de logs) |
| INF-20 | Copie de travail non vérifiée | Vérifiée | — |
| INF-21 | Tests statiques non exécutés | Exécutés | — |
| INF-22 | Registre des insuffisances non créé | Créé | — |

### Risques résiduels

| # | Risque | Statut |
|---|---|---|
| R1 | Conflit code global ↔ société simultané | ✅ ÉLIMINÉ |
| R3 | Instance dessert les bases de diagnostic | ⚙️ proposition non appliquée |
| R9 | Aucun journal exploitable | ⚙️ proposition non appliquée |
| R10 | Mécanisme inerte en production | 🔒 bloqué par autorisation |
| R11 | Libellés non appliqués en production | 🔒 bloqué par autorisation |
| R12 | Écriture SQL directe (hors ORM) | documenté |
| R13 | Réservation non purgée sur chemin non-ORM | documenté |
| R14 | `setup_reservations()` ne répare pas les incohérences | documenté (limite) |
| R15 | Isolation non démontrée | ⚠️ bloquant |

---

*Rédigé dans le cadre du Prompt N°36 — Module `gestion_agricole` — Odoo 20 Community.*
