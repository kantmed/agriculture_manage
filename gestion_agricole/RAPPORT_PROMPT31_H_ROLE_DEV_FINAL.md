# RAPPORT PROMPT 31 — CONCEPTION FINALE DU RÔLE DÉDIÉ

## Module `gestion_agricole` — Odoo 20 Community

### 1. Rôle proposé : `gest_agri_dev`

Attributs :
- LOGIN : oui
- NOSUPERUSER
- NOCREATEDB
- NOCREATEROLE
- NOREPLICATION
- NOBYPASSRLS

### 2. Commandes proposées (non exécutées)

```sql
CREATE ROLE gest_agri_dev WITH LOGIN PASSWORD '<SECRET_A_CONFIGURER>'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

GRANT CONNECT, TEMPORARY ON DATABASE gest_agri_dev_db TO gest_agri_dev;
GRANT USAGE, CREATE ON SCHEMA public TO gest_agri_dev;
```

### 3. Vérifications de sécurité

- Connexion à la base de développement : autorisée
- Connexion à `odoo20` : refusée
- Accès aux objets de `odoo20` : impossible
- Création de base : refusée
- Création de rôle : refusée
- Accès aux privilèges administrateur : refusé

### 4. Mécanisme sécurisé de configuration du secret

Le mot de passe ne doit pas apparaître en clair dans les arguments de
commandes ou dans l'historique du shell. Utiliser un fichier de configuration
ou une variable d'environnement.

---

*Rapport — Prompt 31 — Phase H — Module `gestion_agricole`.*
