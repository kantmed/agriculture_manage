# Agriculture Manage Livestock — Odoo 20 Community

## Version 1.1.0 — Reproduction et naissances
Cette version ajoute le suivi des cycles de reproduction des animaux suivis individuellement :
- saillie naturelle ou insémination artificielle ;
- date de service et date prévisionnelle de mise bas ;
- confirmation de gestation ;
- enregistrement d'une mise bas et création des fiches des petits ;
- rattachement des petits à leur mère, à leur père si connu, et au cycle de reproduction ;
- consultation de l'historique de reproduction depuis la fiche de la femelle.

Le cycle suit les états : prévu → saillie/insémination réalisée → gestation confirmée → mise bas enregistrée, ou échec/avortement.

### Règles et limites
- Le suivi détaillé de reproduction est réservé aux animaux individuels. Les lots collectifs (notamment volailles) ne sont pas encore gérés par ce cycle.
- Une fiche de reproduction concerne une femelle et une saillie/insémination. Le mâle/père est facultatif.
- La date prévisionnelle de mise bas est saisie par l'utilisateur ; aucune durée de gestation standard n'est imposée, car elle varie selon les espèces et les pratiques.
- Lors de l'enregistrement de la mise bas, le système crée le nombre de fiches individuelles indiqué. Le sexe des petits est initialisé à « Inconnu » et peut être corrigé ensuite.
- Cette version ne calcule pas automatiquement les taux de fertilité, les intervalles entre mises bas, ni les performances génétiques.
- Les soins vétérinaires, vaccinations, alimentation, production, ventes et comptabilité seront traités dans les étapes ultérieures.

### Intégration
Le module réutilise `agriculture.farm`, `agriculture.farm.site` et les groupes de sécurité existants. Il ne modifie pas le modèle `agriculture.farm.operation` ni les campagnes agricoles.

### Installation / mise à jour
Après extraction dans le dossier d'addons personnalisé et redémarrage du serveur :

```bash
./odoo-bin -c /chemin/odoo.conf -d odoo20 -u agriculture_manage_livestock --stop-after-init
```

Pour une première installation, remplacer `-u` par `-i`.

### Vérifications
Les contrôles statiques (syntaxe Python, XML, manifest et structure CSV) ont été effectués. L'installation, les droits effectifs et le scénario complet de reproduction doivent encore être testés sur une base de test Odoo 20 avant déploiement en production.


## Version 20.0.1.2.0 — Santé animale

Ajouts :
- suivi sanitaire individuel ou collectif par lot ;
- vaccinations, traitements, maladies, déparasitage, visites vétérinaires,
  quarantaine et interventions ;
- planification, réalisation et annulation d'un événement ;
- médicament/vaccin, dosage, quantité, coût et intervenant ;
- prochain rappel et délais d'attente viande/lait.

Limites connues :
- aucun mouvement de stock n'est généré automatiquement ;
- aucun ordre de facturation ou écriture comptable n'est créé ;
- les délais d'attente sont enregistrés et restent à saisir/valider par l'utilisateur ;
- les décès restent gérés par les mouvements de cheptel, pas par cet écran sanitaire.
