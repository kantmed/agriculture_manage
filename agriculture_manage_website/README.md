# Agriculture Management Website

## Version 20.0.1.5.0

Cette version ajoute la déclaration d'une demande de maintenance depuis le portail.

### Maintenance du portail
- Consultation des équipements agricoles et de leurs interventions.
- Déclaration d'une demande corrective ou préventive avec date/heure souhaitée.
- Affectation initiale à l'équipe de maintenance de l'équipement ou à une équipe active de la société.
- Enregistrement du demandeur comme créateur de la demande.
- Sélection limitée aux équipements actifs des exploitations accessibles à l'utilisateur.
- Contrôle serveur de l'équipement, du type et de la date.
- Jeton CSRF obligatoire sur le formulaire.
- La création d'une demande ne permet pas au portail de choisir un technicien, une équipe, un statut ou un coût.
- L'affectation et la planification opérationnelle restent gérées dans le back-office.

### Routes du portail
- `/my/agriculture/maintenance/equipment`
- `/my/agriculture/maintenance/equipment/<id>`
- `/my/agriculture/maintenance/requests`
- `/my/agriculture/maintenance/requests/new`
- `/my/agriculture/maintenance/requests/<id>`

### Sécurité
Les recherches de données sont limitées aux exploitations associées au partenaire commercial de l'utilisateur ou dont il est responsable, et à ses sociétés autorisées. Les identifiants transmis par le navigateur sont revalidés côté serveur.

### Mise à niveau
Sauvegarder la base de données et mettre à niveau `agriculture_manage_website`.
