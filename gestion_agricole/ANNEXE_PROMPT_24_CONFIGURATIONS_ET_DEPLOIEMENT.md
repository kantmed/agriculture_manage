# ANNEXE 6 — CONFIGURATIONS ET DÉPLOIEMENT

## Fichiers modèles

### /tmp/odoo20-production-proposed.conf
SHA256: 8c534760eeb7e2083566b5c3031df3f77a7f9e9f57d2db3bac58596f12f0e2dc
Taille : 1530 octets

Contenu clé :
- `db_name = odoo20`
- `dbfilter = ^odoo20$`
- `list_db = False`
- `http_port = 8071`
- `logfile = /var/log/odoo/odoo20.log`
- Secrets masqués (`<SECRET_A_CONFIGURER>`)

### /tmp/odoo20-test-proposed.conf
SHA256: 09f838b2e493057019a8fb393c7e8fcb12d64c71b70033e0ad893d24092c9f62
Taille : 1528 octets

Contenu clé :
- `db_name = gest_agri_audit_test`
- `dbfilter = ^gest_agri_audit_test$`
- `http_port = 8072`
- `data_dir = /var/lib/odoo20-test`
- `logfile = /var/log/odoo20-test/odoo20-test.log`
- Secrets masqués

## Procédure de bascule future

1. Sauvegarde préalable (`pg_dump -Fc`).
2. Vérification des ports (8072 libre).
3. Création des répertoires de test.
4. Modification de `/etc/odoo20.conf` (ajout `db_name`, `dbfilter`).
5. Création de `/etc/odoo20-test.conf`.
6. Arrêt propre de la production.
7. Démarrage de la production avec la nouvelle config.
8. Démarrage de l'instance de test.
9. Vérification HTTP et connexions PostgreSQL.
10. Contrôle des journaux.
11. Critères de réussite : 4 contrôles.
12. Retour arrière : restaurer `/etc/odoo20.conf`.

**Aucune bascule réelle effectuée.**

## Sauvegarde et restauration

```bash
pg_dump -Fc -U odoo20 -h 127.0.0.1 -p 5433 odoo20 > /backup/odoo20_$(date +%Y%m%d_%H%M%S).dump
pg_restore --list /backup/odoo20_*.dump | head
```

Test de restauration dans une base isolée recommandé. Ne pas considérer un
`pg_dump` réussi comme preuve d'une restauration valide.
