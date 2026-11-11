# ANNEXE 7 — SAUVEGARDE ET RESTAURATION

## Sauvegarde (documentaire)

```bash
# Sauvegarde logique
pg_dump -Fc -U odoo20 -h 127.0.0.1 -p 5433 odoo20 > /backup/odoo20_$(date +%Y%m%d_%H%M%S).dump

# Vérification
pg_restore --list /backup/odoo20_*.dump | head

# Test de restauration dans une base isolée
createdb -U odoo20 -h 127.0.0.1 -p 5433 odoo20_restore_test
pg_restore -U odoo20 -h 127.0.0.1 -p 5433 -d odoo20_restore_test /backup/odoo20_*.dump
```

Ne réalise aucune sauvegarde réelle pendant cette mission.

## Retour arrière

| Scénario | Décision | État de la base | Restauration nécessaire ? |
|---|---|---|---|
| Échec avant création de l'extension | Arrêt | inchangée | non |
| Échec pendant le backfill | Arrêt, rollback automatique | transaction annulée | non |
| Échec pendant la création de la contrainte | Arrêt, rollback automatique | transaction annulée | non |
| Échec de mise à jour du module | Arrêt | transaction annulée | non (sauf corruption) |
| Erreur après migration | Évaluation | données modifiées | possible |
| Erreur fonctionnelle après réouverture | Évaluation | données modifiées | possible |

Ne jamais supprimer manuellement des tables ou contraintes sans évaluer les
dépendances.

## Critères d'autorisation

- [ ] Sauvegarde vérifiée (test de restauration réussi).
- [ ] Doublons historiques contrôlés.
- [ ] Privilèges DBA confirmés.
- [ ] Fenêtre de maintenance planifiée.
- [ ] Procédure de retour arrière documentée.
- [ ] Autorisation explicite de l'utilisateur.
- [ ] Isolation de l'instance appliquée (D2).
- [ ] Journalisation activée (D3).
