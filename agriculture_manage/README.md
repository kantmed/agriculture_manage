# Gestion agricole

Module principal de gestion des exploitations agricoles pour Odoo 20.

## Fonctionnalités

- Gestion multi-société des exploitations agricoles.
- Identification automatique des exploitations (`EXP-AAAA-NNNN`).
- Gestion des responsables, contacts, coordonnées et activités agricoles.
- Gestion des sites rattachés à une exploitation, avec référence automatique.
- Gestion des parcelles rattachées à une exploitation et, facultativement, à un site.
- Conversion des superficies en hectares depuis les hectares, ares et mètres carrés.
- Contrôle du cumul des parcelles par rapport à la superficie totale de l'exploitation.
- Saisie du type de sol, de l'irrigation, de l'état et des coordonnées GPS des parcelles.
- Gestion des infrastructures (entrepôts, serres, puits, réservoirs, stations de pompage, bâtiments, ateliers, bureaux et réseaux d'irrigation).
- Tableau de bord avec indicateurs filtrés sur la société active.
- Historique des échanges et activités via le chatter sur les fiches qui en héritent.
- Profils d'accès : utilisateur agricole, responsable agricole et administrateur agricole.

## Règles de gestion principales

1. La superficie totale d'une exploitation doit être strictement positive.
2. La superficie d'une parcelle doit être strictement positive.
3. Le cumul des superficies des parcelles d'une exploitation ne doit pas dépasser sa superficie totale.
4. Un site ou une infrastructure associé à une exploitation doit appartenir à cette même exploitation.
5. Les coordonnées GPS doivent respecter les plages de latitude (-90 à 90) et de longitude (-180 à 180).
6. La surface et la capacité d'une infrastructure ne peuvent pas être négatives.
7. Le responsable d'une exploitation doit avoir accès à la société de cette exploitation.

## Tableau de bord

Les indicateurs de superficie ont des définitions distinctes :

- **Superficie totale** : somme des superficies déclarées sur les exploitations actives de la société courante.
- **Superficie affectée** : somme des superficies des parcelles enregistrées sur ces exploitations, y compris les parcelles archivées, conformément au contrôle de capacité.
- **Superficie non affectée** : superficie totale moins superficie affectée.
- **Superficie en culture / disponible** : somme des parcelles actives dans l'état correspondant.

## Installation / mise à niveau

Ajouter `agriculture_manage` au chemin des addons Odoo, puis installer le module depuis Applications. Après mise à jour du code, mettre à niveau le module :

```bash
./odoo-bin -d NOM_BASE -u agriculture_manage --stop-after-init
```

Les modules complémentaires (cultures, stock, élevage, matériel, maintenance, projets, analyses, comptabilité et ventes) sont distincts et doivent être installés selon leurs dépendances et les besoins de l'exploitation.

## Tests

Les tests Odoo du module se trouvent dans `tests/`. Ils couvrent notamment les références automatiques, les contrôles de superficie, les rattachements et les indicateurs du tableau de bord. Ils doivent être exécutés dans un environnement Odoo 20 configuré avec une base de test.
