from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AgricultureFarmOperation(models.Model):
    _name = "agriculture.farm.operation"
    _description = "Opération culturale"
    _order = "date desc, name"

    name = fields.Char(
        string="Opération",
        required=True,
    )
    code = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default="Nouveau",
    )
    campaign_id = fields.Many2one(
        "agriculture.farm.crop.campaign",
        string="Campagne",
        ondelete="cascade",
    )
    plot_id = fields.Many2one(
        "agriculture.farm.plot",
        string="Parcelle",
    )
    operation_type = fields.Selection(
        [
            ("plowing", "Labour"),
            ("sowing", "Semis"),
            ("fertilizing", "Fertilisation"),
            ("spraying", "Traitement"),
            ("irrigation", "Irrigation"),
            ("harvesting", "Récolte"),
            ("other", "Autre"),
        ],
        string="Type d'opération",
        default="other",
        required=True,
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
    )
    description = fields.Text(string="Description")
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("done", "Réalisée"),
            ("cancelled", "Annulée"),
        ],
        string="État",
        default="draft",
    )
    location_id = fields.Many2one(
        "stock.location",
        string="Emplacement source",
        domain="[('usage', '=', 'internal')]",
    )
    location_dest_id = fields.Many2one(
        "stock.location",
        string="Emplacement destination",
        help="Emplacement de consommation des intrants.",
    )
    picking_id = fields.Many2one(
        "stock.picking",
        string="Transfert de stock",
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company", string="Société", compute="_compute_company_id", store=True, readonly=True,
    )

    @api.depends("campaign_id")
    def _compute_company_id(self):
        for operation in self:
            if operation.campaign_id:
                operation.company_id = operation.campaign_id.company_id
            elif "project_id" in operation._fields and operation.project_id:
                operation.company_id = operation.project_id.company_id
            else:
                operation.company_id = False
    line_ids = fields.One2many(
        "agriculture.farm.operation.line",
        "operation_id",
        string="Intrants / lignes",
    )
    notes = fields.Html(string="Observations")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("farm.operation")
                    or "Nouveau"
                )
        return super().create(vals_list)


    def action_validate(self):
        """Mark the agricultural work as completed.

        Stock movements are deliberately managed by agriculture_manage_stock.
        Keeping this base method free of stock picking creation prevents a
        second, automatic delivery from being created when the stock addon has
        already prepared its internal consumption transfer.
        """
        for operation in self:
            if operation.state == "draft":
                operation.state = "done"
        return True

    def action_cancel(self):
        self.state = "cancelled"
        return True
