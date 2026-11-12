# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GestAgriAnimalDisease(models.Model):
    _name = "gest_agri.animal.disease"
    _description = "Maladie animale"
    _order = "name"
    _check_company_auto = True

    name = fields.Char(string="Nom de la maladie", required=True, index=True)
    code = fields.Char(string="Code", required=True, index=True)
    description = fields.Text(string="Description")
    symptoms = fields.Text(string="Symptômes caractéristiques")
    species_ids = fields.Many2many("gest_agri.livestock.species", string="Espèces concernées")
    severity = fields.Selection(
        selection=[("low", "Faible"), ("medium", "Moyenne"), ("high", "Élevée"), ("critical", "Critique")],
        string="Gravité", default="medium",
    )
    contagious = fields.Boolean(string="Contagieuse", default=False)
    recommendations = fields.Text(string="Recommandations générales")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one("res.company", string="Société", index=True, default=lambda self: self.env.company)

    _code_company_unique = models.UniqueIndex(
        "(COALESCE(company_id, 0), LOWER(BTRIM(code))) WHERE active IS TRUE",
        "Le code de la maladie doit être unique au sein de la société.",
    )
