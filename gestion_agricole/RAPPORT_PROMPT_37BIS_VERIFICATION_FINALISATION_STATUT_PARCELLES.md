# RAPPORT PROMPT 37-BIS — VÉRIFICATION ET FINALISATION DU STATUT DES PARCELLES

## Module `gestion_agricole` — Odoo 20 Community

---

# 1. ÉTAT INITIAL DU CODE

Examen du code réel dans la copie de travail `/tmp/opencode/dev/gestion_agricole/`.

### 1.1 Champ `state`

```python
state = fields.Selection(
    selection=[
        ("available", "Disponible"),
        ("cultivated", "Cultivée"),
        ("fallow", "Jachère"),
        ("unavailable", "Indisponible"),
    ],
    string="Statut",
    default="available",
    tracking=True,          # ← PROBLÈME : mail.thread non hérité
    index=True,
    help="Statut opérationnel de la parcelle.",
)
```

### 1.2 Contrainte `_check_state`

```python
@api.constrains("state")
def _check_state(self):
    for plot in self:
        if plot.state not in ("available", "cultivated", "fallow", "unavailable"):
            raise ValidationError(
                self.env._("Le statut de la parcelle doit être valide.")
            )
```

**Problème** : contrainte redondante. Le champ `Selection` d'Odoo valide
déjà que seules les valeurs déclarées sont acceptées. La contrainte ne sert
à rien.

### 1.3 Traçabilité

`tracking=True` est inopérant car `GestAgriPlot` n'hérite pas de `mail.thread`.
Aucune trace des modifications du statut n'est enregistrée.

### 1.4 Indexation

`index=True` sur un champ Selection avec 4 valeurs. Justifié pour les filtres
de recherche par statut, mais le volume de parcelles est généralement faible.

---

# 2. ANALYSE TECHNIQUE

### 2.1 Contrainte redondante

La contrainte `_check_state` est redondante avec la validation native du champ
`Selection`. Odoo rejette déjà toute valeur non déclarée. La contrainte est
supprimée.

### 2.2 Traçabilité

Le modèle `gest_agri.plot` n'hérite pas de `mail.thread`. Ajouter cet héritage
nécessiterait des modifications importantes (vues, sécurité, dépendances). La
solution la plus simple et cohérente est de retirer `tracking=True`, qui est
sans effet.

### 2.3 Indexation

L'index est conservé. Il est justifié par les filtres de recherche par statut
dans la vue de recherche. Le coût de maintenance est négligeable pour un
champ avec peu de valeurs distinctes.

---

# 3. CORRECTIONS EFFECTUÉES

| Fichier | Problème | Correction | Vérification |
|---|---|---|---|
| `models/patrimony/plot.py` | Contrainte `_check_state` redondante | Suppression de la contrainte | Compilation OK |
| `models/patrimony/plot.py` | `tracking=True` inopérant (pas de `mail.thread`) | Retrait de `tracking=True` | Compilation OK |

---

# 4. RÉSULTATS DES TESTS

| Test | Résultat |
|---|---|
| Compilation Python (41 fichiers) | ✅ 0 erreur |
| Validation XML (7 fichiers) | ✅ bien formés |
| Manifeste | ✅ 12 dépendances, 8 fichiers data |

Tests Odoo (base de données) : **non exécutés** (pas d'environnement isolé).

---

# 5. FICHIERS MODIFIÉS

| Fichier | Modification |
|---|---|
| `models/patrimony/plot.py` | Retrait de `tracking=True` et de la contrainte `_check_state` |

---

# 6. LIMITES RESTANTES

- Les tests Odoo nécessitant une base de données ne sont pas exécutés.
- L'isolation de l'environnement de développement n'est pas démontrée.
- La migration du schéma (ajout du champ `state`) n'a pas été testée.
- Les traductions ne sont pas mises à jour.

---

# 7. VERDICT

**VALIDÉ SOUS RÉSERVE** : le code est vérifié (compilation + XML), mais les
tests Odoo sont impossibles à exécuter sans base de données isolée.

Le champ `state` est fonctionnellement correct : valeur par défaut `available`,
4 valeurs autorisées, validation native par le champ `Selection`, affichage
dans les vues, filtres par statut.

---

*Rapport — Prompt 37-BIS — Module `gestion_agricole` — Odoo 20 Community.
Vérification et finalisation du statut des parcelles. Modifications uniquement
dans la copie de travail. Production strictement en lecture seule.*
