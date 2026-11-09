# Agriculture Management Website

## Version 20.0.1.3.0

Cette version ajoute la gestion des infrastructures agricoles depuis le portail utilisateur.

### Routes du portail
- `/my/agriculture/infrastructures` : liste et recherche.
- `/my/agriculture/infrastructures/new` : formulaire de création.
- `/my/agriculture/infrastructures/<id>` : fiche détaillée.
- `/my/agriculture/infrastructures/<id>/edit` : modification.

### Sécurité et validation
- Les infrastructures sont limitées aux exploitations accessibles à l'utilisateur connecté.
- Le site sélectionné doit appartenir à l'exploitation choisie.
- Les surfaces et capacités négatives sont refusées.
- Les types et états sont validés côté serveur.
- Les formulaires POST utilisent le jeton CSRF du portail.

### Mise à niveau
Mettre à niveau le module `agriculture_manage_website` après sauvegarde de la base de données.
