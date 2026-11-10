# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_unique_code


class GestAgriWaterSource(models.Model):
    _name = "gest_agri.water.source"
    _description = "Source d'eau"
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
    source_type = fields.Selection(
        selection=[
            ("well", "Puits"),
            ("borehole", "Forage"),
            ("spring", "Source"),
            ("river", "Rivière"),
            ("pond", "Retenue / bassin"),
            ("network", "Réseau public"),
            ("other", "Autre"),
        ],
        string="Type de source",
        required=True,
        default="other",
    )
    capacity_m3_day = fields.Float(
        string="Débit disponible (m³/jour)",
        digits=(16, 2),
        default=0.0,
    )
    depth_m = fields.Float(string="Profondeur (m)", digits=(16, 2), default=0.0)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    irrigation_network_ids = fields.One2many(
        "gest_agri.irrigation.network", "water_source_id", string="Réseaux d'irrigation"
    )

    _code_farm_unique = models.UniqueIndex(
        "(farm_id, UPPER(code)) WHERE active IS TRUE",
        "Le code de la source d'eau doit être unique au sein de l'exploitation.",
    )

    @api.constrains("code", "farm_id", "active")
    def _check_code_unique(self):
        check_unique_code(self, "farm_id")

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for source in self:
            if source.site_id and source.site_id.farm_id != source.farm_id:
                raise ValidationError(
                    self.env._(
                        "Le site « %(site)s » n'appartient pas à l'exploitation "
                        "« %(farm)s ».",
                        site=source.site_id.display_name,
                        farm=source.farm_id.display_name,
                    )
                )

    @api.constrains("capacity_m3_day", "depth_m")
    def _check_positive_values(self):
        for source in self:
            if source.capacity_m3_day < 0:
                raise ValidationError(
                    self.env._("Le débit disponible ne peut pas être négatif.")
                )
            if source.depth_m < 0:
                raise ValidationError(
                    self.env._("La profondeur ne peut pas être négative.")
                )
