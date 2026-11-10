# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError


def check_unique_code(records, scope_field=None):
    """Vérifie l'unicité du code sur les enregistrements actifs.

    ``scope_field`` permet de restreindre la vérification à un périmètre
    fonctionnel, par exemple ``farm_id`` pour les parcelles, sites et
    infrastructures. La comparaison ignore la casse et les espaces.
    """
    for record in records:
        if not record.code:
            continue
        domain = [("active", "=", True), ("id", "!=", record.id)]
        if scope_field:
            scope = record[scope_field]
            domain.append((scope_field, "=", scope.id if scope else False))

        normalized = record.code.strip().casefold()
        for other in records.sudo().search(domain):
            if other.code and other.code.strip().casefold() == normalized:
                raise ValidationError(
                    records.env._(
                        "Le code « %(code)s » est déjà utilisé dans ce périmètre.",
                        code=record.code,
                    )
                )


def check_same_company(records, field_names):
    """Vérifie que les relations désignées appartiennent bien à la société."""
    for record in records:
        if not record.company_id:
            continue
        for field_name in field_names:
            related = record[field_name]
            if related and related.company_id and related.company_id != record.company_id:
                raise ValidationError(
                    records.env._(
                        "La société de « %(record)s » ne correspond pas à celle de la "
                        "relation « %(field)s ».",
                        record=record.display_name,
                        field=field_name,
                    )
                )
