# -*- coding: utf-8 -*-
from odoo import api, fields, models

from ._common import check_unique_reference


class GestAgriTreatmentType(models.Model):
    _name = "gest_agri.treatment.type"
    _description = "Type de traitement"
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

    @api.constrains("code", "company_id", "active")
    def _check_code_unique(self):
        check_unique_reference(self, "code", "Code", global_scope=True)

    @api.constrains("name", "company_id", "active")
    def _check_name_unique(self):
        check_unique_reference(self, "name", "Nom", global_scope=False)
