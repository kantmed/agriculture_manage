from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = "project.project"

    agriculture_farm_id = fields.Many2one(
        "agriculture.farm",
        string="Exploitation agricole",
        index=True,
        ondelete="restrict",
        check_company=True,
        help="Exploitation principalement concernée par ce projet.",
    )
    agriculture_plot_ids = fields.Many2many(
        "agriculture.farm.plot",
        "agriculture_project_plot_rel",
        "project_id",
        "plot_id",
        string="Parcelles concernées",
        help="Un projet peut concerner plusieurs parcelles de la même exploitation.",
    )
    agriculture_project_type = fields.Selection(
        [
            ("development", "Développement agricole"),
            ("plantation", "Plantation / verger"),
            ("irrigation", "Irrigation / hydraulique"),
            ("building", "Bâtiment / infrastructure"),
            ("equipment", "Acquisition d'équipement"),
            ("land", "Aménagement foncier"),
            ("other", "Autre"),
        ],
        string="Type de projet agricole",
        default="development",
        tracking=True,
    )
    agriculture_currency_id = fields.Many2one(
        "res.currency", string="Devise agricole", related="company_id.currency_id", readonly=True,
    )
    agriculture_investment_estimate = fields.Monetary(
        string="Investissement prévisionnel",
        currency_field="agriculture_currency_id",
        tracking=True,
        help="Montant indicatif du projet. Ce champ ne crée aucune écriture comptable.",
    )
    agriculture_project_notes = fields.Html(string="Notes agricoles")
    agriculture_plot_count = fields.Integer(
        string="Nombre de parcelles",
        compute="_compute_agriculture_plot_count",
    )
    agriculture_operation_ids = fields.One2many(
        "agriculture.farm.operation", "project_id", string="Opérations du projet",
    )

    @api.depends("agriculture_plot_ids")
    def _compute_agriculture_plot_count(self):
        for project in self:
            project.agriculture_plot_count = len(project.agriculture_plot_ids)

    def action_view_agriculture_operations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Opérations du projet"),
            "res_model": "agriculture.farm.operation",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id)],
            "context": {
                "default_project_id": self.id,
                "default_company_id": self.company_id.id,
            },
        }

    @api.constrains("agriculture_farm_id", "agriculture_plot_ids", "company_id")
    def _check_agriculture_links(self):
        for project in self:
            farm = project.agriculture_farm_id
            if farm and not project.company_id:
                raise ValidationError(_("Un projet agricole rattaché à une exploitation doit avoir une société."))
            if farm and project.company_id and farm.company_id != project.company_id:
                raise ValidationError(_("L'exploitation et le projet doivent appartenir à la même société."))
            if project.agriculture_plot_ids:
                if not farm:
                    raise ValidationError(_("Sélectionnez une exploitation avant d'affecter des parcelles."))
                wrong_plots = project.agriculture_plot_ids.filtered(lambda plot: plot.farm_id != farm)
                if wrong_plots:
                    raise ValidationError(_("Toutes les parcelles doivent appartenir à l'exploitation du projet."))


class AgricultureFarmOperation(models.Model):
    _inherit = "agriculture.farm.operation"

    project_id = fields.Many2one(
        "project.project",
        string="Projet",
        index=True,
        ondelete="restrict",
        check_company=True,
        help="Projet auquel cette opération de réalisation est rattachée. Une opération est liée soit à une campagne, soit à un projet.",
    )
    # These two fields were originally related to campaign_id in the crop/stock
    # modules. They must also work for project operations.
    company_id = fields.Many2one(
        "res.company", string="Société", compute="_compute_agriculture_company_id",
        store=True, readonly=True,
    )
    farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation", compute="_compute_agriculture_farm_id",
        store=True, readonly=True,
    )

    @api.depends("campaign_id.company_id", "project_id.company_id")
    def _compute_agriculture_company_id(self):
        for operation in self:
            operation.company_id = (
                operation.campaign_id.company_id
                or operation.project_id.company_id
                or operation.project_id.agriculture_farm_id.company_id
                or False
            )

    @api.depends("campaign_id.farm_id", "project_id.agriculture_farm_id")
    def _compute_agriculture_farm_id(self):
        for operation in self:
            operation.farm_id = (
                operation.campaign_id.farm_id
                or operation.project_id.agriculture_farm_id
                or False
            )

    @api.onchange("campaign_id")
    def _onchange_campaign_id_clear_project(self):
        if self.campaign_id:
            self.project_id = False

    @api.onchange("project_id")
    def _onchange_project_id_clear_campaign(self):
        if self.project_id:
            self.campaign_id = False
            if self.plot_id and self.project_id.agriculture_plot_ids and self.plot_id not in self.project_id.agriculture_plot_ids:
                self.plot_id = False

    @api.constrains("campaign_id", "project_id", "plot_id", "company_id")
    def _check_operation_owner(self):
        for operation in self:
            if bool(operation.campaign_id) == bool(operation.project_id):
                raise ValidationError(_("Une opération doit être rattachée à une campagne ou à un projet, mais jamais aux deux."))
            if operation.campaign_id and operation.plot_id and operation.plot_id.farm_id != operation.campaign_id.farm_id:
                raise ValidationError(_("La parcelle doit appartenir à l'exploitation de la campagne."))
            if operation.project_id:
                project = operation.project_id
                if operation.company_id and project.company_id != operation.company_id:
                    raise ValidationError(_("Le projet et l'opération doivent appartenir à la même société."))
                if operation.plot_id:
                    if not project.agriculture_farm_id or operation.plot_id.farm_id != project.agriculture_farm_id:
                        raise ValidationError(_("La parcelle de l'opération doit appartenir à l'exploitation du projet."))
                    if project.agriculture_plot_ids and operation.plot_id not in project.agriculture_plot_ids:
                        raise ValidationError(_("La parcelle de l'opération doit faire partie des parcelles du projet."))
