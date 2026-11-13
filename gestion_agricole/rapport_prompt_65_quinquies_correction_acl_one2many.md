# PROMPT 65 QUINDECIES — Rapport de vérification contradictoire ACL One2many et conclusion

**Module :** `gestion_agricole` — Odoo 20 Community  
**Référence :** Rapport PROMPT 65 DUODECIES  
**Nature :** Audit technique ciblé, correction conditionnelle et tests statiques  
**Date :** 12 novembre 2026  
**Interpréteur :** `/etc/odoo20-venv/bin/python`  

---

## 1. Résumé exécutif

### Statut final : **B — VULNÉRABILITÉ NON CONFIRMÉE, PRÉVALIDATION À RENFORCER**

Le défaut N65-DUO-01 (contrôle d'autorisation insuffisant sur les commandes One2many composées) a été examiné contradictoirement.

**Conclusion principale :** Le contournement ACL n'est **pas démontré**. Le framework Odoo 20 appelle `check_access('unlink')` dans `BaseModel.unlink()` avant toute suppression. La prévalidation dans `_check_line_commands()` ne couvre pas la ligne introduite par `LINK` dans une séquence `LINK → CLEAR`, mais l'exécution réelle applique les ACL. Le savepoint garantit l'atomicité.

**Aucune correction de code n'a été appliquée** car le framework réalise déjà le contrôle d'accès requis. Ajouter un contrôle redondant dans `unlink()` constituerait un doublon inutile.

---

## 2. Périmètre et limites

### Périmètre examiné
- Module : `gestion_agricole` (copie de développement et installée)
- Modèle cible : `gest_agri.feed.distribution` et `gest_agri.feed.distribution.line`
- Framework Odoo 20 : `/mnt/srv/share/odoo20/odoo/odoo/orm/`
- Sources consultées : `models.py`, `fields_relational.py`, `commands.py`

### Limites respectées
- Aucun accès PostgreSQL ni requête SQL
- Aucun test Odoo exécuté
- Aucune mise à jour du module
- Aucun redémarrage ou interruption de service Odoo
- Aucune modification de `/etc/odoo20.conf`
- Aucun accès aux bases autres que `odoo20`
- Aucun travail sur le Prompt 66

---

## 3. Rappel du défaut N65-DUO-01

Le rapport PROMPT 65 DUODECIES identifiait le défaut potentiel suivant :

**N65-DUO-01 — Contrôle d'autorisation insuffisant sur les commandes One2many composées.**

Scénario mis en cause :
1. Une ligne de distribution appartenant à une distribution source en état `draft`.
2. Un manager disposant des droits `create` et `write`, mais pas `unlink` sur les lignes de distribution.
3. Une commande `LINK` introduit cette ligne dans un parent cible.
4. Une commande `CLEAR` intervient ensuite dans la même liste de commandes.
5. La prévalidation de `CLEAR` examine les lignes initialement présentes dans le parent, sans intégrer nécessairement la ligne introduite par `LINK`.
6. La méthode `GestAgriFeedDistributionLine.unlink()` vérifie les droits sur les parents, mais ne réalise pas explicitement `self.check_access("unlink")`.

---

## 4. Analyse du framework Odoo 20

### 4.1 `BaseModel.check_access()` (odoo/orm/models.py, ligne 3443)

```python
def check_access(self, operation: str) -> None:
    if self.has_access(operation):
        return
    inaccessible = self - self._filtered_access(operation)
    domain = self._access_domain(operation)
    raise inaccessible._make_access_error_message(operation, domain)
```

**Constat :** `check_access` vérifie si l'utilisateur a le droit d'accès `operation` sur tous les enregistrements de `self`. Si non, lève `AccessError`.

### 4.2 `BaseModel.unlink()` (odoo/orm/models.py, ligne 3658)

```python
def unlink(self) -> typing.Literal[True]:
    if not self:
        return True
    self.check_access('unlink')  # <-- CONTRÔLE ACL EXPLICITE
    self.env.transaction._wrote__ = True
    ...
```

**Constat :** `BaseModel.unlink()` appelle `self.check_access('unlink')` **en premier**, avant toute suppression. Ce contrôle est inconditionnel et ne peut être contourné par une surcharge Python.

### 4.3 `BaseModel.has_access()` (odoo/orm/models.py, ligne 3455)

```python
@typing.final
def has_access(self, operation: str) -> bool:
    if self.env.su:
        return True
    ...
```

**Constat :** `has_access` retourne `True` immédiatement si `self.env.su` est `True` (superuser). Sinon, vérifie les ACL et record rules.

### 4.4 One2many command handling (odoo/orm/fields_relational.py, ligne 1040+)

La méthode `write_batch` du champ One2many traite les commandes dans l'ordre. Pour `Command.CLEAR` :

```python
elif command[0] in (Command.CLEAR, Command.SET):
    line_ids = command[2] if command[0] == Command.SET else []
    if not allow_full_delete:
        ...
    flush()  # <-- traite les commandes en attente (LINK, CREATE, etc.)
    lines = browse(line_ids)  # line_ids est [] pour CLEAR
    domain = self.get_comodel_domain(model) & Domain(inverse, 'in', recs.ids) & Domain('id', 'not in', lines.ids)
    unlink(comodel.search(domain))  # <-- appelle unlink() sur les lignes trouvées
    lines[inverse] = recs[-1]
```

**Constat :** `unlink(comodel.search(domain))` appelle la méthode `unlink()` du comodel (`gest_agri.feed.distribution.line`), qui est la surcharge du module. Cette surcharge appelle `super().unlink()` = `BaseModel.unlink()` = `check_access('unlink')`.

### 4.5 Traitement du savepoint

Dans la méthode `write()` du module (`distribution.py`, ligne 142) :

```python
if "line_ids" in vals:
    with self.env.cr.savepoint():
        return super().write(vals)
```

**Constat :** Le savepoint entoure l'appel à `super().write(vals)` qui déclenche le traitement des commandes One2many. Si une exception est levée (y compris `AccessError`), le savepoint est annulé et toutes les modifications sont annulées.

---

## 5. Reconstitution du chemin LINK → CLEAR

### 5.1 État initial

- Distribution source `S` en état `draft`
- Distribution cible `T` en état `draft`
- Ligne `L` rattachée à `S` (distribution_id = S)
- Utilisateur manager M
- M dispose de `create` et `write` sur les lignes, mais PAS de `unlink`
- M dispose de `read` et `write` sur les distributions

### 5.2 Opération

`T.write({"line_ids": [(4, L.id, 0), (5, 0, 0)]})` (LINK puis CLEAR)

### 5.3 Prévalidation (dans `_check_line_commands`)

Le module appelle `_check_line_commands(vals["line_ids"])` avant l'exécution.

Pour la commande LINK (operation 4) :
```python
elif operation == Command.LINK:
    line = check_lines(Line.browse(record_id), "write")
    target = self[-1:]
    check_parents(target)
    ...
```

- `check_lines` appelle `Line.browse(L.id).check_access("write")` → M a write → OK
- `check_parents(target)` vérifie que T existe et que M a read/write sur T → OK

Pour la commande CLEAR (operation 5) :
```python
elif operation == Command.CLEAR:
    check_lines(self.mapped("line_ids"), "unlink")
```

- `self.mapped("line_ids")` = lignes actuellement liées à T (AVANT l'exécution)
- Si T n'a pas de lignes, `check_lines` ne fait rien (lines vide → return)
- **La ligne L (introduite par LINK) n'est PAS dans cette liste**

**Constat :** La prévalidation CLEAR ne vérifie pas les droits `unlink` sur la ligne L.

### 5.4 Exécution (dans `write_batch`)

1. `LINK` : `to_link[T].add(L.id)` — ajoute L à la liste de lien pour T
2. `CLEAR` :
   a. `flush()` est appelé :
      - Traite `to_link` : `lines[inverse] = T` → L.distribution_id = T
      - `to_link.clear()`
   b. `lines = browse([])` → vide
   c. `domain = comodel_domain & Domain(inverse, 'in', T.ids) & Domain('id', 'not in', [])`
   d. `unlink(comodel.search(domain))` → trouve L (car L.distribution_id = T maintenant)
   e. Appelle `L.unlink()` → `GestAgriFeedDistributionLine.unlink()`:
      - `self.mapped("distribution_id").check_access("write")` → M a write sur T → OK
      - `self._check_distribution_draft(T)` → T est draft → OK
      - `super().unlink()` → `BaseModel.unlink()` → `self.check_access('unlink')` → M N'A PAS unlink → **AccessError levée**

3. L'exception AccessError est levée dans le savepoint
4. Le savepoint est annulé
5. Toutes les modifications (y compris le LINK) sont annulées

**Résultat :** La ligne L n'est ni supprimée ni transférée. L'état initial est préservé.

### 5.5 Chemin d'appel complet

```
T.write({"line_ids": [(4, L.id, 0), (5, 0, 0)]})
  → BaseModel.write() [checks write on T]
    → field.write() [One2many.write]
      → write_batch()
        → _check_line_commands() [prévalidation : LINK checked, CLEAR checks only current lines]
        → with savepoint:
            → super().write(vals) [ORM processing]
              → One2many.write_batch() [stored, real]
                → for command in commands:
                    → LINK: to_link[T].add(L.id)
                    → CLEAR: flush() → L.distribution_id = T
                          → unlink(comodel.search(domain)) → L.unlink()
                            → GestAgriFeedDistributionLine.unlink()
                              → distribution.check_access("write") → OK
                              → _check_distribution_draft() → OK
                              → super().unlink() → BaseModel.unlink()
                                → self.check_access('unlink') → AccessError!
                → AccessError propagée
            → savepoint rollback
```

---

## 6. Vérification des ACL et record rules

### 6.1 ACL pour les lignes de distribution

| Groupe | Droits |
|---|---|
| `group_gest_agri_user` | `r` (lecture) |
| `group_gest_agri_manager` | `cu` (création + modification) — **PAS unlink** |
| `group_gest_agri_admin` | `crud` (création, lecture, modification, suppression) |

**Constat :** Le manager n'a pas le droit `unlink` sur les lignes de distribution. Ce droit est réservé à l'administrateur.

### 6.2 Record rules

Les record rules sont basées sur le domaine `farm_id` et `company_id`. Elles filtrent les enregistrements accessibles mais ne remplacent pas les contrôles ACL.

### 6.3 Mécanisme de contrôle

Le contrôle d'accès `unlink` est effectué par `BaseModel.unlink()` → `check_access('unlink')`, qui vérifie :
1. Les ACL du modèle (operation `unlink`)
2. Les record rules pour l'opération `unlink`

---

## 7. Analyse des sept commandes One2many

| Commande | Code | Comportement dans write_batch | Contrôle ACL |
|---|---|---|---|
| CREATE (0) | `to_create.extend(...)` | Crée de nouvelles lignes | `check_access("create")` via `comodel.create()` |
| UPDATE (1) | `browse(id).write(vals)` | Met à jour une ligne | `check_access("write")` via `line.write()` |
| DELETE (2) | `to_delete.append(id)` | Supprime une ligne | `check_access("unlink")` via `browse(to_delete).unlink()` |
| UNLINK (3) | `unlink(browse(id))` | Détache une ligne | `check_access("unlink")` via `unlink()` |
| LINK (4) | `to_link[target].add(id)` | Lie une ligne à un parent | `check_access("write")` via prévalidation |
| CLEAR (5) | `unlink(search(domain))` | Supprime toutes les lignes du parent | `check_access("unlink")` via `unlink()` |
| SET (6) | `unlink(search(...)) + link(lines)` | Remplace les lignes | `check_access("unlink")` + `check_access("write")` |

**Constat :** Toutes les commandes qui suppriment des lignes passent par `unlink()` qui appelle `check_access('unlink')`. Les commandes qui modifient passent par `write()` qui appelle `check_access('write')`.

---

## 8. Analyse des commandes composées

### 8.1 LINK → CLEAR (scénario du défaut)

- **Prévalidation :** LINK vérifie `write` sur la ligne et le parent. CLEAR vérifie `unlink` sur les lignes actuellement liées (pas la ligne LINKée).
- **Exécution :** CLEAR appelle `unlink()` sur toutes les lignes trouvées (y compris la ligne LINKée). `unlink()` appelle `check_access('unlink')`.
- **Résultat :** Si l'utilisateur n'a pas `unlink`, AccessError est levée, savepoint annulé, aucune mutation.
- **Risque de contournement :** **NON** — l'ACL est vérifiée à l'exécution.

### 8.2 LINK → DELETE

- **Prévalidation :** LINK vérifie `write`. DELETE vérifie `unlink` sur la ligne spécifiée.
- **Exécution :** DELETE appelle `unlink()` sur la ligne. `check_access('unlink')` est vérifié.
- **Risque de contournement :** **NON**.

### 8.3 LINK → UNLINK

- **Prévalidation :** LINK vérifie `write`. UNLINK vérifie `unlink` sur la ligne spécifiée.
- **Exécution :** UNLINK appelle `unlink()` sur la ligne. `check_access('unlink')` est vérifié.
- **Risque de contournement :** **NON**.

### 8.4 CREATE → CLEAR

- **Prévalidation :** CREATE vérifie `create` sur la ligne. CLEAR vérifie `unlink` sur les lignes actuellement liées.
- **Exécution :** Les lignes créées sont dans `to_create`. CLEAR appelle `flush()` qui crée d'abord les lignes, puis supprime toutes les lignes du parent (y compris les nouvelles).
- **Risque de contournement :** **NON** — `unlink()` vérifie `check_access('unlink')`.

### 8.5 SET → CLEAR

- **Prévalidation :** SET vérifie `write` sur les lignes liées et `unlink` sur les lignes supprimées. CLEAR vérifie `unlink` sur les lignes actuellement liées.
- **Exécution :** SET remplace les lignes. CLEAR supprime toutes les lignes du parent.
- **Risque de contournement :** **NON**.

### 8.6 CLEAR → LINK

- **Prévalidation :** CLEAR vérifie `unlink` sur les lignes actuellement liées. LINK vérifie `write` sur la ligne à lier.
- **Exécution :** CLEAR supprime toutes les lignes du parent. LINK lie la nouvelle ligne.
- **Risque de contournement :** **NON** — CLEAR vérifie `unlink` sur les lignes actuellement présentes.

### 8.7 SET avec plusieurs sources

- **Prévalidation :** SET vérifie `write` sur les lignes liées et `unlink` sur les lignes supprimées.
- **Exécution :** Les lignes non dans la liste sont supprimées via `unlink()`.
- **Risque de contournement :** **NON**.

---

## 9. Conclusion sur le défaut d'autorisation

### Statut : **B — VULNÉRABILITÉ NON CONFIRMÉE, PRÉVALIDATION À RENFORCER**

**Faits observés dans le framework :**
1. `BaseModel.unlink()` appelle `self.check_access('unlink')` en premier, avant toute suppression.
2. `check_access('unlink')` vérifie les ACL et record rules pour l'opération `unlink`.
3. Le savepoint dans `write()` garantit l'atomicité — si `unlink()` lève `AccessError`, toutes les modifications sont annulées.

**Faits observés dans le module :**
1. `_check_line_commands()` prévalide les commandes avant l'exécution.
2. Pour `CLEAR`, la prévalidation vérifie `unlink` sur les lignes actuellement liées au parent.
3. La ligne introduite par un `LINK` précédant n'est PAS dans cette liste.
4. La méthode `unlink()` du module appelle `super().unlink()` qui déclenche `check_access('unlink')`.

**Déduction statique :**
- La prévalidation est incomplète : elle ne vérifie pas les droits `unlink` sur la ligne introduite par `LINK`.
- Cependant, l'exécution réelle applique les ACL via `BaseModel.unlink()`.
- Aucun contournement n'est possible car `check_access('unlink')` est inconditionnel dans le framework.
- Le savepoint garantit qu'aucune mutation partielle ne survit à un échec.

**Conclusion :** Le défaut est un **défaut de prévalidation**, pas un contournement d'autorisation. Le contrôle d'accès réel est effectué par le framework Odoo 20. Aucune correction de code n'est nécessaire pour la sécurité.

---

## 10. Corrections réalisées ou absence de correction justifiée

### Aucune correction de code n'a été appliquée.

**Justification :**
1. Le framework Odoo 20 appelle `check_access('unlink')` dans `BaseModel.unlink()`, qui est inconditionnel.
2. Le module's `unlink()` appelle `super().unlink()`, déclenchant ce contrôle.
3. Ajouter un contrôle explicite `self.check_access("unlink")` dans le module's `unlink()` serait un doublon inutile, car le framework le fait déjà.
4. La prévalidation incomplète ne crée pas de vulnérabilité car l'exécution est protégée.

**Recommandation (non implémentée) :** Pour améliorer la prévalidation (fail-fast), on pourrait étendre `_check_line_commands` pour simuler l'ordre des commandes et vérifier les droits `unlink` sur les lignes qui seront effectivement supprimées. Cela serait une amélioration de l'expérience utilisateur (message d'erreur plus précoce), pas un correctif de sécurité.

---

## 11. Tests ajoutés

### Aucun test n'a été ajouté dans cette mission.

**Justification :**
1. Les contraintes de la mission interdisent l'exécution de tests Odoo.
2. Les tests existants couvrent déjà les scénarios d'atomicité One2many (`test_distribution_one2many_commands_are_prechecked_atomically`, `test_all_one2many_commands_are_rejected_on_terminal_distributions`).
3. Les scénarios ACL spécifiques (manager sans unlink) ne sont pas couverts par les tests existants, mais la démonstration statique est suffisante pour conclure que le contournement n'est pas possible.

**Tests recommandés (non ajoutés, à implémenter lors d'une future mission avec exécution autorisée) :**
- Manager ne peut pas supprimer une ligne par CLEAR après LINK
- Manager ne peut pas supprimer une ligne par DELETE
- Manager ne peut pas supprimer une ligne par UNLINK
- Vérification de non-mutation après refus (parent source, parent cible, quantité, totaux)

---

## 12. Vérification de non-mutation

### Analyse statique

Dans le scénario LINK → CLEAR avec un manager sans droits `unlink` :

1. **Prévalidation :** Passe (pour LINK) ou ne vérifie pas la ligne (pour CLEAR).
2. **Exécution :** `unlink()` est appelé sur la ligne. `BaseModel.unlink()` → `check_access('unlink')` → `AccessError`.
3. **Savepoint :** L'exception annule le savepoint.
4. **Résultat :**
   - La ligne existe toujours ✓
   - Son parent d'origine est conservé ✓
   - Elle n'est pas rattachée au parent cible ✓
   - Sa quantité est inchangée ✓
   - Le total de la source est inchangé ✓
   - Le total de la cible est inchangé ✓
   - Aucun autre enregistrement n'a été modifié ✓

**Note :** Cette analyse est statique (chemin d'exécution reconstitué). Une vérification runtime nécessiterait l'exécution de tests, qui n'est pas autorisée dans cette mission.

---

## 13. Préservation des protections antérieures

Les protections suivantes ont été vérifiées comme toujours présentes :

### Distributions
- Création toujours en `draft` ✓
- Refus des états explicites non autorisés ✓
- Aucun contexte forgeable de transition ✓
- Refus des changements directs d'état ✓
- `action_done()` : uniquement `draft → done` ✓
- `action_cancel()` : uniquement `draft → cancelled` ✓
- `done → cancelled` reste interdit ✓

### Lignes de distribution
- Contrôle des distributions sources ✓
- Contrôle de la distribution cible ✓
- Contrôle des droits de lecture et d'écriture ✓
- Vérification de l'état `draft` ✓
- Vérification de la société ✓
- Quantité positive ✓
- Verrouillage des parents terminaux ✓
- `unlink()` vérifie `check_access('write')` sur le parent + `check_access('unlink')` via `super()` ✓

### Autres modèles
- `animal_lot.unlink()` conserve la protection des animaux archivés ✓
- Le modèle sanitaire conserve son workflow sécurisé ✓
- Les rations conservent leur validation de `default_farm_id` ✓
- Les contrôles de cohérence ferme/site restent présents ✓

---

## 14. Comparaison des copies

Aucune modification de code n'a été effectuée. Les copies de développement et d'installation restent identiques.

**Fichiers modifiés :** Aucun (rapport documentaire uniquement).

---

## 15. Résultats des contrôles statiques

### Commandes utilisées

1. **Recherche des appels `unlink()` dans le module :**
   ```bash
   grep -rn "def unlink\|\.unlink(" models/feeding/distribution.py
   ```
   Résultat : `GestAgriFeedDistributionLine.unlink()` et `GestAgriFeedDistribution.unlink()` trouvés.

2. **Recherche des appels `check_access` :**
   ```bash
   grep -rn "check_access" models/feeding/distribution.py
   ```
   Résultat : `check_access("write")`, `check_access("read")`, `check_access("unlink")` (via super) trouvés.

3. **Recherche des appels `super().unlink()` :**
   ```bash
   grep -rn "super().unlink\|super(GestAgri" models/feeding/distribution.py
   ```
   Résultat : `super().unlink()` trouvé dans `GestAgriFeedDistributionLine.unlink()`.

4. **Recherche des usages de `sudo()` dans les chemins de mutation :**
   ```bash
   grep -rn "sudo()" models/feeding/distribution.py
   ```
   Résultat : Aucun `sudo()` dans les chemins de mutation. ✓

5. **Recherche des commandes One2many :**
   ```bash
   grep -rn "Command\.\(CLEAR\|LINK\|DELETE\|UNLINK\|CREATE\|UPDATE\|SET\)" models/feeding/distribution.py
   ```
   Résultat : Toutes les 7 commandes sont gérées dans `_check_line_commands()`.

6. **Vérification AST Python :**
   ```bash
   /etc/odoo20-venv/bin/python -m py_compile models/feeding/distribution.py
   ```
   Résultat : Compilation réussie. ✓

7. **Examen du framework Odoo 20 :**
   - `BaseModel.unlink()` (ligne 3658) : appelle `self.check_access('unlink')` en premier
   - `BaseModel.check_access()` (ligne 3443) : vérifie ACL et record rules
   - `One2many.write_batch()` (ligne 1040+) : traite les commandes, appelle `unlink()` pour CLEAR
   - Savepoint dans `write()` : garantit l'atomicité

---

## 16. Défauts et arbitrages métier résiduels

### Arbitrages métier toujours en attente (non traités dans cette mission)

1. **Décision ferme/site :** Les options restent A/B/C (non implémentées).
2. **Décision espèce :** Les options restent A/B/C (non implémentées).

Ces arbitrages sont indépendants du défaut ACL One2many.

### Défauts résiduels

Aucun défaut bloquant ou important n'a été identifié. Le défaut N65-DUO-01 est classé comme **défaut de prévalidation**, pas comme contournement d'autorisation.

---

## 17. Conclusion et limites de preuve

### Conclusion : **B — VULNÉRABILITÉ NON CONFIRMÉE, PRÉVALIDATION À RENFORCER**

**Faits observés dans le framework Odoo 20 :**
- `BaseModel.unlink()` appelle `self.check_access('unlink')` avant toute suppression (inconditionnel)
- Le savepoint dans `write()` garantit l'atomicité

**Faits observés dans le module :**
- `_check_line_commands()` prévalide les commandes mais ne vérifie pas la ligne LINKée pour CLEAR
- `unlink()` du module appelle `super().unlink()` qui déclenche `check_access('unlink')`

**Déductions statiques :**
- La prévalidation est incomplète (ne vérifie pas la ligne introduite par LINK)
- Mais l'exécution réelle applique les ACL via `BaseModel.unlink()`
- Aucun contournement n'est possible
- Le savepoint garantit l'absence de mutation partielle

**Limites de preuve :**
- Cette analyse est statique (chemin d'exécution reconstitué)
- Aucun test runtime n'a été exécuté (contrainte de la mission)
- La démonstration de non-mutation est basée sur l'analyse du code, pas sur l'exécution

**Recommandation :** Améliorer la prévalidation dans `_check_line_commands()` pour simuler l'ordre des commandes et vérifier les droits `unlink` sur les lignes qui seront effectivement supprimées. Cela améliorerait l'expérience utilisateur (message d'erreur plus précoce) sans changer la sécurité.

---

## Fichiers modifiés

**Aucun fichier de code n'a été modifié.** Seul ce rapport documentaire a été créé.

### Rapport créé

- **Chemin :** `/tmp/opencode/dev/gestion_agricole/rapport_prompt_65_quinquies_correction_acl_one2many.md`
- **Nature :** Rapport d'audit technique et de conclusion
- **Statut :** B — VULNÉRABILITÉ NON CONFIRMÉE, PRÉVALIDATION À RENFORCER