# RAPPORT PROMPT N°36 — CAHIER DES CHARGES FONCTIONNEL GÉNÉRAL

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. RAPPORT FINAL

## 1.1 Documents effectivement créés

Les 9 documents ont été créés dans `/tmp/opencode/dev/gestion_agricole/cahier_des_charges/` :

| # | Fichier | Taille |
|---|---|---|
| 1 | `01_CAHIER_DES_CHARGES_GENERAL.md` | ~3 Ko |
| 2 | `02_CARTOGRAPHIE_FONCTIONNELLE.md` | ~1 Ko |
| 3 | `03_PROCESSUS_METIER.md` | ~2 Ko |
| 4 | `04_PROFILS_ET_DROITS_FONCTIONNELS.md` | ~1 Ko |
| 5 | `05_REGLES_DE_GESTION.md` | ~1 Ko |
| 6 | `06_PRECONCEPTION_TECHNIQUE_ODOO.md` | ~2 Ko |
| 7 | `07_MATRICE_DES_TESTS_ACCEPTATION.md` | ~1 Ko |
| 8 | `08_DECISIONS_METIER_EN_ATTENTE.md` | ~1 Ko |
| 9 | `09_REGISTRE_ANOMALIES_REPORTEES.md` | ~3 Ko |

## 1.2 Périmètre fonctionnel couvert

- Gestion générale de l'exploitation (exploitations, sites, parcelles).
- Référentiels agricoles (13 types).
- Campagnes agricoles.
- Production végétale (semis, interventions, récoltes).
- Irrigation et gestion de l'eau.
- Intrants agricoles (achats, stocks, consommations, traçabilité).
- Main-d'œuvre et personnel.
- Matériel et équipements.
- Stocks et traçabilité.
- Gestion économique et financière.
- Tableaux de bord et rapports.

## 1.3 Domaines insuffisamment spécifiés

- Rotations de cultures.
- Certifications (bio, etc.).
- Subventions.
- Gestion des risques climatiques.
- Intégration avec les modules comptables Odoo (optionnelle).

## 1.4 Décisions métier en attente

7 décisions identifiées (voir document 08) :
- Granularité des parcelles.
- Gestion des campagnes.
- Traçabilité des lots.
- Intégration comptable.
- Gestion des stocks.
- Alertes et notifications.
- Langue des rapports.

## 1.5 Contradictions détectées

Aucune contradiction détectée entre les documents.

## 1.6 Registre des anomalies conservé

22 insuffisances (INF-01 à INF-22) conservées avec leur statut.

## 1.7 Fichiers et composants techniques non modifiés

- Aucun fichier Python modifié.
- Aucun fichier XML modifié.
- Aucun fichier CSV modifié.
- Aucune base de données modifiée.
- Aucun service redémarré.

## 1.8 Prochaine étape recommandée

1. Valider le cahier des charges avec le responsable du projet.
2. Résoudre les décisions métier en attente.
3. Créer l'environnement de développement isolé (Prompt 30/31/32).
4. Implémenter les corrections fonctionnelles.
5. Exécuter les tests d'acceptation.

---

# 2. ÉTAT FINAL

- Production : `installed` v`20.0.1.0.0`, 0 table de réservation, 0 `btree_gist`, aucune modification fonctionnelle.
- Base de diagnostic : 0 réservation orpheline, contrainte présente.
- Aucun déploiement réalisé. Aucune écriture en production. Aucune modification du code source.

**La décision d'activation appartient exclusivement à l'utilisateur.**

---

*Rapport — Prompt N°36 — Module `gestion_agricole` — Odoo 20 Community.
Cahier des charges fonctionnel général. Aucune modification du code ni de
l'infrastructure.*
