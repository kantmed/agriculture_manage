# RAPPORT PROMPT 30 — SYNTHÈSE DÉCISIONNELLE

## Module `gestion_agricole` — Odoo 20 Community

### 1. Verdicts par domaine

| Domaine | Verdict |
|---|---|
| Identification des processus | VALIDÉ |
| Séparation du code | VALIDÉ |
| Séparation des configurations | VALIDÉ |
| Séparation des bases | NON DÉMONTRÉE |
| Séparation PostgreSQL | NON DÉMONTRÉE |
| Séparation des filestores | NON DÉMONTRÉE |
| Séparation des journaux | VALIDÉ |
| Protection de la production | NON DÉMONTRÉE |
| Lancement du serveur de développement | BLOQUÉ |

### 2. Verdict global

**ISOLATION NON DÉMONTRÉE.**

La phase corrective du code ne peut pas commencer. Le rôle PostgreSQL de
développement doit être créé et validé avant toute modification du code.

### 3. Conditions pour débloquer

1. Créer le rôle `gest_agri_dev` avec des privilèges limités à
   `gest_agri_audit_test`.
2. Vérifier que ce rôle ne peut pas écrire dans `odoo20`.
3. Configurer le filestore de développement dans un répertoire indépendant.
4. Lancer le serveur de développement avec la configuration dédiée.
5. Vérifier l'isolation par des preuves techniques.

### 4. Règle finale

Aucune correction fonctionnelle du module n'est autorisée. La phase corrective
ne pourra commencer qu'après validation de l'isolation et décision explicite
de l'utilisateur.

---

*Rapport — Prompt 30 — Phase I — Module `gestion_agricole`.*
