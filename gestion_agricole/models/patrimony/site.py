# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_unique_code


class GestAgriSite(models.Model):
    _name = "gest_agri.site"
    _description = "Site d'exploitation"
    _order = "farm_id, sequence, name"
    _check_company_auto = True

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", required=True, index=True)
    farm_id = fields.Many2one(
        "gest_agri.farm",
        string="Exploitation",
        required=True,
        ondelete="cascade",
        check_company=True,
        index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id",
        string="Société",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    description = fields.Text(string="Description")
    area_ha = fields.Float(
        string="Surface (ha)",
        digits=(16, 2),
        default=0.0,
        help="Surface totale du site en hectares.",
    )
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    plot_ids = fields.One2many("gest_agri.plot", "site_id", string="Parcelles")
    building_ids = fields.One2many("gest_agri.building", "site_id", string="Bâtiments")
    infrastructure_ids = fields.One2many(
        "gest_agri.infrastructure", "site_id", string="Infrastructures"
    )
    water_source_ids = fields.One2many(
        "gest_agri.water.source", "site_id", string="Sources d'eau"
    )

    _code_farm_unique = models.UniqueIndex(
        "(farm_id, UPPER(code)) WHERE active IS TRUE",
        "Le code du site doit être unique au sein de l'exploitation.",
    )

    @api.constrains("area_ha")
    def _check_area_ha(self):
        for site in self:
            if site.area_ha < 0:
                raise ValidationError(
                    self.env._("La surface du site ne peut pas être négative.")
                )

    @api.constrains("code", "farm_id", "active")
    def _check_code_unique(self):
        check_unique_code(self, "farm_id")
