# CARTOGRAPHIE FONCTIONNELLE

## Module `gestion_agricole` — Odoo 20 Community

### 1. ORGANISATION EN MODULES

| Module | Contenu | Dépendances |
|---|---|---|
| `gestion_agricole` (socle) | Exploitations, sites, parcelles, référentiels, campagnes, production, irrigation, intrants, personnel, matériel, stocks, coûts, tableaux de bord | base, mail, contacts, uom, product, stock, purchase, sale, account, analytic, maintenance |

Le socle unique est recommandé. Les fonctionnalités sont organisées par menus et
groupes de sécurité, pas par modules séparés.

### 2. MENUS PRINCIPAUX

1. Configuration (référentiels, paramètres)
2. Patrimoine agricole (exploitations, sites, parcelles, bâtiments, infrastructures)
3. Campagnes (campagnes, affectation des parcelles, planification)
4. Production (suivi des cultures, interventions, récoltes)
5. Irrigation (sources, réseaux, programmation, consommations)
6. Intrants (achats, stocks, consommations, traçabilité)
7. Personnel (employés, équipes, travaux, temps)
8. Matériel (équipements, utilisations, entretiens)
9. Stocks (magasins, mouvements, inventaires)
10. Économie (coûts, marges, rentabilité)
11. Tableaux de bord (indicateurs, alertes, comparaisons)

### 3. FLUX D'INFORMATION

Les données circulent du terrain (saisie) vers les tableaux de bord (analyse).
Les référentiels alimentent les opérations. Les opérations alimentent les coûts.
Les coûts alimentent les rapports.

---

*Rédigé dans le cadre du Prompt N°36 — Module `gestion_agricole` — Odoo 20 Community.*
