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


## Version 20.0.1.3.0 — Alimentation animale et consommation de stock

Ajouts :
- création de rations par exploitation et par espèce ;
- composition d'une ration en aliments classés dans la catégorie agricole « Aliments pour animaux » ;
- quantités de ration exprimées par tête et par jour ;
- préparation d'une distribution pour un animal identifié ou un lot ;
- calcul des quantités proposées selon l'effectif mémorisé et le nombre de jours couverts ;
- génération d'un transfert interne Odoo depuis le magasin de l'exploitation vers l'emplacement virtuel de production ;
- validation physique et réservation du stock laissées au flux standard de l'application Inventaire ;
- clôture de la distribution après validation de la sortie et contrôle des quantités réellement sorties.

Règles :
- les aliments doivent être des produits suivis en stock et classés avec `Catégorie agricole = Aliments pour animaux` ;
- le magasin doit appartenir à la même société et, s'il est affecté à une exploitation, à la même exploitation ;
- une distribution concerne exactement un animal ou un lot ;
- la préparation crée un transfert Odoo en brouillon confirmé ; elle ne force jamais la validation du stock ;
- une distribution terminée ne peut pas être annulée directement. Utiliser un retour de stock ou un mouvement correctif dans Inventaire.

Limites de cette version :
- pas de calcul nutritionnel (énergie, protéines, minéraux) ni de formulation automatique ;
- pas de gestion des pâturages ou de l'ingestion au pâturage ;
- pas de ventilation comptable/analytique spécifique des consommations d'aliments vers le coût de revient du cheptel ;
- les retours, pertes et écarts de distribution restent gérés par les opérations natives de stock ;
- les traductions françaises et arabes doivent être complétées dans une phase dédiée.

Vérifications réalisées sur l'archive :
- syntaxe Python, XML et structure des CSV ;
- cohérence des fichiers déclarés dans le manifeste.
L'installation, les droits effectifs, les transferts réels et les scénarios multi-sociétés doivent encore être testés sur une base de test Odoo 20 avant mise en production.
