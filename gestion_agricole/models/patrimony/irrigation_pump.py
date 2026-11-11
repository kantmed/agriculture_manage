# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_unique_code


class GestAgriIrrigationPump(models.Model):
    _name = "gest_agri.irrigation.pump"
    _description = "Pompe d'irrigation"
    _order = "farm_id, sequence, name"
    _check_company_auto = True

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", required=True, index=True)
    network_id = fields.Many2one(
        "gest_agri.irrigation.network",
        string="Réseau d'irrigation",
        required=True,
        ondelete="cascade",
        check_company=True,
        index=True,
    )
    farm_id = fields.Many2one(
        related="network_id.farm_id",
        string="Exploitation",
        store=True,
        readonly=True,
        precompute=True,
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
    power_kw = fields.Float(
        string="Puissance (kW)",
        digits=(16, 2),
        default=0.0,
    )
    flow_rate_m3_h = fields.Float(
        string="Débit (m³/h)",
        digits=(16, 2),
        default=0.0,
    )
    description = fields.Text(string="Description")
    notes = fields.Text(
        string="Notes internes",
        help="Observations et informations complémentaires relatives au pompe d'irrigation.",
    )
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    _code_farm_unique = models.UniqueIndex(
        "(farm_id, UPPER(code)) WHERE active IS TRUE",
        "Le code de la pompe doit être unique au sein de l'exploitation.",
    )

    @api.constrains("code", "farm_id", "active")
    def _check_code_unique(self):
        check_unique_code(self, "farm_id")

    @api.constrains("power_kw", "flow_rate_m3_h")
    def _check_positive_values(self):
        for pump in self:
            if pump.power_kw < 0:
                raise ValidationError(
                    self.env._("La puissance d'une pompe ne peut pas être négative.")
                )
            if pump.flow_rate_m3_h < 0:
                raise ValidationError(
                    self.env._("Le débit d'une pompe ne peut pas être négatif.")
                )
