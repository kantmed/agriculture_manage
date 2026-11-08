from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MesComptesBudget(models.Model):
    _name = "mes.comptes.budget"
    _description = "Budget par catégorie"
    _order = "date_start desc, name"

    name = fields.Char(required=True, string="Nom du budget")
    category_id = fields.Many2one("mes.comptes.category", required=True, string="Catégorie", ondelete="restrict")
    date_start = fields.Date(required=True, string="Du")
    date_end = fields.Date(required=True, string="Au")
    planned_amount = fields.Monetary(required=True, currency_field="currency_id", string="Montant prévu")
    spent_amount = fields.Monetary(compute="_compute_spent", currency_field="currency_id", string="Dépensé")
    remaining_amount = fields.Monetary(compute="_compute_spent", currency_field="currency_id", string="Disponible")
    usage_percent = fields.Float(compute="_compute_spent", string="Utilisation (%)")
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    active = fields.Boolean(default=True)
    is_overdraft = fields.Boolean(
        compute="_compute_is_overdraft",
        search="_search_is_overdraft",
        string="Budget dépassé",
        help="Le montant dépensé dépasse le montant prévu."
    )

    @api.depends("category_id", "date_start", "date_end", "planned_amount", "user_id", "currency_id")
    def _compute_spent(self):
        Transaction = self.env["mes.comptes.transaction"]
        for budget in self:
            if not (budget.category_id and budget.date_start and budget.date_end):
                budget.spent_amount = 0.0
                budget.remaining_amount = budget.planned_amount
                budget.usage_percent = 0.0
                continue
            domain = [
                ("transaction_type", "=", "expense"), ("state", "=", "posted"),
                ("category_id", "=", budget.category_id.id),
                ("date", ">=", budget.date_start), ("date", "<=", budget.date_end),
                ("currency_id", "=", budget.currency_id.id),
                "|",
                ("user_id", "=", budget.user_id.id),
                ("account_id.user_ids", "in", [budget.user_id.id]),
            ]
            spent = Transaction._read_group(domain, [], ["amount:sum"])
            budget.spent_amount = (spent[0][0] or 0.0) if spent else 0.0
            budget.remaining_amount = budget.planned_amount - budget.spent_amount
            budget.usage_percent = (budget.spent_amount / budget.planned_amount * 100) if budget.planned_amount else 0

    @api.depends("spent_amount", "planned_amount")
    def _compute_is_overdraft(self):
        for budget in self:
            budget.is_overdraft = budget.spent_amount > budget.planned_amount

    def _search_is_overdraft(self, operator, value):
        """Recherche des budgets dépassés (le champ est calculé, donc non stocké)."""
        if operator not in ("=", "!="):
            raise ValidationError(_("Opérateur non pris en charge pour « Budget dépassé »."))
        positive = (operator == "=") == bool(value)
        overdraft_ids = [
            budget.id
            for budget in self.search([])
            if budget.spent_amount > budget.planned_amount
        ]
        return [("id", "in" if positive else "not in", overdraft_ids)]

    @api.constrains("date_start", "date_end", "planned_amount", "category_id")
    def _check_budget(self):
        for rec in self:
            if rec.date_end < rec.date_start:
                raise ValidationError(_("La date de fin doit être postérieure à la date de début."))
            if rec.planned_amount <= 0:
                raise ValidationError(_("Le montant prévu doit être strictement positif."))
            if rec.category_id and rec.category_id.transaction_type != "expense":
                raise ValidationError(_("Un budget doit être associé à une catégorie de dépense."))
