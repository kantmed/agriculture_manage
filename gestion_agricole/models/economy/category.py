# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GestAgriEconomicCategory(models.Model):
    _name = "gest_agri.economic.category"
    _description = "Catégorie économique agricole"
    _order = "nature, sequence, name"
    _check_company_auto = True

    name = fields.Char(string="Désignation", required=True, index=True)
    code = fields.Char(string="Code", required=True, index=True)
    nature = fields.Selection(
        selection=[("expense", "Charge"), ("revenue", "Recette")],
        string="Nature",
        required=True,
        index=True,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)
    company_id = fields.Many2one(
        "res.company", string="Société", index=True,
        default=lambda self: self.env.company,
    )

    _code_company_unique = models.UniqueIndex(
        "(COALESCE(company_id, 0), LOWER(BTRIM(code))) WHERE active IS TRUE",
        "Le code de la catégorie doit être unique au sein de la société.",
    )

    # La cohérence de la nature est garantie par la sélection du champ 'nature'.
