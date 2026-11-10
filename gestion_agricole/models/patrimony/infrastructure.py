# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_unique_code


class GestAgriInfrastructure(models.Model):
    _name = "gest_agri.infrastructure"
    _description = "Infrastructure agricole"
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
    site_id = fields.Many2one(
        "gest_agri.site",
        string="Site",
        ondelete="set null",
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
    infrastructure_kind = fields.Selection(
        selection=[
            ("road", "Voie d'accès"),
            ("fence", "Clôture"),
            ("storage", "Stockage"),
            ("drainage", "Drainage"),
            ("other", "Autre"),
        ],
        string="Type d'infrastructure",
        required=True,
        default="other",
    )
    length_m = fields.Float(
        string="Longueur (m)", digits=(16, 2), default=0.0
    )
    area = fields.Float(string="Surface (m²)", digits=(16, 2), default=0.0)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    _code_farm_unique = models.UniqueIndex(
        "(farm_id, UPPER(code)) WHERE active IS TRUE",
        "Le code de l'infrastructure doit être unique au sein de l'exploitation.",
    )

    @api.constrains("code", "farm_id", "active")
    def _check_code_unique(self):
        check_unique_code(self, "farm_id")

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for infrastructure in self:
            if (
                infrastructure.site_id
                and infrastructure.site_id.farm_id != infrastructure.farm_id
            ):
                raise ValidationError(
                    self.env._(
                        "Le site « %(site)s » n'appartient pas à l'exploitation "
                        "« %(farm)s ».",
                        site=infrastructure.site_id.display_name,
                        farm=infrastructure.farm_id.display_name,
                    )
                )

    @api.constrains("length_m", "area")
    def _check_positive_values(self):
        for infrastructure in self:
            if infrastructure.length_m < 0:
                raise ValidationError(
                    self.env._("La longueur d'une infrastructure ne peut pas être négative.")
                )
            if infrastructure.area < 0:
                raise ValidationError(
                    self.env._("La surface d'une infrastructure ne peut pas être négative.")
                )
