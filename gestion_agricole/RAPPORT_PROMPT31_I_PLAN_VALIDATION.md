# RAPPORT PROMPT 31 — PLAN DE VALIDATION

## Module `gestion_agricole` — Odoo 20 Community

### Matrice de validation

| Test | Résultat attendu |
|---|---|
| Connexion à la base de développement | Autorisée |
| Lecture de la base de développement | Autorisée |
| Création d'une table de test | Autorisée |
| Modification d'une table de test | Autorisée |
| Création d'un index de test | Autorisée |
| Utilisation d'une séquence de test | Autorisée |
| Connexion à `odoo20` | Refusée |
| Accès aux objets de `odoo20` | Impossible |
| Connexion à `gest_agri_audit_test` (si Option 2) | Refusée |
| Création de base par `gest_agri_dev` | Refusée |
| Création de rôle par `gest_agri_dev` | Refusée |
| Accès aux privilèges administrateur | Refusé |

### Conclusion

Tous les tests d'écriture seront exécutés exclusivement sur la nouvelle base
de développement et seulement après autorisation.

---

*Rapport — Prompt 31 — Phase I — Module `gestion_agricole`.*
