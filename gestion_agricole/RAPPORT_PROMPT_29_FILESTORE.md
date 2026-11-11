# RAPPORT PROMPT N°29 — VÉRIFICATION DU FILESTORE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Filestore actuel

- `data_dir` actuel : `/var/lib/odoo` (config active)
- Filestore de production : `/var/lib/odoo/filestore/odoo20`
- Filestore de diagnostic : `/var/lib/odoo/filestore/gest_agri_audit_test`

### 2. Vérification

- Les deux filestores partagent le même `data_dir` (`/var/lib/odoo`).
- Il n'y a pas de lien symbolique détecté entre les filestores.
- Le filestore de développement proposé (`/tmp/opencode/dev/data/filestore`) est
  indépendant.

### 3. Conclusion

Le filestore de production et celui de diagnostic partagent le même répertoire
racine. L'isolation complète nécessite des `data_dir` distincts (proposé dans
la configuration de développement).

---

*Rapport — Prompt N°29 — Phase E — Module `gestion_agricole`.*
