from odoo import api, fields, models, _


class AgricultureFarmCropBudget(models.Model):
    _inherit = "agriculture.farm.crop.budget"

    financial_transaction_ids = fields.One2many(
        "agriculture.farm.financial.transaction", "budget_id",
        string="Mouvements financiers liés",
    )
    account_move_ids = fields.One2many(
        "account.move", "agriculture_budget_id", string="Factures comptables liées",
    )
    accounting_expense_total = fields.Monetary(
        string="Dépenses comptabilisées (factures fournisseurs)",
        currency_field="currency_id", compute="_compute_totals", store=True,
    )

    def _get_budget_accounting_moves(self):
        self.ensure_one()
        domain = [
            ("agriculture_budget_id", "=", self.id),
            ("company_id", "=", self.company_id.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("in_invoice", "in_refund")),
        ]
        moves = self.env["account.move"].search(domain)
        return moves.filtered(lambda move: (
            (not move.agriculture_financial_transaction_id
             or move.agriculture_financial_transaction_id.state == "posted")
            and (not self.date_start or (move.invoice_date or move.date) >= self.date_start)
            and (not self.date_end or (move.invoice_date or move.date) <= self.date_end)
        ))

    def _get_budget_invoice_expense(self, moves=None, category=None, plot=None):
        self.ensure_one()
        moves = moves if moves is not None else self._get_budget_accounting_moves()
        total = 0.0
        for move in moves:
            # Costs already included in a validated agricultural operation are not counted twice.
            transaction = move.agriculture_financial_transaction_id
            if move.agriculture_operation_id or (transaction and transaction.operation_id):
                continue
            move_category = "labor" if transaction and transaction.category == "labor" else "other_expense"
            if category and move_category != category:
                continue
            if plot:
                move_plot = move.agriculture_plot_id or (transaction.plot_id if transaction else False)
                if move_plot != plot:
                    continue
            # Use the posted journal-item balance (company currency), excluding taxes.
            # Storable products are excluded here: their cost enters the budget when consumed
            # by an agricultural operation, not when the supplier invoice is received.
            invoice_lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
                and not (line.product_id and line.product_id.is_storable)
            )
            total += sum(invoice_lines.mapped("balance"))
        return total

    @api.depends(
        "line_ids.planned_amount", "line_ids.actual_amount",
        "expense_ids.amount", "expense_ids.state", "expense_ids.date",
        "campaign_id.operation_ids.state", "campaign_id.operation_ids.date",
        "campaign_id.operation_ids.line_ids.analysis_cost", "currency_id",
        "account_move_ids.state", "account_move_ids.move_type",
        "account_move_ids.amount_untaxed_signed", "account_move_ids.invoice_date",
        "account_move_ids.date", "account_move_ids.agriculture_operation_id",
        "account_move_ids.invoice_line_ids.balance",
        "account_move_ids.invoice_line_ids.product_id.is_storable",
        "financial_transaction_ids.state",
        "financial_transaction_ids.account_move_id.state",
        "financial_transaction_ids.account_move_id.amount_untaxed_signed",
        "financial_transaction_ids.account_move_id.invoice_date",
        "financial_transaction_ids.account_move_id.move_type",
        "financial_transaction_ids.account_move_id.agriculture_operation_id",
        "financial_transaction_ids.operation_id",
        "date_start", "date_end", "company_id",
    )
    def _compute_totals(self):
        super()._compute_totals()
        for budget in self:
            moves = budget._get_budget_accounting_moves()
            accounting_actual = budget._get_budget_invoice_expense(moves)
            currency = budget.currency_id
            if currency:
                accounting_actual = currency.round(accounting_actual)
            budget.accounting_expense_total = accounting_actual
            actual = budget.actual_total + accounting_actual
            if currency:
                actual = currency.round(actual)
            budget.actual_total = actual
            budget.variance_total = currency.round(actual - budget.budget_total) if currency else actual - budget.budget_total
            budget.remaining_total = currency.round(budget.budget_total - actual) if currency else budget.budget_total - actual
            budget.consumption_rate = actual / budget.budget_total if budget.budget_total else 0.0
            budget.is_over_budget = actual > budget.budget_total and bool(budget.budget_total)


class AgricultureFarmCropBudgetLine(models.Model):
    _inherit = "agriculture.farm.crop.budget.line"

    @api.depends(
        "budget_id.campaign_id.operation_ids.state",
        "budget_id.campaign_id.operation_ids.date",
        "budget_id.campaign_id.operation_ids.operation_type",
        "budget_id.campaign_id.operation_ids.plot_id",
        "budget_id.campaign_id.operation_ids.line_ids.analysis_cost",
        "budget_id.expense_ids.amount", "budget_id.expense_ids.state",
        "budget_id.expense_ids.category", "budget_id.expense_ids.date",
        "budget_id.expense_ids.campaign_plot_id",
        "budget_id.account_move_ids.state", "budget_id.account_move_ids.move_type",
        "budget_id.account_move_ids.amount_untaxed_signed", "budget_id.account_move_ids.invoice_date",
        "budget_id.account_move_ids.date", "budget_id.account_move_ids.agriculture_operation_id",
        "budget_id.account_move_ids.invoice_line_ids.balance",
        "budget_id.account_move_ids.invoice_line_ids.product_id.is_storable",
        "budget_id.financial_transaction_ids.state",
        "budget_id.financial_transaction_ids.account_move_id.state",
        "budget_id.financial_transaction_ids.account_move_id.amount_untaxed_signed",
        "budget_id.financial_transaction_ids.account_move_id.invoice_date",
        "budget_id.financial_transaction_ids.account_move_id.move_type",
        "budget_id.financial_transaction_ids.account_move_id.agriculture_operation_id",
        "budget_id.financial_transaction_ids.category",
        "budget_id.financial_transaction_ids.operation_id",
        "budget_id.date_start", "budget_id.date_end",
        "campaign_plot_id", "category",
    )
    def _compute_actual_amount(self):
        super()._compute_actual_amount()
        for line in self:
            if line.category not in ("labor", "other_expense"):
                continue
            budget = line.budget_id
            moves = budget._get_budget_accounting_moves()
            amount = budget._get_budget_invoice_expense(
                moves=moves,
                category=line.category,
                plot=line.campaign_plot_id.plot_id if line.campaign_plot_id else False,
            )
            currency = budget.currency_id
            line.actual_amount = currency.round(amount) if currency else amount
