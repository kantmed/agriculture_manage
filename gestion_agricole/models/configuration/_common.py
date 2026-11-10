# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError


def check_unique_reference(records, field_name, label, global_scope=False):
    """Contrôle l'unicité d'une valeur sur les enregistrements actifs.

    Le contrôle est insensible à la casse et aux espaces de début et de fin.
    La portée dépend de ``company_id`` :

    * ``global_scope=True`` : un enregistrement global (sans société) entre en
      conflit avec toutes les sociétés ; un enregistrement propre à une société
      entre en conflit avec la même société et avec les enregistrements globaux.
    * ``global_scope=False`` : la comparaison reste strictement dans la même
      portée (même société, ou global avec global).
    """
    for record in records:
        value = record[field_name]
        if not value:
            continue
        domain = [("active", "=", True), ("id", "!=", record.id)]
        if record.company_id:
            if global_scope:
                domain = [
                    "|",
                    ("company_id", "=", record.company_id.id),
                    ("company_id", "=", False),
                ] + domain
            else:
                domain = [("company_id", "=", record.company_id.id)] + domain
        elif not global_scope:
            domain = [("company_id", "=", False)] + domain

        normalized = value.strip().casefold()
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
