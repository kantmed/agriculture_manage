# RAPPORT PROMPT 31 — PROPRIÉTÉ DES OBJETS ET PRIVILÈGES ODOO

## Module `gestion_agricole` — Odoo 20 Community

### 1. Exploitation normale

Privilèges nécessaires : SELECT, INSERT, UPDATE, DELETE, séquences, fonctions.

### 2. Modifications structurelles

Privilèges nécessaires : CREATE TABLE, ALTER TABLE, DROP TABLE, CREATE INDEX,
ALTER INDEX, création de contraintes, modification de colonnes, création de
séquences, modifications de vues, créations de fonctions.

### 3. Pourquoi les GRANT ne remplacent pas la propriété

Les GRANT permettent l'accès aux objets, mais ne confèrent pas la propriété.
Un rôle non propriétaire ne peut pas ALTER ou DROP un objet, même avec des
GRANT. Odoo a besoin de la propriété pour les migrations.

### 4. Stratégie compatible avec les migrations futures

Le rôle de développement doit être propriétaire des objets de la base de
développement. Cela nécessite une restauration avec `--no-owner` et un
`ALTER ... OWNER TO` ou l'utilisation de `--role`.

---

*Rapport — Prompt 31 — Phase E — Module `gestion_agricole`.*
