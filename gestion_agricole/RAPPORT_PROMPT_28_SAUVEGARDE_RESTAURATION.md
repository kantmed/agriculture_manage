# RAPPORT PROMPT N°28 — SAUVEGARDE ET RESTAURATION

## Module `gestion_agricole` — Odoo 20 Community

### 1. Procédure de sauvegarde (documentaire)

```bash
pg_dump -Fc -U odoo20 -h 127.0.0.1 -p 5433 odoo20 > /backup/odoo20_$(date +%Y%m%d_%H%M%S).dump
pg_restore --list /backup/odoo20_*.dump | head
```

### 2. Test de restauration

```bash
createdb -U odoo20 -h 127.0.0.1 -p 5433 odoo20_restore_test
pg_restore -U odoo20 -h 127.0.0.1 -p 5433 -d odoo20_restore_test /backup/odoo20_*.dump
```

Ne pas considérer un `pg_dump` réussi comme preuve d'une restauration valide.

### 3. Retour arrière

| Scénario | Décision | Restauration nécessaire ? |
|---|---|---|
| Échec avant création de l'extension | Arrêt | non |
| Échec pendant le backfill | Arrêt, rollback automatique | non |
| Échec pendant la création de la contrainte | Arrêt, rollback automatique | non |
| Échec de mise à jour du module | Arrêt | non (sauf corruption) |
| Erreur après migration | Évaluation | possible |
| Erreur fonctionnelle après réouverture | Évaluation | possible |

### 4. Statut

- FAIT OBSERVÉ : aucune sauvegarde réelle effectuée.
- PROPOSITION : procédure documentée.
- NON DÉMONTRÉ : restauration réelle.

---

*Rapport — Prompt N°28 — Phase G — Module `gestion_agricole`.*
