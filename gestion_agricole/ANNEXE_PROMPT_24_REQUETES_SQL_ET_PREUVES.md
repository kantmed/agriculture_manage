# ANNEXE 4 — REQUÊTES SQL ET PREUVES

## Collations des bases

```sql
SELECT datname, datcollate, datctype FROM pg_database
WHERE datname IN ('odoo20','gest_agri_audit_test','gest_agri_concurrency_test');
```

## Collations des colonnes

```sql
SELECT table_name, column_name, collation_name, data_type
FROM information_schema.columns
WHERE table_name LIKE 'gest_agri%type' AND column_name IN ('code','name');
```

## Index uniques

```sql
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename LIKE 'gest_agri%' AND indexname LIKE '%unique%';
```

## Validité des index

```sql
SELECT count(*) FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid
WHERE c.relname LIKE 'gest_agri%' AND NOT i.indisvalid;
```

## Contrainte GiST

```sql
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
WHERE conname = 'gest_agri_reference_reservation_scope_exclusion';
```

## Réservations orphelines

```sql
SELECT count(*) FROM gest_agri_reference_reservation;
```

## Production (lecture seule)

```sql
SELECT state, latest_version, write_date, write_uid
FROM ir_module_module WHERE name='gestion_agricole';
SELECT count(*) FROM pg_class WHERE relname='gest_agri_reference_reservation';
SELECT count(*) FROM pg_extension WHERE extname='btree_gist';
SELECT count(*) FROM gest_agri_farm;
SELECT count(*) FROM gest_agri_site;
```

## Tests de normalisation GiST

```sql
INSERT INTO gest_agri_reference_reservation (model_name, kind, normalized, scope_lo, scope_hi)
VALUES ('test.collation','code','abc',1,NULL);
-- second insert with same key -> ExclusionViolation
```

## Sortie du runner

```
odoo.tests.stats: gestion_agricole: 111 tests 22.05s 8448 queries
odoo.tests.stats: web: 6 tests 0.03s 14 queries
odoo.tests.result: 0 failed, 0 error(s) of 101 tests when loading database 'gest_agri_audit_test'
```
