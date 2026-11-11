# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_unique_code


class GestAgriIrrigationNetwork(models.Model):
    _name = "gest_agri.irrigation.network"
    _description = "Réseau d'irrigation"
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
    water_source_id = fields.Many2one(
        "gest_agri.water.source",
        string="Source d'eau",
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
    network_type = fields.Selection(
        selection=[
            ("drip", "Goutte-à-goutte"),
            ("sprinkler", "Aspersion"),
            ("gravity", "Gravitaire"),
            ("pivot", "Pivot"),
            ("other", "Autre"),
        ],
        string="Type de réseau",
        required=True,
        default="drip",
    )
    flow_rate_m3_h = fields.Float(
        string="Débit (m³/h)",
        digits=(16, 2),
        default=0.0,
    )
    description = fields.Text(string="Description")
    notes = fields.Text(
        string="Notes internes",
        help="Observations et informations complémentaires relatives au réseau d'irrigation.",
    )
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    sector_ids = fields.One2many(
        "gest_agri.irrigation.sector", "network_id", string="Secteurs"
    )
    pump_ids = fields.One2many(
        "gest_agri.irrigation.pump", "network_id", string="Pompes"
    )

    _code_farm_unique = models.UniqueIndex(
        "(farm_id, UPPER(code)) WHERE active IS TRUE",
        "Le code du réseau d'irrigation doit être unique au sein de l'exploitation.",
    )

    @api.constrains("code", "farm_id", "active")
    def _check_code_unique(self):
        check_unique_code(self, "farm_id")

    @api.constrains("farm_id", "water_source_id")
    def _check_water_source_farm(self):
        for network in self:
            if (
                network.water_source_id
                and network.water_source_id.farm_id != network.farm_id
            ):
                raise ValidationError(
                    self.env._(
                        "La source d'eau « %(source)s » n'appartient pas à "
                        "l'exploitation « %(farm)s ».",
                        source=network.water_source_id.display_name,
                        farm=network.farm_id.display_name,
                    )
                )

    @api.constrains("flow_rate_m3_h")
    def _check_flow_rate(self):
        for network in self:
            if network.flow_rate_m3_h < 0:
                raise ValidationError(
                    self.env._("Le débit du réseau ne peut pas être négatif.")
                )
