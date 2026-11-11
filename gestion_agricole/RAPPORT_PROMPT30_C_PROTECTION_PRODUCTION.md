# RAPPORT PROMPT 30 — PROTECTION FORMELLE DE LA PRODUCTION

## Module `gestion_agricole` — Odoo 20 Community

### 1. Vérification de protection

| Contrôle | Statut | Preuve |
|---|---|---|
| Connexion à `gest_agri_audit_test` | possible (rôle `odoo20`) | `has_database_privilege` = true |
| Connexion à `odoo20` | possible (rôle `odoo20`) | `has_database_privilege` = true |
| Refus de connexion à `odoo20` pour `gest_agri_dev` | non testé (rôle non créé) | à vérifier après création |
| Refus d'écriture sur `odoo20` | non testé (pas d'écriture réelle) | documenté |

### 2. Méthode de vérification proposée

Après création du rôle `gest_agri_dev` :

```sql
-- Vérifier la connexion à la base de diagnostic
psql -U gest_agri_dev -h 127.0.0.1 -p 5433 -d gest_agri_audit_test -c "SELECT 1;"

-- Vérifier le refus de connexion à la production
psql -U gest_agri_dev -h 127.0.0.1 -p 5433 -d odoo20 -c "SELECT 1;"
-- Attendu : FATAL: permission denied for database "odoo20"
```

### 3. Conclusion

La protection formelle n'est pas encore démontrée. Le rôle `gest_agri_dev` n'a
pas été créé. La vérification sera possible après création du rôle.

**Statut : NON DÉMONTRÉ.**

---

*Rapport — Prompt 30 — Phase C — Module `gestion_agricole`.*
