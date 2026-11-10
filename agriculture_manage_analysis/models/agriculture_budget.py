from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


OPERATION_TYPES = [
    ("plowing", "Labour"),
    ("sowing", "Semis"),
    ("fertilizing", "Fertilisation"),
    ("spraying", "Traitement"),
    ("irrigation", "Irrigation"),
    ("harvesting", "Récolte"),
    ("other", "Autre opération"),
    ("labor", "Main-d'œuvre"),
    ("other_expense", "Autres dépenses"),
]


class AgricultureFarmCropBudget(models.Model):
    _name = "agriculture.farm.crop.budget"
    _description = "Budget agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, name"

    name = fields.Char(string="Budget", required=True)
    code = fields.Char(string="Référence", readonly=True, copy=False, default="Nouveau")
    campaign_id = fields.Many2one(
        "agriculture.farm.crop.campaign", string="Campagne",
        required=True, ondelete="restrict", index=True,
    )
    farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation",
        related="campaign_id.farm_id", store=True, readonly=True,
    )
    company_id = fields.Many2one(
        "res.company", related="campaign_id.company_id", store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", store=True, readonly=True,
    )
    date_start = fields.Date(string="Début de période")
    date_end = fields.Date(string="Fin de période")
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("confirmed", "Confirmé"),
        ("closed", "Clôturé"),
        ("cancelled", "Annulé"),
    ], string="État", default="draft", required=True, tracking=True)
    line_ids = fields.One2many(
        "agriculture.farm.crop.budget.line", "budget_id", string="Prévisions budgétaires",
        copy=True,
    )
    expense_ids = fields.One2many(
        "agriculture.farm.crop.budget.expense", "budget_id", string="Dépenses complémentaires",
        copy=True,
    )
    budget_total = fields.Monetary(
        string="Budget prévisionnel", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    actual_total = fields.Monetary(
        string="Dépenses réelles", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    variance_total = fields.Monetary(
        string="Écart (réel - prévu)", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    remaining_total = fields.Monetary(
        string="Budget restant", currency_field="currency_id",
        compute="_compute_totals", store=True,
    )
    consumption_rate = fields.Float(
        string="Consommation (%)", compute="_compute_totals", store=True,
    )
    is_over_budget = fields.Boolean(
        string="Dépassement", compute="_compute_totals", store=True,
    )
    block_over_budget = fields.Boolean(
        string="Bloquer si dépassement", default=False,
        help="Empêche l'enregistrement de dépenses si le budget est dépassé.",
    )

    _campaign_budget_unique = models.Constraint(
        "UNIQUE(campaign_id)",
        "Un budget existe déjà pour cette campagne.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                vals["code"] = self.env["ir.sequence"].next_by_code("agriculture.farm.crop.budget") or "Nouveau"
        return super().create(vals_list)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for budget in self:
            if budget.date_start and budget.date_end and budget.date_end < budget.date_start:
                raise ValidationError(_("La date de fin doit être postérieure ou égale à la date de début."))

    def check_budget_available(self, amount):
        self.ensure_one()
        if not self.block_over_budget:
            return True
        if self.remaining_total - amount < 0:
            raise ValidationError(_("Le budget '%s' est dépassé : dépense de %s dépasserait le montant prévu.") % (self.name, amount))
        return True

    @api.depends(
        "line_ids.planned_amount", "line_ids.actual_amount",
        "expense_ids.amount", "expense_ids.state", "expense_ids.date",
        "campaign_id.operation_ids.state", "campaign_id.operation_ids.date",
        "campaign_id.operation_ids.line_ids.analysis_cost", "currency_id",
    )
    def _compute_totals(self):
        for budget in self:
            currency = budget.currency_id
            planned = sum(budget.line_ids.mapped("planned_amount"))
            # Actual amounts are computed from validated operations plus complementary expenses.
            operations = budget.campaign_id.operation_ids.filtered(
                lambda op: op.state == "done"
                and (not budget.date_start or op.date >= budget.date_start)
                and (not budget.date_end or op.date <= budget.date_end)
            )
            operation_actual = sum(operations.mapped("line_ids.analysis_cost"))
            # Native supplier invoices are added by agriculture_manage_account.
            # Legacy manual expense rows are intentionally not treated as accounting actuals.
            actual = operation_actual
            if currency:
                planned = currency.round(planned)
                actual = currency.round(actual)
            variance = actual - planned
            remaining = planned - actual
            budget.budget_total = planned
            budget.actual_total = actual
            budget.variance_total = currency.round(variance) if currency else variance
            budget.remaining_total = currency.round(remaining) if currency else remaining
            budget.consumption_rate = (actual / planned) if planned else 0.0
            budget.is_over_budget = actual > planned and bool(planned)

    def action_confirm(self):
        for budget in self:
            if not budget.line_ids:
                raise UserError(_("Ajoutez au moins une ligne de prévision avant de confirmer le budget."))
            budget.state = "confirmed"
        return True

    def action_close(self):
        self.write({"state": "closed"})
        return True

    def action_set_draft(self):
        self.write({"state": "draft"})
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    def action_view_campaign(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Campagne"),
            "res_model": "agriculture.farm.crop.campaign",
            "view_mode": "form",
            "res_id": self.campaign_id.id,
        }


class AgricultureFarmCropBudgetLine(models.Model):
    _name = "agriculture.farm.crop.budget.line"
    _description = "Ligne de budget agricole"
    _order = "budget_id, sequence, id"

    budget_id = fields.Many2one(
        "agriculture.farm.crop.budget", string="Budget", required=True,
        ondelete="cascade", index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Désignation", required=True)
    category = fields.Selection(OPERATION_TYPES, string="Catégorie", required=True, default="other")
    campaign_plot_id = fields.Many2one(
        "agriculture.farm.crop.campaign.plot", string="Parcelle de campagne",
        ondelete="restrict",
    )
    plot_id = fields.Many2one(
        "agriculture.farm.plot", string="Parcelle",
        related="campaign_plot_id.plot_id", store=True, readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="budget_id.currency_id", readonly=True,
    )
    planned_amount = fields.Monetary(
        string="Montant prévu", currency_field="currency_id", default=0.0,
    )
    actual_amount = fields.Monetary(
        string="Montant réel", currency_field="currency_id",
        compute="_compute_actual_amount", store=True,
    )
    variance_amount = fields.Monetary(
        string="Écart", currency_field="currency_id",
        compute="_compute_amounts", store=True,
    )
    remaining_amount = fields.Monetary(
        string="Restant", currency_field="currency_id",
        compute="_compute_amounts", store=True,
    )
    consumption_rate = fields.Float(string="Consommation (%)", compute="_compute_amounts", store=True)

    @api.constrains("campaign_plot_id", "budget_id")
    def _check_campaign_plot(self):
        for line in self:
            if line.campaign_plot_id and line.campaign_plot_id.campaign_id != line.budget_id.campaign_id:
                raise ValidationError(_("La parcelle doit appartenir à la campagne du budget."))

    @api.depends(
        "budget_id.campaign_id.operation_ids.state",
        "budget_id.campaign_id.operation_ids.date",
        "budget_id.campaign_id.operation_ids.operation_type",
        "budget_id.campaign_id.operation_ids.plot_id",
        "budget_id.campaign_id.operation_ids.line_ids.analysis_cost",
        "budget_id.expense_ids.amount", "budget_id.expense_ids.state",
        "budget_id.expense_ids.category", "budget_id.expense_ids.date",
        "budget_id.expense_ids.campaign_plot_id",
        "category", "campaign_plot_id", "budget_id.date_start", "budget_id.date_end",
    )
    def _compute_actual_amount(self):
        for line in self:
            budget = line.budget_id
            amount = 0.0
            if line.category in ("labor", "other_expense"):
                # Actual complementary expenses come from posted native vendor bills.
                # agriculture_manage_account extends this computation.
                amount = 0.0
            else:
                operations = budget.campaign_id.operation_ids.filtered(
                    lambda op: op.state == "done"
                    and op.operation_type == line.category
                    and (not budget.date_start or op.date >= budget.date_start)
                    and (not budget.date_end or op.date <= budget.date_end)
                    and (not line.campaign_plot_id or op.plot_id == line.campaign_plot_id.plot_id)
                )
                amount += sum(operations.mapped("line_ids.analysis_cost"))
            currency = budget.currency_id
            line.actual_amount = currency.round(amount) if currency else amount

    @api.depends("planned_amount", "actual_amount", "currency_id")
    def _compute_amounts(self):
        for line in self:
            currency = line.currency_id
            variance = line.actual_amount - line.planned_amount
            remaining = line.planned_amount - line.actual_amount
            line.variance_amount = currency.round(variance) if currency else variance
            line.remaining_amount = currency.round(remaining) if currency else remaining
            line.consumption_rate = (
                line.actual_amount / line.planned_amount
                if line.planned_amount else 0.0
            )


class AgricultureFarmCropBudgetExpense(models.Model):
    _name = "agriculture.farm.crop.budget.expense"
    _description = "Dépense complémentaire du budget agricole"
    _order = "date desc, id desc"

    name = fields.Char(string="Libellé", required=True)
    budget_id = fields.Many2one(
        "agriculture.farm.crop.budget", string="Budget", required=True,
        ondelete="cascade", index=True,
    )
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    category = fields.Selection([
        ("labor", "Main-d'œuvre"),
        ("other_expense", "Autres dépenses"),
    ], string="Catégorie", required=True, default="other_expense")
    campaign_plot_id = fields.Many2one(
        "agriculture.farm.crop.campaign.plot", string="Parcelle de campagne",
        ondelete="restrict",
    )
    partner_id = fields.Many2one("res.partner", string="Bénéficiaire / fournisseur")
    amount = fields.Monetary(string="Montant", currency_field="currency_id", required=True)
    currency_id = fields.Many2one(
        "res.currency", related="budget_id.currency_id", readonly=True,
    )
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("posted", "Comptabilisée"),
        ("cancelled", "Annulée"),
    ], string="État", default="draft", required=True)
    description = fields.Text(string="Description")

    @api.constrains("campaign_plot_id", "budget_id", "amount")
    def _check_expense(self):
        for expense in self:
            if expense.amount < 0:
                raise ValidationError(_("Le montant d'une dépense doit être positif ou nul."))
            if expense.campaign_plot_id and expense.campaign_plot_id.campaign_id != expense.budget_id.campaign_id:
                raise ValidationError(_("La parcelle doit appartenir à la campagne du budget."))

    def action_post(self):
        raise UserError(_(
            "Les dépenses réelles doivent être enregistrées dans les Mouvements financiers "
            "et validées par une facture fournisseur Odoo. Cette ligne historique ne crée "
            "aucune écriture comptable."
        ))

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    def action_set_draft(self):
        self.write({"state": "draft"})
        return True
