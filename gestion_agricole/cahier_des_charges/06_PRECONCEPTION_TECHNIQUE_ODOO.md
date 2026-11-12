# PRÉCONCEPTION TECHNIQUE ODOO

## Module `gestion_agricole` — Odoo 20 Community

### 1. MODÈLES ENVISAGÉS

#### Référentiels (13 modèles)
`farm.type`, `soil.type`, `crop.type`, `crop.variety`, `livestock.species`,
`livestock.breed`, `operation.type`, `treatment.type`, `fertilizer.type`,
`irrigation.type`, `equipment.type`, `building.type`, `production.type`.

Champs communs : `name`, `code`, `company_id`, `active`.

#### Patrimoine (10 modèles)
`farm`, `farm_access`, `plot`, `site`, `building`, `infrastructure`,
`water_source`, `irrigation_network`, `irrigation_sector`, `irrigation_pump`.

#### Production
`campaign`, `crop_cycle`, `intervention`, `harvest`.

#### Intrants
`input_type`, `input_purchase`, `input_consumption`, `input_lot`.

#### Personnel
`employee`, `team`, `work_log`.

#### Matériel
`equipment`, `equipment_usage`, `equipment_maintenance`.

#### Stocks
`warehouse`, `location`, `stock_move`, `inventory`.

#### Économie
`cost`, `revenue`, `margin`.

### 2. RELATIONS PRINCIPALES

- `farm` → `site` (One2many)
- `site` → `plot` (One2many)
- `farm` → `building`, `infrastructure`, `water_source` (One2many)
- `campaign` → `plot` (Many2many via affectation)
- `plot` → `crop_cycle` (One2many)
- `crop_cycle` → `intervention` (One2many)
- `crop_cycle` → `harvest` (One2many)

### 3. INTÉGRATIONS ODOO STANDARD

- `res.company` : multi-société.
- `res.users` : droits et profils.
- `product.product` : intrants.
- `stock.location` : emplacements.
- `account.move` : coûts (optionnel).
- `purchase.order` : achats d'intrants (optionnel).

### 4. SÉCURITÉ

- 3 groupes : user, manager, admin.
- ACL par modèle.
- Règles d'enregistrement multi-société.
- `bypass_search_access` sur les champs calculés de `res.users`.

---

*Rédigé dans le cadre du Prompt N°36 — Module `gestion_agricole` — Odoo 20 Community.*
