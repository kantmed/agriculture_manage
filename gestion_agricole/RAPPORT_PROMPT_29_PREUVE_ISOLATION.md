# RAPPORT PROMPT N°29 — PREUVE D'ISOLATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. Démonstration

| Critère | Statut | Preuve |
|---|---|---|
| Copie indépendante du code | ✅ | SHA256 identique, répertoire distinct |
| Configuration indépendante | ✅ | Fichier modèle créé, non appliqué |
| Base de diagnostic identifiée | ✅ | `gest_agri_audit_test` |
| Filestore indépendant | ⚠️ | Partage le même `data_dir` racine |
| Port libre | ✅ | 8072 non écouté |
| Journaux indépendants | ✅ | Chemin distinct proposé |
| Accès PostgreSQL limité | ❌ | Rôle `odoo20` peut écrire dans `odoo20` |
| Absence de risque d'écriture dans `odoo20` | ❌ | Le rôle PostgreSQL de développement peut écrire en production |

### 2. Conclusion

**L'isolation n'est pas complète.** Le rôle PostgreSQL `odoo20` peut écrire
dans `odoo20` (production). Une séparation des rôles PostgreSQL est nécessaire
pour une isolation réelle.

**Verdict : ISOLATION NON DÉMONTRÉE.**

---

*Rapport — Prompt N°29 — Phase F — Module `gestion_agricole`.*
