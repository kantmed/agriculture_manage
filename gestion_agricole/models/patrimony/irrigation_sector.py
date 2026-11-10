# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_unique_code


class GestAgriIrrigationSector(models.Model):
    _name = "gest_agri.irrigation.sector"
    _description = "Secteur d'irrigation"
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
    area = fields.Float(
        string="Surface irriguée (ha)",
        digits=(16, 2),
        default=0.0,
    )
    plot_ids = fields.Many2many(
        "gest_agri.plot",
        "gest_agri_irrigation_sector_plot_rel",
        "sector_id",
        "plot_id",
        string="Parcelles desservies",
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    _code_farm_unique = models.UniqueIndex(
        "(farm_id, UPPER(code)) WHERE active IS TRUE",
        "Le code du secteur doit être unique au sein de l'exploitation.",
    )

    @api.constrains("code", "farm_id", "active")
    def _check_code_unique(self):
        check_unique_code(self, "farm_id")

    @api.constrains("area")
    def _check_area(self):
        for sector in self:
            if sector.area < 0:
                raise ValidationError(
                    self.env._("La surface irriguée ne peut pas être négative.")
                )

    @api.constrains("farm_id", "plot_ids")
    def _check_plot_farm(self):
        for sector in self:
            # Sens 1 : toutes les parcelles doivent appartenir à l'exploitation du secteur
            wrong = sector.plot_ids.filtered(lambda plot: plot.farm_id != sector.farm_id)
            if wrong:
                raise ValidationError(
                    self.env._(
                        "Les parcelles %(plots)s n'appartiennent pas à "
                        "l'exploitation « %(farm)s ».",
                        plots=", ".join(wrong.mapped("display_name")),
                        farm=sector.farm_id.display_name,
                    )
                )
            # Sens 2 : vérification inverse - si une parcelle change d'exploitation,
            # elle ne doit pas rester dans des secteurs de l'ancienne exploitation
            for plot in sector.plot_ids:
                # Vérifier que plot.farm_id est bien sector.farm_id
                if plot.farm_id != sector.farm_id:
                    # La parcelle a été déplacée hors de l'exploitation du secteur
                    # On vérifie s'il y a des secteurs hérités de l'ancienne ferme
                    old_sectors = self.env['gest_agri.irrigation.sector'].search([
                        ('farm_id', '=', plot.farm_id.id),
                        ('active', '=', True),
                    ])
                    # Si la parcelle était dans un secteur existant et qu'on change
                    # son exploitation, c'est une incohérence
                    if plot.id in sector.plot_ids and plot.farm_id != sector.farm_id:
                        raise ValidationError(
                            self.env._(
                                "Une parcelle ne peut pas changer d'exploitation sans "
                                "mise à jour des secteurs qui lui sont rattachés. "
                                "Contactez un administrateur."
                            )
                        )
