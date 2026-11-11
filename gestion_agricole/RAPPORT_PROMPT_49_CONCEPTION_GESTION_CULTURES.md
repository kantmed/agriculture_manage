# RAPPORT PROMPT N°49 — CONCEPTION DE LA GESTION DES CULTURES ET DE LEUR AFFECTATION AUX PARCELLES

## Module `gestion_agricole` — Odoo 20 Community

> **Nature de ce document** : étude de conception préalable.
> Aucun modèle, fichier Python/XML, manifeste, ACL ni donnée de la base `odoo20`
> n'a été modifié. Seul ce rapport a été rédigé.

---

# 1. INVENTAIRE DES MODÈLES ET CHAMPS EXISTANTS

## 1.1 Référentiels liés aux cultures

### `gest_agri.crop.type` — Type de culture

| Champ | Type | Propriétés |
|---|---|---|
| `name` | Char | requis, indexé, unique par société |
| `code` | Char | requis, indexé, unique par société/global |
| `description` | Text | — |
| `active` | Boolean | défaut `True` |
| `company_id` | Many2one `res.company` | défaut société courante, `False` = global |
| `sequence` | Integer | défaut 10 |
| `crop_cycle` | Selection | `annual` / `perennial`, requis, défaut `annual` |

Unicité garantie par index PostgreSQL (`UniqueIndex`) + mixin de réservation
`ReferenceReservationMixin` (mécanisme inerte sans `btree_gist`).

### `gest_agri.crop.variety` — Variété de culture

| Champ | Type | Propriétés |
|---|---|---|
| `name` | Char | requis, indexé |
| `code` | Char | requis, indexé |
| `description` | Text | — |
| `active` | Boolean | défaut `True` |
| `company_id` | Many2one `res.company` | défaut société courante, `False` = global |
| `sequence` | Integer | défaut 10 |
| `crop_type_id` | Many2one `gest_agri.crop.type` | **requis**, `check_company`, `ondelete=restrict` |

Une variété est donc **toujours rattachée à un type de culture**. C'est un point
d'appui direct pour la future culture implantée.

### Autres référentiels sans lien direct avec les cultures

`gest_agri.operation.type` (type d'opération agricole) existe déjà mais n'est
rattaché à aucun modèle opérationnel. Il servira aux futures interventions.

## 1.2 Patrimoine

### `gest_agri.plot` — Parcelle agricole

Champs structurants :

| Champ | Type | Remarque |
|---|---|---|
| `name`, `code` | Char | code unique par exploitation |
| `farm_id` | Many2one `gest_agri.farm` | requis, cascade |
| `site_id` | Many2one `gest_agri.site` | optionnel, cohérence exploitation contrôlée |
| `company_id` | Many2one `res.company` | related `farm_id.company_id`, stocké |
| `area` | Float (ha) | requis, défaut 0 |
| `soil_type_id`, `irrigation_type_id` | Many2one | référentiels |
| **`crop_type_id`** | Many2one `gest_agri.crop.type` | **optionnel**, `check_company`, `ondelete=restrict` |
| `state` | Selection | `available`, `cultivated`, `fallow`, `unavailable` |
| `notes`, `description` | Text | documentation |
| `active`, `sequence` | — | archivage / ordre |

Le champ `crop_type_id` est utilisé :
- dans la liste des parcelles (colonne) ;
- dans le formulaire (groupe principal) ;
- dans la recherche (filtre et regroupement « Type de culture ») ;
- dans le test `test_plot_crop_type_assignment`.

**Il s'agit d'une caractéristique statique de la parcelle** (vocation ou type de
culture indicatif). Il ne comporte ni date, ni variété, ni état, ni historique.
Il ne peut donc pas représenter une culture réellement implantée. Il doit être
**conservé tel quel** ; son éventuelle clarification (aide/label) fera l'objet
d'une décision séparée.

### `gest_agri.farm` — Exploitation

Champs utiles à la conception :
- `total_area`, `allocated_area` (somme des surfaces des parcelles) ;
- `plot_ids` (One2many), `site_ids` (One2many) ;
- `company_id`, `manager_id`, `status`, `notes` ;
- `_inherit = ["mail.thread", "mail.activity.mixin"]`.

### `gest_agri.site` — Site

- `area_ha`, `plot_ids`, `farm_id`, `company_id`, `notes`.

## 1.3 Modèles absents (vérifiés dans tout le module)

Aucun modèle n'existe pour :

- `gest_agri.campaign` (campagne agricole) ;
- culture implantée / cycle de culture ;
- intervention / opération réalisée ;
- récolte / production ;
- lot, stock agricole, intrant ;
- équipement, personnel, coûts.

Les menus « Production végétale », « Élevage », « Matériel », « Personnel »,
« Économie » existent dans `views/menu_views.xml` mais sont **vides**.

---

# 2. RELATIONS DÉJÀ DISPONIBLES

```
res.company
   └── gest_agri.farm            (company_id)
         ├── site_ids  ──────────► gest_agri.site
         │       └── plot_ids ───► gest_agri.plot
         ├── plot_ids ───────────► gest_agri.plot
         ├── building_ids, infrastructure_ids, water_source_ids…
         └── access_ids ─────────► gest_agri.farm.access

gest_agri.crop.type
   └── variétés (par crop_type_id) ► gest_agri.crop.variety

gest_agri.plot
   └── crop_type_id ─────────────► gest_agri.crop.type   (statique, non opérationnel)
```

Il n'existe **aucune** relation opérationnelle entre une parcelle et une culture
datée, ni entre une culture et une campagne.

---

# 3. ÉLÉMENTS DU CAHIER DES CHARGES APPLICABLES

| Document | Élément | Portée pour la conception |
|---|---|---|
| 01 — Général | « Suivre les campagnes et les cultures par parcelle » | Justifie un modèle de culture par parcelle. |
| 03 — Processus | Créer une campagne, puis affecter les parcelles aux cultures | La campagne précède l'affectation. |
| 03 — Processus | Création d'une culture : campagne, culture, variété, date de semis | Champs attendus : campagne, type, variété, date de semis. |
| 03 — Processus | Suivi des stades, récolte, rendement | Hors périmètre immédiat (interventions/récoltes ultérieures). |
| 05 — Règles | **« Une parcelle ne peut pas être affectée à deux cultures simultanément »** | Règle d'exclusivité temporelle à implémenter. |
| 05 — Règles | Campagnes définies par dates de début et de fin | Modèle campagne avec dates. |
| 05 — Règles | Historique, archivage, états et transitions | Modèle avec `active`, `state`, suivi. |
| 06 — Préconception | Modèles prévus : `campaign`, `crop_cycle`, `intervention`, `harvest` | `crop_cycle` est le nom cible. |
| 06 — Préconception | `campaign` → `plot` (Many2many via affectation) ; `plot` → `crop_cycle` (One2many) | Le cycle de culture porte l'affectation. |
| 06 — Préconception | `crop_cycle` → `intervention`, `harvest` (One2many) | Extensions futures. |
| 07 — Tests | « Affecter une parcelle à une culture » | Test d'acceptation prioritaire. |
| 08 — Décisions | Campagnes : une par an vs plusieurs ; rotations non spécifiées | Décisions ouvertes à ne pas trancher arbitrairement. |

---

# 4. LACUNES FONCTIONNELLES CONSTATÉES

1. **Aucune culture opérationnelle datée** : `crop_type_id` sur la parcelle ne
   permet ni succession, ni historique, ni variété, ni état.
2. **Aucune campagne agricole** : le rattachement campagne/culture est impossible
   aujourd'hui.
3. **Aucune règle d'exclusivité** : rien n'empêche deux cultures simultanées.
4. **Aucun historique de succession** : aucune trace des cultures passées.
5. **Aucune numérotation** : `data/sequences.xml` est vide et réservé.
6. **Aucune vue ni ACL** pour la production végétale.
7. **Aucune gestion des interventions/récoltes** (hors périmètre immédiat).

---

# 5. MODÈLE OPÉRATIONNEL RECOMMANDÉ

## 5.1 Principe

Créer **un modèle unique** représentant l'implantation d'une culture sur une
parcelle pendant une période donnée :

> `gest_agri.crop.cycle` — « Culture implantée » (cycle de culture)

Un enregistrement = **une culture, sur une parcelle, sur un intervalle de dates**.
C'est ce modèle qui porte l'historique des successions et l'exclusivité
temporelle.

La campagne est **retirée de la première brique** : elle sera ajoutée par un
champ `campaign_id` nullable lorsque le modèle `gest_agri.campaign` existera
(voir §10). Cela évite de créer une référence vers un modèle inexistant ou de
figer prématurément les règles de campagne non validées.

## 5.2 Réponses aux questions de conception

| # | Question | Réponse recommandée |
|---|---|---|
| 1 | Plusieurs cultures successives dans l'année ? | **Oui**, via plusieurs `crop.cycle` avec des intervalles disjoints. |
| 2 | Plusieurs cultures simultanées ? | **Non**, conformément à la règle 05. À revoir si les cultures associées deviennent un besoin validé. |
| 3 | Culture principale / secondaire / associée ? | **Pas de champ en phase 1** : incompatible avec l'exclusivité. Décision métier à valider avant toute introduction. |
| 4 | Date de semis / plantation ? | `date_start` (Date, requis). Une date réelle distincte de la date prévue reste une décision ouverte. |
| 5 | Fin prévue / fin réelle ? | Deux champs : `date_end_planned` et `date_end_actual`, tous deux facultatifs. |
| 6 | Rattachement à une campagne absente ? | **Différé** : pas de champ `campaign_id` en phase 1 ; ajout nullable en phase 2 après création de `campaign`. |
| 7 | Variété rattachée au type ? | `crop_variety_id` optionnel, filtré par `crop_type_id` et contrôlé en contrainte. |
| 8 | États ? | `planned` → `planted` → `in_progress` → `done`, plus `cancelled`. |
| 9 | Historique des successions ? | Chaque cycle est conservé (archivage, pas suppression) ; relation `plot.crop_cycle_ids`. |
| 10 | Cohérence exploitation/site/parcelle/culture ? | `farm_id`/`site_id`/`company_id` dérivés de `plot_id` ; `check_company` sur les référentiels ; contrôle variété/type. |

---

# 6. DESCRIPTION DÉTAILLÉE DES CHAMPS

## 6.1 Modèle `gest_agri.crop.cycle`

| Champ | Type | Propriétés recommandées |
|---|---|---|
| `name` | Char | « Référence », requis, `default` = séquence `gest_agri.crop.cycle`, `copy=False`, indexé |
| `plot_id` | Many2one `gest_agri.plot` | requis, `ondelete="cascade"`, indexé |
| `farm_id` | Many2one `gest_agri.farm` | related `plot_id.farm_id`, stocké, lecture seule, `precompute=True`, indexé |
| `site_id` | Many2one `gest_agri.site` | related `plot_id.site_id`, stocké, lecture seule, indexé |
| `company_id` | Many2one `res.company` | related `plot_id.company_id`, stocké, lecture seule, `precompute=True`, indexé |
| `crop_type_id` | Many2one `gest_agri.crop.type` | requis, `check_company=True`, `ondelete="restrict"`, indexé |
| `crop_variety_id` | Many2one `gest_agri.crop.variety` | optionnel, `check_company=True`, `ondelete="restrict"`, indexé, domaine sur `crop_type_id` |
| `date_start` | Date | requis, « Date de semis / plantation » |
| `date_end_planned` | Date | optionnel, « Fin prévue » |
| `date_end_actual` | Date | optionnel, « Fin réelle » |
| `state` | Selection | `planned` (Prévue), `planted` (Implantée), `in_progress` (En cours), `done` (Terminée), `cancelled` (Annulée), défaut `planned`, indexé |
| `area_ha` | Float | `digits=(16, 2)`, défaut 0.0, surface occupée par la culture (décision ouverte : préremplir avec `plot.area` ?) |
| `notes` | Text | Notes internes libres |
| `active` | Boolean | défaut `True` (archivage) |
| `sequence` | Integer | défaut 10 |

Champs calculés utiles (recommandés, non stockés) :
- `is_current` : culture actuellement en cours (dates + état), recherchable ;
- éventuellement `display_name` plus lisible (référence + parcelle + culture).

Champs **à ne pas créer en phase 1** :
- `campaign_id` (modèle absent) ;
- `crop_role` / culture secondaire (règle d'exclusivité) ;
- `harvest_ids`, `intervention_ids` (modèles absents) ;
- `yield` / rendement (dépend de la récolte).

## 6.2 Évolutions sur les modèles existants

- `gest_agri.plot` : ajouter `crop_cycle_ids = One2many("gest_agri.crop.cycle", "plot_id")`
  et éventuellement `crop_cycle_count` calculé. **Ne pas toucher** à `crop_type_id`.
- `gest_agri.plot` : ajouter un onglet « Cultures » dans le formulaire.
- `gest_agri.farm` : éventuellement un compteur `crop_cycle_count` (non prioritaire).
- `gest_agri.crop.type` / `crop.variety` : aucune modification nécessaire.

## 6.3 Séquence

Créer dans `data/sequences.xml` une séquence `gest_agri.crop.cycle`, par exemple :

```
CUL/%(range_year)s/%(month)s/%(day)s/0001
```

ou plus simplement `CUL/%(year)s/00001`. Le format exact reste une décision
d'exploitation ; l'important est une référence unique et lisible.

---

# 7. CONTRAINTES ET RÈGLES DE GESTION RECOMMANDÉES

## 7.1 Cohérence des relations

1. `plot_id` requis ; `farm_id`, `site_id`, `company_id` toujours dérivés de la
   parcelle (jamais saisis).
2. `crop_type_id` et `crop_variety_id` doivent appartenir à la société de la
   parcelle (`check_company` + `_check_company_auto`).
3. `crop_variety_id.crop_type_id` doit être égal à `crop_type_id` :
   `@api.constrains("crop_type_id", "crop_variety_id")`.
4. Le site de la parcelle est déjà contrôlé par `plot._check_site_farm`.

## 7.2 Cohérence des dates

- `date_end_planned >= date_start` si les deux sont renseignées.
- `date_end_actual >= date_start` si les deux sont renseignées.
- Aucune contrainte entre fin prévue et fin réelle (l'écart est informatif).
- `date_start` requis ; les fins restent facultatives.

## 7.3 Exclusivité temporelle (règle 05)

Pour une même parcelle, deux cycles **non annulés** ne peuvent pas se
chevaucher. Intervalle effectif :

```
fin_effective = date_end_actual or date_end_planned or +infinity
```

Contrainte Python (`@api.constrains`) parcourant les autres cycles de la parcelle
et rejetant tout chevauchement, avec message explicite en français. Les
enregistrements `cancelled` sont exclus du contrôle.

Points à valider :
- une culture terminée le 30/06 et une nouvelle démarrant le 30/06 : chevauchement
  ou succession ? Recommandation : considérer l'intervalle comme **inclusif** et
  refuser le même jour, sauf décision contraire ;
- les cycles archivés (`active=False`) doivent-ils encore bloquer ? Recommandation :
  oui pour préserver l'historique réel, sauf s'ils sont annulés.

## 7.4 Unicité et concurrence

### Ce qui peut être garanti sans extension

- **Index unique** `(plot_id, date_start) WHERE active IS TRUE` via
  `models.UniqueIndex` : empêche deux cycles de même date de début sur une
  parcelle. C'est une garantie PostgreSQL réelle, y compris sous concurrence.
- Contrainte Python de chevauchement : **meilleur effort**, non fiable en
  concurrence (deux transactions peuvent valider deux intervalles chevauchants
  si leurs dates de début diffèrent).

### Ce qui exigerait `btree_gist`

La garantie forte serait une contrainte d'exclusion :

```sql
ALTER TABLE gest_agri_crop_cycle
ADD CONSTRAINT gest_agri_crop_cycle_no_overlap
EXCLUDE USING gist (
    plot_id WITH =,
    daterange(
        date_start,
        COALESCE(date_end_actual, date_end_planned, 'infinity'::date),
        '[]'
    ) WITH &&
)
WHERE (state <> 'cancelled');
```

Cette contrainte nécessite `btree_gist` (opérateur GiST pour l'égalité sur
`plot_id`). **L'extension n'est pas installée et ne doit pas l'être dans ce
prompt.** Elle correspond à la décision D1 / INF-10, toujours en attente
d'autorisation.

**Recommandation** : phase 1 = contrainte Python + index unique
`(plot_id, date_start)` + documentation explicite de la limite concurrente.
Phase ultérieure = ajout de la contrainte d'exclusion SQL si `btree_gist` est
autorisé, sur le modèle du mécanisme déjà utilisé dans
`models/configuration/reservation.py` (SQL brut conditionné à la présence de
l'extension, jamais de `CREATE EXTENSION` par le module).

## 7.5 États et transitions

| État | Sens | Transitions autorisées |
|---|---|---|
| `planned` | Prévue, non semée | → `planted`, → `cancelled` |
| `planted` | Semée / plantée | → `in_progress`, → `cancelled` |
| `in_progress` | Suivi actif | → `done`, → `cancelled` |
| `done` | Terminée | (lecture seule ; remise en brouillon réservée admin si besoin) |
| `cancelled` | Annulée | → `planned` (réactivation par un responsable/admin) |

Boutons d'action dans l'en-tête du formulaire. Les transitions doivent être
implémentées par méthodes explicites, pas par simple édition du champ `state`.
La pertinence de distinguer `planted` et `in_progress` reste à valider : une
version à 4 états (`planned`, `in_progress`, `done`, `cancelled`) est une
alternative acceptable.

## 7.6 Suivi et notes

- `notes` (Text) pour les observations.
- `state` avec `tracking=True` si le modèle hérite de `mail.thread` (cohérent
  avec `gest_agri.farm`). Recommandation : hériter de `mail.thread` uniquement,
  sans `mail.activity.mixin` en phase 1, pour garder le formulaire simple.
- Archivage plutôt que suppression.

## 7.7 Droits d'accès

Aucune modification des groupes existants (`user`, `manager`, `admin`).
Trois lignes ACL à ajouter, sur le modèle de `gest_agri.plot` :

| Groupe | Opérations | Domaine |
|---|---|---|
| `group_gest_agri_user` | `r` | `[('farm_id', 'in', user.gest_agri_farm_ids.ids)]` |
| `group_gest_agri_manager` | `cu` | `[('farm_id', 'in', user.gest_agri_managed_farm_ids.ids)]` |
| `group_gest_agri_admin` | `crud` | `[('company_id', 'in', company_ids)]` |

Ainsi un utilisateur ne voit que les cultures des exploitations auxquelles il a
accès ; un responsable ne crée/modifie que sur les exploitations qu'il gère.

---

# 8. DÉCISIONS MÉTIER ENCORE NÉCESSAIRES

| # | Décision | Options | Impact | Bloquant pour phase 1 ? |
|---|---|---|---|---|
| 1 | Campagne : une par an ou plusieurs ? | unique annuelle / multiples | unicité, UI, coûts | **Non** si `campaign_id` différé |
| 2 | Rattachement campagne obligatoire ? | obligatoire / optionnel | validation, migration | Non en phase 1 |
| 3 | Cultures associées / secondaires ? | interdites / autorisées | contredit la règle 05, champ `crop_role` | Non (recommandation : interdites) |
| 4 | Chevauchement au jour près | inclusif / semi-ouvert | contrainte de chevauchement | Oui, à trancher avant codage |
| 5 | Cycles archivés dans le contrôle de chevauchement | inclus / exclus | historique | Oui (recommandation : inclus) |
| 6 | Surface de la culture | pleine parcelle / partielle | champ `area_ha` | Non (champ optionnel) |
| 7 | Date de semis réelle distincte de la prévue | oui / non | champ supplémentaire, workflow | Non |
| 8 | Granularité des états | 4 ou 5 états | workflow | Oui, à confirmer |
| 9 | Variété obligatoire ou facultative | requis / optionnel | saisie | Non (recommandation : facultative) |
| 10 | `crop_type_id` sur la parcelle | conserver tel quel / requalifier en « vocation » | libellé, aide, formation | Non (conservé tel quel) |
| 11 | `btree_gist` pour exclusion SQL | autoriser / différer | intégrité concurrente | Non (différé, INF-10) |
| 12 | Format de numérotation | `CUL/...` | séquence | Non |

---

# 9. ORGANISATION DES FICHIERS PROPOSÉE

## 9.1 Python

```
models/
├── __init__.py                     # + from . import production
├── production/
│   ├── __init__.py                 # from . import crop_cycle
│   └── crop_cycle.py               # GestAgriCropCycle
└── patrimony/
    └── plot.py                     # + crop_cycle_ids, count éventuel
```

## 9.2 XML

```
views/
├── production_views.xml            # list, form, search, action
└── patrimony_views.xml             # + onglet « Cultures » sur la parcelle
views/menu_views.xml                # + menuitem sous Production végétale
data/sequences.xml                  # + séquence gest_agri.crop.cycle
__manifest__.py                     # + views/production_views.xml
```

## 9.3 Sécurité

```
security/ir.access.csv              # + 3 lignes ACL pour crop.cycle
```

## 9.4 Tests

```
tests/
├── __init__.py                     # + from . import test_crop_cycle
├── test_crop_cycle.py              # tests fonctionnels
└── test_security.py                # + tests d'isolation crop.cycle
```

---

# 10. DÉCOUPAGE RECOMMANDÉ DES PROCHAINS PROMPTS

| Prompt | Contenu | Justification |
|---|---|---|
| **50** | **Modèle `gest_agri.crop.cycle`** : champs de base, contraintes de dates, cohérence variété/type, chevauchement Python, index unique `(plot_id, date_start)`, ACL, vues liste/formulaire/recherche, menu, onglet sur la parcelle, séquence, tests. | Première brique opérationnelle demandée ; aucune dépendance à la campagne. |
| **51** | Modèle minimal `gest_agri.campaign` (nom, code, dates, société, état, notes, `active`) + ACL + vues + menu. | Prépare le rattachement sans figer la granularité (plusieurs campagnes autorisées). |
| **52** | Ajout de `campaign_id` (nullable) sur `crop.cycle`, domaine et cohérence société, affichage et filtres. | Migration additive sans rupture. |
| **53** | Contrainte d'exclusion SQL `btree_gist` (si autorisée) + tests de concurrence. | Renforce l'intégrité temporelle jusqu'ici garantie en Python. |
| **54** | Modèle `gest_agri.intervention` (opérations : semis, fertilisation, traitement, irrigation). | Suite du processus 03. |
| **55** | Modèle `gest_agri.harvest` (récolte, quantité, qualité, rendement). | Suite du processus 03 et calculs de rendement. |

Chaque prompt reste une petite brique, testable et réplicable sur `odoo20`.

---

# 11. RECOMMANDATION FINALE

## Première brique à développer : Prompt 50

**Créer `gest_agri.crop.cycle`** avec :

- `name` (séquence), `plot_id`, `farm_id`/`site_id`/`company_id` dérivés ;
- `crop_type_id` (requis), `crop_variety_id` (optionnel, contrôlé) ;
- `date_start` (requis), `date_end_planned`, `date_end_actual` ;
- `state` (`planned`, `planted`, `in_progress`, `done`, `cancelled`) ;
- `area_ha`, `notes`, `active`, `sequence` ;
- contrainte Python de chevauchement + index unique `(plot_id, date_start)` ;
- ACL calquées sur la parcelle, vues liste/formulaire/recherche, menu
  « Production végétale », onglet « Cultures » sur la parcelle ;
- tests fonctionnels et de sécurité.

**Ne pas inclure** `campaign_id`, les interventions, les récoltes ni les cultures
associées dans cette première brique.

## Décisions à valider avant le codage

1. **Chevauchement au jour près** : inclusif ou semi-ouvert ?
2. **Cycles archivés** : bloquent-ils encore un nouveau chevauchement ? (recommandation : oui)
3. **Granularité des états** : 4 ou 5 états ? (recommandation : 5, avec `planted` distinct)
4. **Surface de la culture** : pleine parcelle ou surface partielle saisissable ?
5. **`crop_type_id` de la parcelle** : conservé tel quel (recommandation) ou requalifié en « vocation » ?

Les décisions relatives à la campagne (une ou plusieurs par an, rattachement
obligatoire) peuvent rester ouvertes : elles n'empêchent pas la première brique,
grâce au report de `campaign_id`.

---

*Rapport — Prompt N°49 — Module `gestion_agricole` — Odoo 20 Community.
Étude de conception, sans modification de code, de vue, de manifeste, d'ACL ou
de base de données.*
