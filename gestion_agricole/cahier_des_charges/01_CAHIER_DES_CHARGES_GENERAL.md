# CAHIER DES CHARGES GÉNÉRAL — SYSTÈME DE GESTION AGRICOLE

## Module `gestion_agricole` — Odoo 20 Community

### 1. PRÉSENTATION DU PROJET

#### 1.1 Contexte
Le projet `gestion_agricole` vise à fournir un système de gestion intégré pour les
exploitations agricoles, basé sur Odoo 20 Community. Le système doit couvrir
l'ensemble des processus agricoles, de la préparation des sols à la commercialisation
de la production, en passant par la gestion des intrants, du personnel, du matériel
et de l'irrigation.

#### 1.2 Objectifs
- Centraliser la gestion de l'exploitation agricole.
- Suivre les campagnes et les cultures par parcelle.
- Gérer les intrants, le personnel et le matériel.
- Assurer la traçabilité des opérations et des produits.
- Calculer les coûts de production et les marges.
- Fournir des tableaux de bord et des rapports d'aide à la décision.

#### 1.3 Périmètre fonctionnel
Le système couvre 11 domaines fonctionnels :
1. Gestion générale de l'exploitation.
2. Référentiels agricoles.
3. Campagnes agricoles.
4. Production végétale.
5. Irrigation et gestion de l'eau.
6. Intrants agricoles.
7. Main-d'œuvre et personnel.
8. Matériel et équipements agricoles.
9. Stocks et traçabilité.
10. Gestion économique et financière.
11. Tableaux de bord et rapports.

#### 1.4 Périmètre technique
- ERP : Odoo 20 Community.
- Module principal : `gestion_agricole` (préfixe `gest_agri`).
- Langue principale : Français.
- Multi-société : oui.
- Multi-exploitation : oui.

### 2. ACTEURS

| Profil | Responsabilités |
|---|---|
| Administrateur | Configuration, droits, paramétrage |
| Directeur d'exploitation | Supervision globale, décisions stratégiques |
| Responsable agricole | Gestion des campagnes et des parcelles |
| Chef de culture | Suivi des cultures et interventions |
| Responsable de parcelle | Saisie des travaux et observations |
| Responsable irrigation | Programmation et suivi de l'irrigation |
| Magasinier | Gestion des stocks et des mouvements |
| Responsable des achats | Commandes et réceptions d'intrants |
| Responsable du matériel | Suivi des équipements et entretiens |
| Gestionnaire du personnel | Affectations et temps de travail |
| Comptable | Coûts et rentabilité |
| Agent de saisie | Saisie des données de terrain |
| Utilisateur en consultation | Lecture seule |

### 3. PRINCIPES GÉNÉRAUX

- Multi-société et multi-exploitation.
- Traçabilité complète des opérations.
- Archivage et réactivation des enregistrements.
- Historique des modifications.
- Gestion des états et des transitions.
- Règles de validation strictes.
- Restrictions d'accès par profil.

### 4. LIMITES DU MODULE

Le module agricole gère la production et le suivi agricole. L'intégration
avec les modules Odoo standard (comptabilité, achats, ventes, stock) est
prévue mais le module agricole ne remplace pas ces modules.

### 5. CRITÈRES D'ACCEPTATION

Chaque fonctionnalité doit être vérifiable par des tests d'acceptation
documentés dans la matrice des tests (document 07).

---

*Rédigé dans le cadre du Prompt N°36 — Module `gestion_agricole` — Odoo 20 Community.*
