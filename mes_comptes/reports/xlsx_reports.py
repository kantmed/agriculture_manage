from odoo import models, _


class MesComptesXlsxCommon(models.AbstractModel):
    _name = "report.mes_comptes.xlsx_common"
    _inherit = "report.report_xlsx.abstract"
    _description = "Outils communs d'export Excel Mes Comptes"

    def _write_rows(self, workbook, sheet, headers, rows):
        header_format = workbook.add_format({"bold": True, "bg_color": "#E9ECEF"})
        sheet.write_row(0, 0, headers, header_format)
        for row_number, row in enumerate(rows, start=1):
            for column, value in enumerate(row):
                if isinstance(value, str):
                    sheet.write_string(row_number, column, value)
                else:
                    sheet.write(row_number, column, value)
        sheet.freeze_panes(1, 0)
        sheet.autofilter(0, 0, len(rows), len(headers) - 1)
        sheet.set_column(0, len(headers) - 1, 18)


class MesComptesTransactionsXlsx(models.AbstractModel):
    _name = "report.mes_comptes.transactions_xlsx"
    _inherit = "report.mes_comptes.xlsx_common"
    _description = "Export Excel des opérations Mes Comptes"

    def generate_xlsx_report(self, workbook, data, transactions):
        sheet = workbook.add_worksheet(_("Opérations"))
        headers = [_("Date"), _("Libellé"), _("Nature"), _("Compte"), _("Catégorie"),
                   _("Montant"), _("Devise"), _("Statut"), _("Référence")]
        self._write_rows(workbook, sheet, headers, [
            [
                str(tx.date or ""), tx.name,
                dict(tx._fields["transaction_type"]._description_selection(self.env)).get(tx.transaction_type),
                tx.account_id.name, tx.category_id.name or "",
                tx.amount, tx.currency_id.name,
                dict(tx._fields["state"]._description_selection(self.env)).get(tx.state), tx.reference or "",
            ]
            for tx in transactions
        ])


class MesComptesAccountsXlsx(models.AbstractModel):
    _name = "report.mes_comptes.accounts_xlsx"
    _inherit = "report.mes_comptes.xlsx_common"
    _description = "Export Excel des comptes Mes Comptes"

    def generate_xlsx_report(self, workbook, data, accounts):
        sheet = workbook.add_worksheet(_("Comptes"))
        headers = [_("Nom du compte"), _("Type"), _("Référence"), _("Devise"),
                   _("Solde initial"), _("Solde actuel"), _("Active")]
        self._write_rows(workbook, sheet, headers, [
            [
                account.name,
                dict(account._fields["account_type"]._description_selection(self.env)).get(account.account_type),
                account.code or "",
                account.currency_id.name, account.opening_balance,
                account.current_balance,
                self.env._("Oui") if account.active else self.env._("Non"),
            ]
            for account in accounts
        ])


class MesComptesBudgetsXlsx(models.AbstractModel):
    _name = "report.mes_comptes.budgets_xlsx"
    _inherit = "report.mes_comptes.xlsx_common"
    _description = "Export Excel des budgets Mes Comptes"

    def generate_xlsx_report(self, workbook, data, budgets):
        sheet = workbook.add_worksheet(_("Budgets"))
        headers = [_("Nom du budget"), _("Catégorie"), _("Du"), _("Au"), _("Devise"),
                   _("Montant prévu"), _("Dépensé"), _("Disponible"), _("Utilisation (%)")]
        self._write_rows(workbook, sheet, headers, [
            [
                budget.name, budget.category_id.name, str(budget.date_start or ""),
                str(budget.date_end or ""), budget.currency_id.name,
                budget.planned_amount, budget.spent_amount,
                budget.remaining_amount, budget.usage_percent,
            ]
            for budget in budgets
        ])


class MesComptesTransfersXlsx(models.AbstractModel):
    _name = "report.mes_comptes.transfers_xlsx"
    _inherit = "report.mes_comptes.xlsx_common"
    _description = "Export Excel des virements Mes Comptes"

    def generate_xlsx_report(self, workbook, data, transfers):
        sheet = workbook.add_worksheet(_("Virements"))
        headers = [_("Date"), _("Libellé"), _("Compte source"), _("Compte destinataire"),
                   _("Devise source"), _("Montant débité"), _("Devise destinataire"),
                   _("Montant crédité"), _("Taux de change"), _("Statut")]
        self._write_rows(workbook, sheet, headers, [
            [
                str(t.date or ""), t.name,
                t.source_account_id.name, t.destination_account_id.name,
                t.currency_id.name, t.amount,
                t.destination_currency_id.name, t.destination_amount,
                t.exchange_rate,
                dict(t._fields["state"]._description_selection(self.env)).get(t.state),
            ]
            for t in transfers
        ])


class MesComptesDebtsXlsx(models.AbstractModel):
    _name = "report.mes_comptes.debts_xlsx"
    _inherit = "report.mes_comptes.xlsx_common"
    _description = "Export Excel des dettes Mes Comptes"

    def generate_xlsx_report(self, workbook, data, debts):
        sheet = workbook.add_worksheet(_("Dettes et créances"))
        headers = [_("Objet"), _("Type"), _("Personne"), _("Date"), _("Échéance"),
                   _("Montant initial"), _("Montant réglé"), _("Reste à régler"), _("Devise"), _("Statut")]
        self._write_rows(workbook, sheet, headers, [
            [
                d.name, dict(d._fields["debt_type"]._description_selection(self.env)).get(d.debt_type),
                d.partner_name, str(d.date or ""), str(d.due_date or ""),
                d.amount, d.paid_amount, d.remaining_amount,
                d.currency_id.name,
                dict(d._fields["state"]._description_selection(self.env)).get(d.state),
            ]
            for d in debts
        ])


class MesComptesDebtPaymentsXlsx(models.AbstractModel):
    _name = "report.mes_comptes.debt_payments_xlsx"
    _inherit = "report.mes_comptes.xlsx_common"
    _description = "Export Excel des règlements de dettes Mes Comptes"

    def generate_xlsx_report(self, workbook, data, payments):
        sheet = workbook.add_worksheet(_("Règlements de dettes"))
        headers = [_("Date"), _("Dette / créance"), _("Compte utilisé"), _("Devise"), _("Montant"), _("Statut")]
        self._write_rows(workbook, sheet, headers, [
            [
                str(p.date or ""), p.debt_id.name, p.account_id.name,
                p.currency_id.name, p.amount,
                dict(p._fields["state"]._description_selection(self.env)).get(p.state),
            ]
            for p in payments
        ])
