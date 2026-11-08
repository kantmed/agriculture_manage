from odoo import fields, models


class AgricultureFarm(models.Model):
    _inherit = "agriculture.farm"

    project_ids = fields.One2many(
        "project.project", "agriculture_farm_id", string="Projets agricoles"
    )


class AgricultureFarmPlot(models.Model):
    _inherit = "agriculture.farm.plot"

    project_ids = fields.Many2many(
        "project.project",
        "agriculture_project_plot_rel",
        "plot_id",
        "project_id",
        string="Projets concernés",
    )
