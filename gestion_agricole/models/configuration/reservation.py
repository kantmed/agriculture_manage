# -*- coding: utf-8 -*-
"""Réservation d'unicité des référentiels de configuration.

Ce mécanisme matérialise la règle d'unicité la plus stricte du module :

* un **code global** est réservé à **toutes** les sociétés ;
* un **code de société** est réservé dans sa société et doit aussi respecter les
  codes globaux ;
* deux sociétés différentes peuvent utiliser le même code ;
* un **nom global** peut coexister avec un nom de société identique ;
* deux noms globaux identiques sont interdits ;
* seuls les enregistrements **actifs** participent à l'unicité.

Le mécanisme repose sur une contrainte d'exclusion PostgreSQL
``EXCLUDE USING gist`` portant sur un périmètre de type ``int8range`` :

| Situation               | Périmètre (scope)      | Domaine     |
|-------------------------|------------------------|-------------|
| Code global             | ``int8range(1, NULL)`` | positif     |
| Code de société ``c``   | ``int8range(c, c+1)``  | positif     |
| Nom global              | ``int8range(-1, 0)``   | **négatif** |
| Nom de société ``c``    | ``int8range(c, c+1)``  | positif     |

Les domaines sont disjoints **par construction** : le périmètre négatif réservé
aux noms globaux ne peut jamais chevaucher une société (dont l'identifiant est
toujours >= 1), et le périmètre global des codes couvre tout le domaine positif.

Robustesse sous ``REPEATABLE READ`` : une contrainte d'exclusion s'appuie sur le
même mécanisme d'insertion spéculative que les index uniques PostgreSQL — la
transaction concurrente attend, puis le conflit est détecté à la validation. Ce
mécanisme est **indépendant de l'instantané de lecture**, contrairement au verrou
consultatif suivi d'une recherche ORM.

Choix d'architecture : la table de réservation est une **table technique gérée en
SQL brut**, et non un modèle Odoo. Deux raisons :

1. le type ``int8range`` n'a pas d'équivalent parmi les champs Odoo 20 ; la
   contrainte d'exclusion porte donc sur l'expression
   ``(int8range(scope_lo, scope_hi))`` ;
2. la table n'est créée que si l'extension ``btree_gist`` est **déjà** installée
   dans la base. Son installation est une décision opérationnelle explicite
   (``CREATE EXTENSION btree_gist``) : tant qu'elle n'a pas été prise, le
   mécanisme reste **inerte** et la base n'est **pas** modifiée. Aucun modèle
   Odoo n'est déclaré, donc aucun rechargement de registre ne peut créer la
   table par effet de bord.
"""
import logging

import psycopg2

from odoo import api
from odoo.exceptions import ValidationError
from ._common import normalize_reference, reference_scope

_logger = logging.getLogger(__name__)

#: Nom de la table technique de réservation.
RESERVATION_TABLE = "gest_agri_reference_reservation"
#: Nom de la contrainte d'exclusion.
RESERVATION_CONSTRAINT = f"{RESERVATION_TABLE}_scope_exclusion"

#: Modèles de référentiels concernés, dans l'ordre du remplissage.
REFERENCE_MODELS = [
    "gest_agri.farm.type",
    "gest_agri.soil.type",
    "gest_agri.crop.type",
    "gest_agri.crop.variety",
    "gest_agri.livestock.species",
    "gest_agri.livestock.breed",
    "gest_agri.operation.type",
    "gest_agri.treatment.type",
    "gest_agri.fertilizer.type",
    "gest_agri.irrigation.type",
    "gest_agri.equipment.type",
    "gest_agri.building.type",
    "gest_agri.production.type",
]


# ----------------------------------------------------------------------
# Utilitaires base de données
# ----------------------------------------------------------------------
def _extension_present(cr):
    """L'extension PostgreSQL ``btree_gist`` est-elle installée ?"""
    cr.execute("SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")
    return bool(cr.fetchone())


def _constraint_present(cr):
    """La contrainte d'exclusion est-elle en place ?

    ``to_regclass`` est utilisé (et non ``::regclass``) afin que l'absence
    de la table ne provoque pas une erreur : la table n'existe que si le
    mécanisme a été activé.
    """
    cr.execute(
        "SELECT 1 FROM pg_constraint "
        "WHERE conname = %s AND conrelid = to_regclass(%s)",
        (RESERVATION_CONSTRAINT, RESERVATION_TABLE),
    )
    return bool(cr.fetchone())


def _reservation_active(cr):
    """Le mécanisme de réservation est-il actif dans cette base ?

    Vrai si (et seulement si) la contrainte d'exclusion existe : c'est
    l'indicateur qui garantit que la table et son index sont utilisables.
    """
    return _constraint_present(cr)


def _create_table(cr):
    """Crée la table technique et son index de recherche (idempotent)."""
    cr.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RESERVATION_TABLE} (
            id         serial PRIMARY KEY,
            model_name varchar NOT NULL,
            kind       varchar NOT NULL,
            normalized varchar NOT NULL,
            scope_lo   bigint  NOT NULL,
            scope_hi   bigint
        )
        """
    )
    cr.execute(
        f"""
        CREATE INDEX IF NOT EXISTS {RESERVATION_TABLE}_lookup_idx
            ON {RESERVATION_TABLE} (model_name, kind, normalized)
        """
    )


def _insert_reservations(cr, keys):
    """Insère les réservations (peut lever une ExclusionViolation)."""
    for model_name, kind, normalized, scope_lo, scope_hi in keys:
        cr.execute(
            f"""
            INSERT INTO {RESERVATION_TABLE}
                (model_name, kind, normalized, scope_lo, scope_hi)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (model_name, kind, normalized, scope_lo, scope_hi),
        )


def _release_reservations(cr, keys):
    """Libère les réservations indiquées."""
    for model_name, kind, normalized, scope_lo, scope_hi in keys:
        cr.execute(
            f"""
            DELETE FROM {RESERVATION_TABLE}
            WHERE model_name = %s AND kind = %s AND normalized = %s
              AND scope_lo = %s AND scope_hi IS NOT DISTINCT FROM %s
            """,
            (model_name, kind, normalized, scope_lo, scope_hi),
        )


# ----------------------------------------------------------------------
# Clés de réservation
# ----------------------------------------------------------------------
def _record_keys(record):
    """Clés réservées par un enregistrement actif.

    Un enregistrement archivé ne réserve aucune clé : seules les
    enregistrements actifs participent à l'unicité.
    """
    keys = []
    if not record.active:
        return keys
    for kind in ("code", "name"):
        value = record[kind]
        if not value:
            continue
        company_id = record.company_id.id or None
        scope_lo, scope_hi = reference_scope(kind, company_id)
        keys.append(
            (
                record._name,
                kind,
                normalize_reference(value),
                scope_lo,
                scope_hi,
            )
        )
    return keys


def _records_keys(records):
    """Clés réservées par un ensemble d'enregistrements."""
    keys = []
    for record in records:
        keys.extend(_record_keys(record))
    return keys


def _conflict_message(kind, value):
    """Message métier français correspondant à un conflit de réservation."""
    if kind == "code":
        return (
            "Le code « %(value)s » est déjà utilisé : un code global le réserve "
            "à toutes les sociétés, ou une autre société l'utilise déjà."
        )
    return "Le nom « %(value)s » est déjà utilisé dans cette société."


# ----------------------------------------------------------------------
# Installation / migration
# ----------------------------------------------------------------------
def setup_reservations(env):
    """Crée la table, reprend les réservations et pose la contrainte.

    Appelé via ``Registry.post_init`` : la reprise s'effectue donc **après**
    l'initialisation de tous les modèles, et **avant** toute création d'enregistrement
    par l'ORM.

    La reprise échoue si un doublon préexiste : la pose de la contrainte
    d'exclusion lève alors une ``ExclusionViolation`` qui annule la transaction
    de mise à jour — aucune donnée n'est modifiée.
    """
    cr = env.cr
    if _constraint_present(cr):
        return
    if not _extension_present(cr):
        _logger.info(
            "gestion_agricole : l'extension PostgreSQL 'btree_gist' n'est pas "
            "installée dans la base %s ; le mécanisme de réservation d'unicité "
            "reste inerte. Pour l'activer : CREATE EXTENSION btree_gist;",
            cr.dbname,
        )
        return

    _create_table(cr)

    # Reprise des réservations existantes, avec exactement la même
    # normalisation que le code applicatif.
    keys = []
    for model_name in REFERENCE_MODELS:
        model = env[model_name]
        cr.execute("SELECT to_regclass(%s) IS NOT NULL", (model._table,))
        if not cr.fetchone()[0]:
            # Table absente (installation en cours) : rien à reprendre.
            continue
        for record in model.with_context(active_test=False).search([]):
            if not record.active:
                continue
            keys.extend(_record_keys(record))
    if keys:
        _insert_reservations(cr, keys)
        _logger.info(
            "gestion_agricole : %s réservation(s) reprise(s) depuis les référentiels",
            len(keys),
        )

    cr.execute(
        f"""
        ALTER TABLE {RESERVATION_TABLE}
            ADD CONSTRAINT {RESERVATION_CONSTRAINT}
            EXCLUDE USING gist (
                model_name WITH =,
                kind WITH =,
                normalized WITH =,
                (int8range(scope_lo, scope_hi)) WITH &&
            )
        """
    )
    _logger.info(
        "gestion_agricole : contrainte d'exclusion %s créée sur %s",
        RESERVATION_CONSTRAINT,
        RESERVATION_TABLE,
    )


class ReferenceReservationMixin:
    """Mixin Python ajoutant la réservation d'unicité aux référentiels.

    Ce mixin n'est pas un modèle Odoo : il ne touche ni aux champs, ni aux index
    uniques déjà en place. Il surcharge ``create``, ``write`` et ``unlink`` afin
    de maintenir les réservations **dans la même transaction** que les
    enregistrements métier.

    Ordre des opérations (identique en création et en modification) :

    1. **libérer** les réservations qui ne sont plus valides ;
    2. **réserver** les nouvelles clés — un conflit est donc détecté *avant*
       toute écriture métier, ce qui permet de renvoyer un message métier
       français plutôt qu'une erreur PostgreSQL brute ;
    3. écrire l'enregistrement métier.

    L'ensemble est exécuté dans un *savepoint* : en cas de conflit, le
    savepoint est annulé, la transaction reste utilisable et l'enregistrement
    métier n'est pas laissé à l'état partiel.
    """

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------
    def init(self):
        """Planifie la mise en place du mécanisme de réservation.

        Le travail est différé à la fin de l'initialisation du registre
        (``Registry.post_init``) : la reprise des réservations doit voir
        l'ensemble des tables de référentiels, y compris celles créées pendant
        l'installation.
        """
        self.env.registry.post_init(setup_reservations, self.env)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _reservation_active(self):
        return _reservation_active(self.env.cr)

    def _projected_company_id(self, vals):
        """Société effective d'un enregistrement en cours d'écriture.

        Reprend l'ordre de résolution d'Odoo : valeur fournie, puis valeur du
        contexte (``default_company_id``), puis valeur par défaut du champ.
        """
        if "company_id" in vals:
            return vals["company_id"] or None
        context_value = self.env.context.get("default_company_id")
        if context_value is not None:
            return context_value or None
        default = self._fields["company_id"].default
        if default is not None:
            value = default(self)
            return value.id if value else None
        return None

    def _projected_keys(self, records, vals):
        """Clés que les enregistrements auront après l'écriture."""
        keys = []
        for record in records:
            active = vals.get("active", record.active)
            if not active:
                continue
            company_id = self._projected_company_id(vals)
            for kind in ("code", "name"):
                value = vals.get(kind, record[kind])
                if not value:
                    continue
                scope_lo, scope_hi = reference_scope(kind, company_id)
                keys.append(
                    (
                        record._name,
                        kind,
                        normalize_reference(value),
                        scope_lo,
                        scope_hi,
                    )
                )
        return keys

    def _projected_keys_for_create(self, vals_list):
        """Clés que les enregistrements à créer auront."""
        keys = []
        for vals in vals_list:
            if not vals.get("active", True):
                continue
            company_id = self._projected_company_id(vals)
            for kind in ("code", "name"):
                value = vals.get(kind)
                if not value:
                    continue
                scope_lo, scope_hi = reference_scope(kind, company_id)
                keys.append(
                    (
                        self._name,
                        kind,
                        normalize_reference(value),
                        scope_lo,
                        scope_hi,
                    )
                )
        return keys

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        if not self._reservation_active():
            return super().create(vals_list)
        with self.env.cr.savepoint():
            self._reserve_keys(self._projected_keys_for_create(vals_list))
            records = super().create(vals_list)
        return records

    def write(self, vals):
        if not self._reservation_active():
            return super().write(vals)
        obsolete = _records_keys(self)
        projected = self._projected_keys(self, vals)
        with self.env.cr.savepoint():
            _release_reservations(
                self.env.cr, [key for key in obsolete if key not in projected]
            )
            self._reserve_keys([key for key in projected if key not in obsolete])
            # write() retourne True : les enregistrements concernés restent self.
            super().write(vals)
        return True

    def unlink(self):
        if not self._reservation_active():
            return super().unlink()
        obsolete = _records_keys(self)
        with self.env.cr.savepoint():
            result = super().unlink()
            _release_reservations(self.env.cr, obsolete)
        return result

    # ------------------------------------------------------------------
    # Réservation
    # ------------------------------------------------------------------
    def _reserve_keys(self, keys):
        """Réserve les clés indiquées (peut lever un conflit)."""
        if not keys:
            return
        try:
            _insert_reservations(self.env.cr, keys)
        except psycopg2.errors.ExclusionViolation as exc:
            raise self._conflict_error(keys, exc) from exc
        except psycopg2.errors.UniqueViolation as exc:
            # Filet de sécurité : les index uniques des tables de référence
            # peuvent encore rejeter la ligne (cas concurrent).
            raise self._conflict_error(keys, exc) from exc

    def _reserve_records(self, records):
        """Réserve les clés des enregistrements actifs."""
        self._reserve_keys(_records_keys(records))

    def _conflict_error(self, keys, exc):
        """Traduit un conflit de réservation en message métier français."""
        model_name, kind, normalized = keys[0][0], keys[0][1], keys[0][2]
        return ValidationError(
            self.env._(
                _conflict_message(kind, normalized),
                value=normalized.upper(),
            )
        )
