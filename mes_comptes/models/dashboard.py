from odoo import api, models
from odoo.fields import Date
from dateutil.relativedelta import relativedelta


class MesComptesDashboard(models.AbstractModel):
    _name = "mes.comptes.dashboard"
    _description = "Données du tableau de bord Mes Comptes"

    @api.model
    def get_dashboard_data(self, reference_date=None):
        today = Date.context_today(self)
        ref = Date.to_date(reference_date) if reference_date else today
        month_start = ref.replace(day=1)
        next_month = month_start + relativedelta(months=1)
        previous_month_start = month_start - relativedelta(months=1)
        year_start = ref.replace(month=1, day=1)
        previous_year_start = year_start - relativedelta(years=1)
        previous_year_end = year_start - relativedelta(days=1)
        chart_start = month_start - relativedelta(months=11)

        tx_model = self.env["mes.comptes.transaction"]
        account_model = self.env["mes.comptes.account"]

        account_domain = [
            ("active", "=", True),
            "|", ("user_id", "=", self.env.uid), ("user_ids", "in", [self.env.uid]),
        ]
        tx_domain = [
            ("state", "=", "posted"),
            ("date", ">=", previous_year_start),
            ("date", "<", next_month),
            "|", ("user_id", "=", self.env.uid), ("account_id.user_ids", "in", [self.env.uid]),
        ]

        def period_totals(currency, date_from, date_to):
            """Agrège les recettes/dépenses d'une devise sur une période (SQL)."""
            groups = tx_model._read_group(
                tx_domain + [
                    ("currency_id", "=", currency.id),
                    ("date", ">=", date_from),
                    ("date", "<", date_to),
                ],
                ["transaction_type"],
                ["amount:sum"],
            )
            totals = {"income": 0.0, "expense": 0.0}
            for transaction_type, amount in groups:
                if transaction_type in totals:
                    totals[transaction_type] = amount or 0.0
            totals["net"] = totals["income"] - totals["expense"]
            return totals

        def currency_info(currency):
            return {
                "currency_id": currency.id,
                "currency_name": currency.name,
            }

        # Soldes par devise : lecture agrégée du champ stocké, sans parcourir les comptes.
        balance_rows = account_model._read_group(
            account_domain, ["currency_id"], ["current_balance:sum"]
        )
        balances = {
            currency.id: amount or 0.0
            for currency, amount in balance_rows
            if currency
        }
        # Devises réellement utilisées (comptes + opérations de la période analysée).
        tx_currency_rows = tx_model._read_group(tx_domain, ["currency_id"], [])
        currency_ids = set(balances)
        for (currency,) in tx_currency_rows:
            if currency:
                currency_ids.add(currency.id)
        currencies = self.env["res.currency"].browse(sorted(currency_ids))

        balance_by_currency = []
        monthly_by_currency = []
        yearly_by_currency = []
        charts_by_currency = []

        for currency in currencies:
            current_month = period_totals(currency, month_start, next_month)
            previous_month = period_totals(currency, previous_month_start, month_start)
            current_year = period_totals(currency, year_start, ref + relativedelta(days=1))
            previous_year = period_totals(
                currency, previous_year_start, previous_year_end + relativedelta(days=1)
            )

            balance_by_currency.append({
                **currency_info(currency),
                "balance": balances.get(currency.id, 0.0),
            })
            monthly_by_currency.append({
                **currency_info(currency),
                **current_month,
                "previous": previous_month,
            })
            yearly_by_currency.append({
                **currency_info(currency),
                **current_year,
                "previous": previous_year,
            })

            # Évolution sur 12 mois, agrégée directement par mois en SQL.
            trend_groups = tx_model._read_group(
                tx_domain + [
                    ("currency_id", "=", currency.id),
                    ("date", ">=", chart_start),
                    ("date", "<", next_month),
                ],
                ["date:month", "transaction_type"],
                ["amount:sum"],
            )
            trend = {}
            for month_value, transaction_type, amount in trend_groups:
                if not month_value:
                    continue
                values = trend.setdefault(
                    (month_value.year, month_value.month),
                    {"income": 0.0, "expense": 0.0},
                )
                if transaction_type in values:
                    values[transaction_type] = amount or 0.0

            monthly_trend = []
            for offset in range(12):
                period_start = chart_start + relativedelta(months=offset)
                values = trend.get((period_start.year, period_start.month), {})
                income = values.get("income", 0.0)
                expense = values.get("expense", 0.0)
                monthly_trend.append({
                    "label": period_start.strftime("%m/%y"),
                    "income": income,
                    "expense": expense,
                    "net": income - expense,
                })
            charts_by_currency.append({
                **currency_info(currency),
                "monthly_trend": monthly_trend,
            })

        accounts = account_model.search(account_domain)
        account_types = dict(
            account_model._fields["account_type"]._description_selection(self.env)
        )
        month_domain = [
            ("state", "=", "posted"),
            ("date", ">=", month_start), ("date", "<", next_month),
            "|", ("user_id", "=", self.env.uid), ("account_id.user_ids", "in", [self.env.uid]),
        ]
        return {
            "reference_date": str(ref),
            "balance_by_currency": balance_by_currency,
            "monthly_by_currency": monthly_by_currency,
            "yearly_by_currency": yearly_by_currency,
            "charts_by_currency": charts_by_currency,
            "accounts": [{
                "id": a.id, "name": a.name,
                "type": account_types.get(a.account_type),
                "balance": a.current_balance or 0.0,
                "currency_id": a.currency_id.id,
            } for a in accounts],
            "recent_transactions": [{
                "id": t.id, "name": t.name, "date": str(t.date),
                "type": t.transaction_type, "amount": t.amount,
                "currency_id": t.currency_id.id,
            } for t in tx_model.search(month_domain, order="date desc, id desc", limit=10)],
        }
