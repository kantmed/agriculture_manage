# RAPPORT PROMPT 30 — ISOLATION DU FILESTORE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Filestore actuel

- `data_dir` actuel : `/var/lib/odoo`
- Filestore de production : `/var/lib/odoo/filestore/odoo20`
- Filestore de diagnostic : `/var/lib/odoo/filestore/gest_agri_audit_test`
- Les deux partagent le même `data_dir` racine.

### 2. Répertoire de développement prévu

- `/tmp/opencode/dev/data/`
- Filestore : `/tmp/opencode/dev/data/filestore/gest_agri_audit_test/`

### 3. Vérification

- Absence de lien symbolique vers `/var/lib/odoo` : à vérifier après création.
- Permissions indépendantes : à configurer.
- Propriétaire du répertoire : à configurer.
- Absence de partage avec le filestore de production : à vérifier.

### 4. Conclusion

Le filestore de développement n'a pas été créé. La procédure est documentée.

---

*Rapport — Prompt 30 — Phase E — Module `gestion_agricole`.*
