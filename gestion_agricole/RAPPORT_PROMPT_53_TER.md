# PROMPT 53 TER — CORRECTION DE LA NAVIGATION ET VALIDATION FINALE DES INTERVENTIONS AGRICOLES

## Module `gestion_agricole` — Odoo 20 Community

### 1. OBJECTIF

Finaliser le Prompt 53 sans refaire le développement fonctionnel.

Deux objectifs uniquement :

1. Corriger l'absence de la méthode `action_view_interventions` dans `gest_agri.crop.cycle`.
2. Exécuter réellement les 39 tests du fichier `tests/test_crop_intervention.py` dans Odoo 20.

### 2. CORRECTION FONCTIONNELLE

Examiner :

- `models/production/crop_cycle.py`
- `views/production_views.xml`
- `views/production_intervention_views.xml`

Ajouter la méthode `action_view_interventions` au modèle `gest_agri.crop.cycle`.

Elle doit permettre d'ouvrir les interventions associées au cycle sélectionné :

- afficher uniquement les interventions du cycle courant ;
- utiliser l'action et les vues déjà définies pour les interventions ;
- transmettre le cycle courant dans le contexte lorsque cela est pertinent ;
- conserver les filtres et possibilités de navigation existants ;
- respecter les droits d'accès et règles de sécurité existants.

Vérifier également la cohérence du bouton de navigation et de sa liaison XML.

Ne pas créer une seconde action inutile si une action existante peut être réutilisée.

### 3. CONTRÔLE DU CODE EXISTANT

Ne pas réécrire le module.

Vérifier seulement que les protections métier précédemment développées sont toujours présentes :

- champs dérivés protégés ;
- cohérence des dates avec le cycle ;
- transitions d'état contrôlées ;
- interventions réalisées protégées ;
- règles de suppression conservées ;
- ACL inchangées.

Corriger uniquement une anomalie directement liée à cette intervention.

### 4. ENVIRONNEMENT PYTHON ET CŒUR ODOO

Utiliser exclusivement :

`/etc/odoo20-venv/bin/python`

Python 3.12.

Les fichiers suivants ont été signalés comme modifiés :

- `/mnt/sr/share/odoo20/odoo/tools/binary.py`
- `/mnt/sr/share/odoo20/odoo/init.py`

Ne pas les modifier davantage.

Ne pas les restaurer automatiquement. Vérifier leur état actuel et signaler précisément les modifications existantes dans le rapport final.

Aucune modification du cœur Odoo n'est autorisée dans cette mission.

### 5. SYNCHRONISATION ET MISE À JOUR

Après correction :

1. Modifier la copie de développement :
   `/tmp/opencode/dev/gestion_agricole/`

2. Répliquer les fichiers nécessaires dans :
   `/mnt/sr/share/odoo20/addons/kantmoh/gestion_agricole/`

3. Vérifier leur identité avec `diff -q`.

4. Mettre à jour exclusivement la base `odoo20` avec Python 3.12.

Commande indicative :

`/etc/odoo20-venv/bin/python /mnt/sr/share/odoo20/odoo/odoo-bin -c /etc/odoo20.conf -d odoo20 --no-http --max-cron-threads=0 --stop-after-init -u gestion_agricole`

### 6. EXÉCUTION RÉELLE DES TESTS

Exécuter les 39 méthodes de test du fichier :

`tests/test_crop_intervention.py`

Utiliser les mécanismes de test Odoo et un filtre ciblé adapté à la classe réelle de tests.

Ne pas compter comme tests réussis :

- une simple vérification syntaxique ;
- une inspection du code ;
- une simulation logique ;
- des tests non exécutés à cause d'un échec de chargement du registre.

Le rapport doit distinguer précisément :

- tests exécutés et réussis ;
- tests exécutés et échoués ;
- tests en erreur ;
- tests non exécutés.

Si les 39 tests ne peuvent pas être exécutés, identifier la cause exacte sans déclarer le Prompt 53 validé.

### 7. PÉRIMÈTRE STRICT

Autorisé :
- copie de développement ;
- réplication du module dans les addons ;
- mise à jour du module `gestion_agricole` ;
- tests sur la base `odoo20`.

Interdit :
- modification de `/etc/odoo20.conf` ;
- modification du cœur Odoo ;
- modification des rôles ou permissions PostgreSQL ;
- modification d'autres bases ;
- modification d'Odoo 16 ;
- redémarrage des services Odoo partagés ;
- installation de `btree_gist` ;
- modification d'autres modules.

### 8. RAPPORT FINAL OBLIGATOIRE

Présenter :

1. Méthode `action_view_interventions` ajoutée et fonctionnement vérifié.
2. Fichiers modifiés.
3. Résultat de la mise à jour de `gestion_agricole` sur `odoo20`, avec code de sortie.
4. Nombre exact de tests réellement exécutés.
5. Résultats détaillés : réussis, échoués, erreurs et non exécutés.
6. Confirmation de synchronisation des répertoires.
7. État des deux fichiers du cœur Odoo précédemment signalés.
8. Confirmation du respect du périmètre strict.
9. Anomalies restantes.

Ne pas annoncer la validation définitive du Prompt 53 si la mise à jour du registre ou l'exécution réelle des tests échoue.
