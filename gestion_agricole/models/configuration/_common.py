# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError

#: Périmètre d'un code global : [1, +inf) — couvre toutes les sociétés.
SCOPE_GLOBAL_CODE = (1, None)
#: Périmètre d'un nom global : [-1, 0) — disjoint de toute société.
SCOPE_GLOBAL_NAME = (-1, 0)


def normalize_reference(value):
    """Normalise une référence (code ou nom) pour les comparaisons.

    La normalisation est insensible à la casse et aux espaces de début et de
    fin, comme les index uniques PostgreSQL ``LOWER(BTRIM(...))`` posés par
    Odoo sur les tables de référence.
    """
    if not value:
        return ""
    return value.strip().casefold()


def reference_scope(kind, company_id):
    """Renvoie le périmètre ``(scope_lo, scope_hi)`` d'une référence.

    * ``kind='code'``, société ``c``  -> ``(c, c+1)``  (domaine positif)
    * ``kind='code'``, global          -> ``(1, None)``  (couvre tout le positif)
    * ``kind='name'``, société ``c``   -> ``(c, c+1)``  (domaine positif)
    * ``kind='name'``, global           -> ``(-1, 0)``   (domaine négatif)

    Les domaines sont disjoints par construction : un nom global ne peut
    jamais chevaucher une société (dont l'identifiant est toujours >= 1).
    """
    if company_id:
        return (company_id, company_id + 1)
    if kind == "code":
        return SCOPE_GLOBAL_CODE
    return SCOPE_GLOBAL_NAME


def _advisory_lock_key(normalized):
    """Calcule une clé de verrou consultatif stable et valide pour PostgreSQL.

    ``pg_advisory_xact_lock`` n'accepte qu'un ``bigint`` signé, soit une plage
    [-2^63, 2^63-1]. Une empreinte SHA-256 brute est un entier *non signé* sur
    64 bits : une valeur sur deux environ dépasse 2^63-1 et PostgreSQL levait
    alors ``UndefinedFunction: la fonction pg_advisory_xact_lock(numeric)
    n'existe pas``.

    La conversion signée garantit une clé dans la plage admise, tout en
    conservant un caractère déterministe et identique sur tous les workers
    Odoo (contrairement au ``hash()`` natif, randomisé entre processus).
    """
    import hashlib

    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def check_unique_reference(records, field_name, label, global_scope=False):
    """Contrôle l'unicité d'une valeur sur les enregistrements actifs.

    Le contrôle est insensible à la casse et aux espaces de début et de fin.
    La portée dépend de ``company_id`` :

    * ``global_scope=True`` : un enregistrement global (sans société) entre en
      conflit avec toutes les sociétés ; un enregistrement propre à une société
      entre en conflit avec la même société et avec les enregistrements globaux.
    * ``global_scope=False`` : la comparaison reste stricte à la portée courante.
      Si l'enregistrement appartient à une société, il ne doit pas entrer en
      conflit avec un autre enregistrement de la même société ni avec un
      enregistrement global (company_id=False). Si l'enregistrement est global,
      il ne doit pas entrer en conflit avec un autre enregistrement global.

    Note : l'opérateur ``|`` (OR) est nécessaire en Odoo pour exprimer la
    disjonction ``company_id = société OU company_id = False``, car l'écriture
    ``[("company_id", "=", X), ("company_id", "=", False)]`` serait un ET et
    ne réaliserait pas le OU attendu.

    Mécanisme de concurrence :
    Cette fonction utilise un advisory lock PostgreSQL ``pg_advisory_xact_lock``
    pour sérialiser les transactions concurrentes portant sur la même référence
    normalisée. Le lock est automatiquement libéré à la fin de la transaction
    Odoo.

    ATTENTION — portée de la garantie :
    sous le niveau d'isolation ``REPEATABLE READ`` utilisé par défaut par
    Odoo 20 (``odoo/sql_db.py``), le verrou consultatif **ne garantit pas**
    l'unicité. La transaction qui attend le verrou conserve l'instantané
    pris avant l'attente et ne voit donc pas l'insertion validée par la
    transaction concurrente. La garantie réelle d'unicité est assurée par les
    index uniques PostgreSQL (``models.UniqueIndex``) déclarés sur les modèles ;
    ce contrôle applicatif sert à :
      - fournir un message d'erreur lisible à l'utilisateur ;
      - sérialiser les contrôles concurrentiels pour limiter les courses ;
      - couvrir les règles de portée que les index uniques ne peuvent pas
        exprimer (portée « globale »).

    La clé de verrouillage est calculée via ``hashlib.sha256()`` pour garantir
    une valeur déterministe identique sur tous les workers Odoo. Le hash
    Python natif étant randomisé entre processus, elle a été remplacée par une
    somme de contrôle cryptographique stable.

    La clé est basée sur la référence normalisée (code insensible à la casse
    et aux espaces), sans inclure company_id : un code global et un code
    société identiques partagent le même verrou, car ils sont en conflit dans
    le même périmètre d'unicité.
    """
    import logging

    _logger = logging.getLogger(__name__)

    for record in records:
        value = record[field_name]
        if not value:
            continue

        # Normalisation : insensible à la casse et aux espaces
        normalized = value.strip().casefold()

        # Clé de verrou déterministe, dans la plage bigint signée admise par
        # PostgreSQL pour pg_advisory_xact_lock().
        lock_key = _advisory_lock_key(normalized)

        try:
            # Acquiert un advisory lock transactionnel.
            # pg_advisory_xact_lock est automatiquement libéré à la fin de la
            # transaction (commit ou rollback).
            record.env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s)", (lock_key,)
            )

            # Dans le lock, on vérifie l'unicité dans le périmètre défini
            domain = [("active", "=", True), ("id", "!=", record.id)]
            if record.company_id:
                # records.company_id est un Many2one : « company_id = société »
                # ou « company_id = False » (référence globale).
                domain = [
                    "|",
                    ("company_id", "=", record.company_id.id),
                    ("company_id", "=", False),
                ] + domain
            elif not global_scope:
                domain = [("company_id", "=", False)] + domain

            # search_fetch ne charge que la colonne utile au lieu de
            # l'intégralité des enregistrements du périmètre.
            others = records.sudo().search_fetch(domain, [field_name])
            for other in others:
                other_value = other[field_name]
                if other_value and other_value.strip().casefold() == normalized:
                    raise ValidationError(
                        records.env._(
                            "La valeur « %(value)s » du champ « %(label)s » existe "
                            "déjà dans ce périmètre.",
                            value=value,
                            label=label,
                        )
                    )

            # Le lock est automatiquement libéré à la fin de la transaction.
            # Aucune action de libération explicite n'est nécessaire.

        except ValidationError:
            # Relever la ValidationError pour la propager
            raise
        except Exception:
            # En cas d'erreur inattendue, on assure que le lock est quand même
            # libéré (pg_advisory_xact_lock l'est automatiquement à la fin de
            # la transaction) et on relance l'erreur pour ne pas masquer le
            # problème.
            _logger.debug(
                "Échec du contrôle d'unicité %s sur %s",
                label,
                records._name,
                exc_info=True,
            )
            raise
