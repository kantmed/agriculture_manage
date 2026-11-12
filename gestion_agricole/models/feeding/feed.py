# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GestAgriFeed(models.Model):
    _name = "gest_agri.feed"
    _description = "Aliment agricole"
    _order = "name"
    _check_company_auto = True

    name = fields.Char(string="Désignation", required=True, index=True)
    code = fields.Char(string="Code", required=True, index=True)
    category = fields.Selection(
        selection=[("forage", "Fourrage"), ("concentrate", "Concentré"), ("mineral", "Minéral"), ("other", "Autre")],
        string="Catégorie", default="other",
    )
    species_id = fields.Many2one("gest_agri.livestock.species", string="Espèce compatible", ondelete="set null", index=True)
    uom_id = fields.Many2one("uom.uom", string="Unité de mesure", required=True, ondelete="restrict")
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one("res.company", string="Société", index=True, default=lambda self: self.env.company)

    _code_company_unique = models.UniqueIndex(
        "(COALESCE(company_id, 0), LOWER(BTRIM(code))) WHERE active IS TRUE",
        "Le code de l'aliment doit être unique au sein de la société.",
    )

    @api.constrains("company_id", "species_id")
    def _check_species_company(self):
        for feed in self:
            if feed.species_id and feed.species_id.company_id and feed.company_id and feed.species_id.company_id != feed.company_id:
                raise ValidationError(self.env._("L'espèce ne appartient pas à la même société."))

    @api.constrains("uom_id")
    def _check_uom(self):
        for feed in self:
            if not feed.uom_id:
                raise ValidationError(self.env._("L'unité de mesure est obligatoire."))