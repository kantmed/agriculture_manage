# ANNEXE 8 — SAUVEGARDE ET RESTAURATION

## Sauvegarde (documentaire)

```bash
pg_dump -Fc -U odoo20 -h 127.0.0.1 -p 5433 odoo20 > /backup/odoo20_$(date +%Y%m%d_%H%M%S).dump
pg_restore --list /backup/odoo20_*.dump | head
```

## Test de restauration

```bash
createdb -U odoo20 -h 127.0.0.1 -p 5433 odoo20_restore_test
pg_restore -U odoo20 -h 127.0.0.1 -p 5433 -d odoo20_restore_test /backup/odoo20_*.dump
```

Ne pas considérer un `pg_dump` réussi comme preuve d'une restauration valide.

## Retour arrière

| Scénario | Décision | Restauration nécessaire ? |
|---|---|---|
| Échec avant création de l'extension | Arrêt | non |
| Échec pendant le backfill | Arrêt, rollback automatique | non |
| Échec pendant la création de la contrainte | Arrêt, rollback automatique | non |
| Échec de mise à jour du module | Arrêt | non (sauf corruption) |
| Erreur après migration | Évaluation | possible |
| Erreur fonctionnelle après réouverture | Évaluation | possible |

Ne jamais supprimer manuellement des tables ou contraintes sans évaluer les
dépendances.
