# -*- coding: utf-8 -*-
from odoo import api, fields, models

from ._common import check_unique_reference


class GestAgriCropVariety(models.Model):
    _name = "gest_agri.crop.variety"
    _description = "Variété de culture"
    _order = "sequence, name"
    _check_company_auto = True

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", required=True, index=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        index=True,
        default=lambda self: self.env.company,
        help="Laisser vide pour un référentiel global, réservé aux administrateurs.",
    )
    sequence = fields.Integer(string="Séquence", default=10)
    crop_type_id = fields.Many2one(
        "gest_agri.crop.type",
        string="Type de culture",
        required=True,
        check_company=True,
        ondelete="restrict",
        index=True,
    )

    @api.constrains("code", "company_id", "active")
    def _check_code_unique(self):
        # Empêcher company_id=False par un gestionnaire non admin
        for record in self.filtered(
            lambda r: not r.env.user.has_group(
                "gestion_agricole.group_gest_agri_admin"
            )
        ):
            if record.company_id == False and record.id:
                raise ValidationError(
                    "Seul un administrateur peut rendre une référence globale "
                    "(company_id=False)."
                )
        check_unique_reference(self, "code", "Code", global_scope=True)

    @api.constrains("name", "company_id", "active")
    def _check_name_unique(self):
        # Empêcher company_id=False par un gestionnaire non admin
        for record in self.filtered(
            lambda r: not r.env.user.has_group(
                "gestion_agricole.group_gest_agri_admin"
            )
        ):
            if record.company_id == False and record.id:
                raise ValidationError(
                    "Seul un administrateur peut rendre une référence globale "
                    "(company_id=False)."
                )
        check_unique_reference(self, "name", "Nom", global_scope=False)
