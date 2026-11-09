# Gestion agricole — Version 5

## Gestion renforcée des infrastructures

- Ajout du responsable de l'infrastructure.
- Ajout des coordonnées GPS (latitude et longitude) avec contrôles de plage.
- Ajout du suivi de maintenance : dernière intervention, prochaine échéance et notes.
- Indicateur calculé et recherchable de maintenance à effectuer, sans stockage afin de tenir compte de la date courante.
- Ajout d'un filtre de recherche pour les infrastructures dont la maintenance est échue.
- Ajout de tests sur les coordonnées, la cohérence des dates et l'échéance de maintenance.

## Validation

Les tests fonctionnels Odoo ne sont pas exécutés dans cet environnement : ils doivent être lancés sur une instance Odoo 20 avec les dépendances du projet.
