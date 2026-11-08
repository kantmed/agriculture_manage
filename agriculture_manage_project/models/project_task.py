from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = "project.task"

    agriculture_farm_id = fields.Many2one(
        related="project_id.agriculture_farm_id",
        string="Exploitation agricole",
        store=True,
        readonly=True,
    )
    agriculture_plot_id = fields.Many2one(
        "agriculture.farm.plot",
        string="Parcelle concernée",
        ondelete="restrict",
        domain="[('id', 'in', project_id.agriculture_plot_ids)]",
        help="Parcelle précise concernée par cette tâche. Elle doit faire partie des parcelles du projet.",
    )

    @api.constrains("project_id", "agriculture_plot_id")
    def _check_agriculture_plot(self):
        for task in self:
            plot = task.agriculture_plot_id
            project = task.project_id
            if not plot:
                continue
            if plot.farm_id != project.agriculture_farm_id:
                raise ValidationError(_("La parcelle de la tâche doit appartenir à l'exploitation du projet."))
            if project.agriculture_plot_ids and plot not in project.agriculture_plot_ids:
                raise ValidationError(_("La parcelle de la tâche doit être sélectionnée dans les parcelles du projet."))
