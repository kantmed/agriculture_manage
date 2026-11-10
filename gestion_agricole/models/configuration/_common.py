# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError


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
    Cette fonction utilise un advisory lock PostgreSQL pg_advisory_xact_lock
    pour sérialiser les transactions concurrentes portant sur la même référence
    normalisée. Le lock est automatiquement libéré à la fin de la transaction
    Odoo, garantissant ainsi l'intégrité sans nécessiter de gestion manuelle.

    La clé de verrouillage est calculée via hashlib.sha256() pour garantir
    une valeur déterministe identique sur tous les workers Odoo. Le hash Python
    native étant randomisée entre processus, elle a été remplacée par une somme
    de contrôle cryptographique stable.

    La clé est basée sur la référence normalisée (code insensible à la casse
    et aux espaces), sans inclure company_id : un code global et un code société
    identiques partagent le même verrou, car ils sont en conflit dans le même
    périmètre d'unicité.
    """
    import logging
    from odoo.exceptions import ValidationError
    import hashlib

    for record in records:
        value = record[field_name]
        if not value:
            continue

        # Normalisation : insensible à la casse et aux espaces
        normalized = value.strip().casefold()

        # Construction déterministe de la clé de lock PostgreSQL via hashlib.sha256().
        # Contrairement à hash() Python qui est randomisée entre processus,
        # sha256() produit une empreinte stable identique sur tous les workers.
        # On utilise les 8 premiers octets du digest, convertis en entier positif,
        # ce qui est dans la plage valide de pg_advisory_xact_lock
        # (comprise entre -2^63 et 2^63-1).
        hash_bytes = hashlib.sha256(normalized.encode("utf-8")).digest()
        lock_key = int.from_bytes(hash_bytes[:8], "big")

        try:
            # Acquiert un advisory lock transactionnel.
            # pg_advisory_xact_lock est automatiquement libéré à la fin de la transaction
            # (commit ou rollback), ce qui garantit la sérialisation sans gestion manuelle.
            record.env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s)", (lock_key,)
            )

            # Dans le lock, on vérifie l'unicité dans le périmètre défini
            domain = [("active", "=", True), ("id", "!=", record.id)]
            if record.company_id:
                if global_scope:
                    domain = [
                        "|",
                        ("company_id", "=", record.company_id.id),
                        ("company_id", "=", False),
                    ] + domain
                else:
                    domain = ["|", ("company_id", "=", record.company_id.id), ("company_id", "=", False)] + domain
            elif not global_scope:
                domain = [("company_id", "=", False)] + domain

            for other in records.sudo().search(domain):
                other_value = other[field_name]
                if other_value and other_value.strip().casefold() == normalized:
                    raise ValidationError(
                        records.env._(
                            "La valeur « %(value)s » du champ « %(label)s » existe déjà dans ce périmètre.",
                            value=value,
                            label=label,
                        )
                    )

            # Le lock est automatiquement libéré à la fin de la transaction.
            # Aucune action de libération explicite n'est nécessaire.

        except ValidationError:
            # Relever la ValidationError pour la propager
            raise
        except Exception as e:
            # En cas d'erreur inattendue, on s'assure que le lock est quand même libéré
            # (pg_advisory_xact_lock l'est automatiquement à la fin de la transaction)
            # Mais on relève tout de même l'erreur pour ne pas masquer le problème
            raise
