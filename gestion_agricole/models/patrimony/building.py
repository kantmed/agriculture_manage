# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_same_company, check_unique_code


class GestAgriBuilding(models.Model):
    _name = "gest_agri.building"
    _description = "Bâtiment agricole"
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
    building_type_id = fields.Many2one(
        "gest_agri.building.type",
        string="Type de bâtiment",
        check_company=True,
        ondelete="restrict",
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
    area = fields.Float(
        string="Surface (m²)",
        digits=(16, 2),
        default=0.0,
        help="Surface couverte du bâtiment en mètres carrés.",
    )
    capacity = fields.Integer(
        string="Capacité",
        default=0,
        help="Capacité d'accueil (places, animaux, tonnes, etc.).",
    )
    description = fields.Text(string="Description")
    notes = fields.Text(
        string="Notes internes",
        help="Observations et informations complémentaires relatives au bâtiment agricole.",
    )
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    _code_farm_unique = models.UniqueIndex(
        "(farm_id, UPPER(code)) WHERE active IS TRUE",
        "Le code du bâtiment doit être unique au sein de l'exploitation.",
    )

    @api.constrains("code", "farm_id", "active")
    def _check_code_unique(self):
        check_unique_code(self, "farm_id")

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for building in self:
            if building.site_id and building.site_id.farm_id != building.farm_id:
                raise ValidationError(
                    self.env._(
                        "Le site « %(site)s » n'appartient pas à l'exploitation "
                        "« %(farm)s ».",
                        site=building.site_id.display_name,
                        farm=building.farm_id.display_name,
                    )
                )

    @api.constrains("area", "capacity")
    def _check_positive_values(self):
        for building in self:
            if building.area < 0:
                raise ValidationError(
                    self.env._("La surface d'un bâtiment ne peut pas être négative.")
                )
            if building.capacity < 0:
                raise ValidationError(
                    self.env._("La capacité d'un bâtiment ne peut pas être négative.")
                )

    @api.constrains("building_type_id")
    def _check_company_relations(self):
        check_same_company(self, ["building_type_id"])
