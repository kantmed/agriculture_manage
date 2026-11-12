# MATRICE DES TESTS D'ACCEPTATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. TESTS FONCTIONNELS

| # | Scénario | Critère d'acceptation |
|---|---|---|
| 1 | Créer une exploitation | Exploitation créée avec société |
| 2 | Créer une campagne | Campagne créée avec dates |
| 3 | Affecter une parcelle à une culture | Affectation enregistrée |
| 4 | Saisir une intervention | Intervention enregistrée sur la parcelle |
| 5 | Enregistrer une récolte | Quantité et qualité enregistrées |
| 6 | Calculer le rendement | Rendement = quantité / superficie |
| 7 | Enregistrer une consommation d'intrant | Stock décrémenté |
| 8 | Programmer une irrigation | Tour d'eau créé |
| 9 | Enregistrer un temps de travail | Temps et coût enregistrés |
| 10 | Calculer les coûts d'une campagne | Coûts agrégés par parcelle |

### 2. TESTS DE SÉCURITÉ

| # | Scénario | Critère d'acceptation |
|---|---|---|
| 1 | Utilisateur société A ne voit pas les données de société B | Isolation respectée |
| 2 | Utilisateur simple ne peut pas créer de référentiel global | Refus |
| 3 | Gestionnaire ne peut pas modifier une exploitation d'une autre société | Refus |

### 3. TESTS DE CONCURRENCE

| # | Scénario | Critère d'acceptation |
|---|---|---|
| 1 | Deux créations simultanées avec même code global | Une seule réussit |
| 2 | Création globale vs création société | Conflit détecté |

---

*Rédigé dans le cadre du Prompt N°36 — Module `gestion_agricole` — Odoo 20 Community.*
