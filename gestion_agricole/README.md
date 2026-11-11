# Gestion Agricole

Module Odoo 20 Community pour la gestion d'une exploitation agricole.

## État actuel

- **Version** : `20.0.1.0.0`
- **Préfixe technique des modèles** : `gest_agri.`
- **Modèle installé** : 26 modèles, 23 actions, 44 menus, 71 lignes de droits
  d'accès, 677 identifiants externes.

## Contenu du module

### Référentiels de configuration (13 modèles)

Chaque référentiel porte un nom, un code, une description, un état actif et une
société facultative. Un enregistrement sans société est **global** : il est
réservé à toutes les sociétés (et administré par un administrateur agricole) ;
un enregistrement avec société est propre à cette société.

| Modèle | Libellé |
|---|---|
| `gest_agri.farm.type` | Type d'exploitation |
| `gest_agri.soil.type` | Type de sol |
| `gest_agri.crop.type` | Type de culture (annuelle / pérenne) |
| `gest_agri.crop.variety` | Variété de culture (rattachée à un type de culture) |
| `gest_agri.livestock.species` | Espèce animale |
| `gest_agri.livestock.breed` | Race animale (rattachée à une espèce) |
| `gest_agri.operation.type` | Type d'opération agricole |
| `gest_agri.treatment.type` | Type de traitement |
| `gest_agri.fertilizer.type` | Type d'engrais |
| `gest_agri.irrigation.type` | Type d'irrigation |
| `gest_agri.equipment.type` | Type d'équipement |
| `gest_agri.building.type` | Type de bâtiment |
| `gest_agri.production.type` | Type de production animale |

### Patrimoine agricole (10 modèles)

| Modèle | Rôle |
|---|---|
| `gest_agri.farm` | Exploitation agricole (code unique par société, surface totale, surface affectée calculée, responsable, compte analytique) |
| `gest_agri.farm.access` | Droit d'accès d'un utilisateur à une exploitation (rôles `user`, `manager`, `admin`) |
| `gest_agri.site` | Site d'exploitation (rattaché à une exploitation) |
| `gest_agri.plot` | Parcelle agricole (surface, type de sol, type d'irrigation, pH, pente, coordonnées) |
| `gest_agri.building` | Bâtiment agricole (type, surface, capacité) |
| `gest_agri.infrastructure` | Infrastructure agricole (voie, clôture, stockage, drainage) |
| `gest_agri.water.source` | Source d'eau (puits, forage, source, rivière, bassin, réseau) |
| `gest_agri.irrigation.network` | Réseau d'irrigation (source d'eau, type, débit) |
| `gest_agri.irrigation.sector` | Secteur d'irrigation (parcelles desservies) |
| `gest_agri.irrigation.pump` | Pompe d'irrigation (puissance, débit) |

### Extension de `res.users`

Deux champs calculés portent les périmètres d'accès :

- `gest_agri_farm_ids` — exploitations accessibles (responsable ou droit d'accès) ;
- `gest_agri_managed_farm_ids` — exploitations administrées.

Ces champs alimentent les domaines des droits d'accès : l'isolation par
exploitation est donc appliquée **au niveau serveur**, et non seulement dans les
menus ou les boutons.

## Unicité des références

L'unicité des codes et des noms est garantie par **trois mécanismes
complémentaires** :

1. **Index uniques PostgreSQL** — trois par référentiel :
   `(company_id, code)`, `(code)` pour les globaux, `(COALESCE(company_id, 0),
   name)`. Ils garantissent l'unicité par société et entre codes globaux.
2. **Table de réservation** `gest_agri_reference_reservation`, avec une
   contrainte d'exclusion PostgreSQL `EXCLUDE USING gist` portant sur un
   périmètre `int8range`. Elle garantit le conflit **transversal** entre un code
   global et un code de société, y compris lorsque les deux créations sont
   strictement concurrentes sous `REPEATABLE READ` (niveau d'isolation par
   défaut d'Odoo 20). Le périmètre d'un code global est `[1, +∞)` et celui d'un
   nom global `{-1}` : les domaines sont disjoints par construction.
3. **Contraintes Python** — message métier en français, affiché à
   l'utilisateur.

> La table de réservation n'est **créée que si l'extension PostgreSQL
> `btree_gist` est installée** dans la base. Son installation est une décision
> opérationnelle explicite : `CREATE EXTENSION btree_gist;`. Tant qu'elle n'a
> pas été prise, le mécanisme reste inerte et la base n'est pas modifiée.

## Sécurité

Trois groupes :

- **Utilisateur agricole** — lecture des référentiels et des exploitations
  auxquelles il a accès ;
- **Responsable agricole** — création et modification des référentiels de sa
  société, des exploitations qu'il gère et de leur patrimoine ;
- **Administrateur agricole** — administration complète dans le périmètre de ses
  sociétés.

Un utilisateur non administrateur ne peut pas modifier ni supprimer ses propres
droits d'accès, ni gérer une référence globale.

## Tests

La suite est exécutée sur une base de diagnostic isolée :

```bash
odoo-bin -c /etc/odoo20.conf -d gest_agri_audit_test \
          --no-http --max-cron-threads=0 --stop-after-init \
          --test-enable --test-tags /gestion_agricole
```

Elle couvre la création, la modification, l'archivage, la réactivation, la
suppression, l'isolation multi-sociétés, la protection des droits d'accès, les
conflits d'unicité (y compris le conflit global / société) et la concurrence
réelle sous `REPEATABLE READ` avec deux connexions PostgreSQL indépendantes.

## Architecture

- Un seul addon installable : `gestion_agricole`.
- Réutilisation des modèles natifs Odoo (`product`, `stock`, `account`,
  `analytic`, `maintenance`).
- Aucune comptabilité ni gestion de stock parallèle.
- Aucun changement des anciens modules agricoles.

## Points connus

- Les modèles de production végétale, d'élevage, de campagne, de traitement, de
  fertilisation et de production *au sens « instance »* ne sont pas encore
  définis : seuls les **types** existent. Les entrées de menu « Production
  végétale », « Élevage », « Matériel », « Personnel » et « Économie » sont donc
  encore vides.
- `report/` et `wizard/` sont des emplacements réservés, volontairement vides.
