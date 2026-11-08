from odoo import api, models


class MesComptesFinancialReport(models.AbstractModel):
    _name = "report.mes_comptes.report_financial"
    _description = "Rapport financier Mes Comptes"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env["mes.comptes.report.wizard"].browse(docids).exists()
        wizard.ensure_one()
        date_start = wizard.date_start
        date_end = wizard.date_end
        user_id = self.env.uid

        transactions = self.env["mes.comptes.transaction"].search([
            ("state", "=", "posted"),
            ("date", ">=", date_start),
            ("date", "<=", date_end),
            "|", ("user_id", "=", user_id), ("account_id.user_ids", "in", [user_id]),
        ], order="date, id")
        currencies = transactions.mapped("currency_id")
        totals = []
        for currency in currencies:
            currency_transactions = transactions.filtered(lambda tx: tx.currency_id == currency)
            income = sum(currency_transactions.filtered(
                lambda tx: tx.transaction_type == "income"
            ).mapped("amount"))
            expense = sum(currency_transactions.filtered(
                lambda tx: tx.transaction_type == "expense"
            ).mapped("amount"))
            totals.append({
                "currency": currency,
                "income": income,
                "expense": expense,
                "net": income - expense,
            })

        transfers = self.env["mes.comptes.transfer"].search([
            ("state", "=", "posted"),
            ("date", ">=", date_start),
            ("date", "<=", date_end),
            "|", "|",
            ("user_id", "=", user_id),
            ("source_account_id.user_ids", "in", [user_id]),
            ("destination_account_id.user_ids", "in", [user_id]),
        ], order="date, id")

        debt_payments = self.env["mes.comptes.debt.payment"].search([
            ("state", "=", "posted"),
            ("date", ">=", date_start),
            ("date", "<=", date_end),
            "|",
            ("debt_id.user_id", "=", user_id),
            ("debt_id.account_id.user_ids", "in", [user_id]),
        ], order="date, id")

        return {
            "doc_ids": wizard.ids,
            "doc_model": wizard._name,
            "docs": wizard,
            "transactions": transactions,
            "totals": totals,
            "transfers": transfers,
            "debt_payments": debt_payments,
        }