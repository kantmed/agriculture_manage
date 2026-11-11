# RAPPORT PROMPT 31 — ANALYSE DE PUBLIC

## Module `gestion_agricole` — Odoo 20 Community

### 1. Analyse

Dans PostgreSQL, certains privilèges peuvent être accordés à PUBLIC par défaut.

Pour le rôle `odoo20` :
- `has_database_privilege('odoo20', 'odoo20', 'CONNECT')` = true
- `has_database_privilege('odoo20', 'odoo20', 'CREATE')` = true
- `has_database_privilege('odoo20', 'odoo20', 'TEMPORARY')` = true

### 2. Risque d'accès indirect

Le futur rôle `gest_agri_dev` pourrait potentiellement accéder à `odoo20` si
des privilèges sont accordés à PUBLIC. Cependant, le rôle `odoo20` n'est
membre d'aucun groupe, et les privilèges sont accordés directement au rôle.

### 3. Conclusion

Le risque d'accès indirect via PUBLIC doit être vérifié après création du
rôle `gest_agri_dev`. Les privilèges de PUBLIC sur les bases et schémas doivent
être examinés.

**Attention** : `REVOKE CONNECT ON DATABASE odoo20 FROM PUBLIC;` n'a pas été
exécuté (pourrait affecter d'autres applications).

---

*Rapport — Prompt 31 — Phase B — Module `gestion_agricole`.*
