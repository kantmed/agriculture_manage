# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_same_company, check_unique_code


class GestAgriPlot(models.Model):
    _name = "gest_agri.plot"
    _description = "Parcelle agricole"
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
    area = fields.Float(
        string="Surface (ha)",
        digits=(16, 2),
        required=True,
        default=0.0,
        help="Surface de la parcelle en hectares.",
    )
    soil_type_id = fields.Many2one(
        "gest_agri.soil.type",
        string="Type de sol",
        check_company=True,
        ondelete="restrict",
        index=True,
    )
    irrigation_type_id = fields.Many2one(
        "gest_agri.irrigation.type",
        string="Type d'irrigation",
        check_company=True,
        ondelete="restrict",
        index=True,
    )
    ph_min = fields.Float(
        string="pH minimum",
        digits=(4, 2),
        default=0.0,
        help="Valeur de pH minimale observée ou attendue sur la parcelle.",
    )
    ph_max = fields.Float(
        string="pH maximum",
        digits=(4, 2),
        default=14.0,
        help="Valeur de pH maximale observée ou attendue sur la parcelle.",
    )
    slope_percent = fields.Float(
        string="Pente (%)",
        digits=(5, 2),
        default=0.0,
        help="Pente moyenne de la parcelle, en pourcentage.",
    )
    latitude = fields.Float(string="Latitude", digits=(10, 6))
    longitude = fields.Float(string="Longitude", digits=(10, 6))
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    _code_farm_unique = models.UniqueIndex(
        "(farm_id, UPPER(code)) WHERE active IS TRUE",
        "Le code de la parcelle doit être unique au sein de l'exploitation.",
    )

    @api.constrains("code", "farm_id", "active")
    def _check_code_unique(self):
        check_unique_code(self, "farm_id")

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for plot in self:
            if plot.site_id and plot.site_id.farm_id != plot.farm_id:
                raise ValidationError(
                    self.env._(
                        "Le site « %(site)s » n'appartient pas à l'exploitation "
                        "« %(farm)s ».",
                        site=plot.site_id.display_name,
                        farm=plot.farm_id.display_name,
                    )
                )

    @api.constrains("area")
    def _check_area(self):
        for plot in self:
            if plot.area < 0:
                raise ValidationError(
                    self.env._("La surface d'une parcelle ne peut pas être négative.")
                )

    @api.constrains("ph_min", "ph_max")
    def _check_ph_range(self):
        for plot in self:
            if not (0.0 <= plot.ph_min <= 14.0) or not (0.0 <= plot.ph_max <= 14.0):
                raise ValidationError(
                    self.env._("Les valeurs de pH doivent être comprises entre 0 et 14.")
                )
            if plot.ph_min > plot.ph_max:
                raise ValidationError(
                    self.env._(
                        "Le pH minimum ne peut pas être supérieur au pH maximum."
                    )
                )

    @api.constrains("slope_percent")
    def _check_slope(self):
        for plot in self:
            if not (0.0 <= plot.slope_percent <= 100.0):
                raise ValidationError(
                    self.env._("La pente doit être comprise entre 0 et 100 %.")
                )

    @api.constrains("latitude", "longitude")
    def _check_coordinates(self):
        for plot in self:
            if plot.latitude and not (-90.0 <= plot.latitude <= 90.0):
                raise ValidationError(
                    self.env._("La latitude doit être comprise entre -90 et 90.")
                )
            if plot.longitude and not (-180.0 <= plot.longitude <= 180.0):
                raise ValidationError(
                    self.env._("La longitude doit être comprise entre -180 et 180.")
                )

    @api.constrains("soil_type_id", "irrigation_type_id")
    def _check_company_relations(self):
        check_same_company(self, ["soil_type_id", "irrigation_type_id"])

    @api.model
    def write(self, vals):
        if 'farm_id' in vals and not self.env.user.has_group(
            'gestion_agricole.group_gest_agri_admin'
        ):
            for record in self.filtered(lambda r: not r.env.user.has_group(
                'gestion_agricole.group_gest_agri_admin'
            )):
                target_farm_id = vals['farm_id']
                target_farm = record.env['gest_agri.farm'].browse(target_farm_id)
                if target_farm.company_id != record.company_id:
                    raise AccessError(
                        "Vous ne pouvez pas déplacer cette parcelle vers une "
                        "exploitation d'une autre société."
                    )
                user = record.env.user
                if not user.has_group(
                    'gestion_agricole.group_gest_agri_manager'
                ) and user.id != target_farm.manager_id.id:
                    raise AccessError(
                        "Vous ne pouvez pas déplacer cette parcelle vers une "
                        "exploitation que vous ne gérez pas."
                    )
        return super(Plot, self).write(vals)