from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    agriculture_farm_id = fields.Many2one("agriculture.farm", string="Exploitation", index=True, ondelete="restrict", check_company=True)
    agriculture_campaign_id = fields.Many2one("agriculture.farm.crop.campaign", string="Campagne agricole", index=True, ondelete="restrict", check_company=True)
    agriculture_plot_id = fields.Many2one("agriculture.farm.plot", string="Parcelle", index=True, ondelete="restrict", check_company=True)
    agriculture_operation_id = fields.Many2one("agriculture.farm.operation", string="Opération agricole", index=True, ondelete="restrict", check_company=True)
    agriculture_harvest_id = fields.Many2one("agriculture.farm.harvest", string="Récolte", index=True, ondelete="restrict", check_company=True)
    agriculture_budget_id = fields.Many2one("agriculture.farm.crop.budget", string="Budget agricole", index=True, ondelete="restrict", check_company=True)
    agriculture_financial_transaction_id = fields.Many2one(
        "agriculture.farm.financial.transaction", string="Mouvement financier agricole",
        index=True, copy=False, ondelete="restrict", check_company=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            budget_id = vals.get("agriculture_budget_id")
            if budget_id:
                budget = self.env["agriculture.farm.crop.budget"].browse(budget_id)
                vals.setdefault("agriculture_farm_id", budget.farm_id.id)
                vals.setdefault("agriculture_campaign_id", budget.campaign_id.id)
        moves = super().create(vals_list)
        for move in moves.filtered(lambda rec: rec.move_type in ("out_invoice", "in_invoice", "out_refund", "in_refund")):
            distribution = move._get_agriculture_analytic_distribution()
            if distribution:
                lines = move.invoice_line_ids.filtered(lambda line: line.display_type == "product" and not line.analytic_distribution)
                if lines:
                    lines.write({"analytic_distribution": distribution})
        return moves

    @api.constrains("agriculture_budget_id", "company_id", "move_type")
    def _check_agriculture_budget(self):
        for move in self:
            if move.agriculture_budget_id:
                if move.move_type not in ("in_invoice", "in_refund"):
                    raise ValidationError(_("Un budget de dépenses ne peut être associé qu'à une facture ou un avoir fournisseur."))
                if move.agriculture_budget_id.company_id != move.company_id:
                    raise ValidationError(_("Le budget agricole et la facture doivent appartenir à la même société."))

    def _get_agriculture_analytic_distribution(self):
        self.ensure_one()
        farm = self.agriculture_farm_id
        campaign = self.agriculture_campaign_id
        plot = self.agriculture_plot_id
        if self.agriculture_operation_id:
            operation = self.agriculture_operation_id
            campaign = campaign or operation.campaign_id
            farm = farm or campaign.farm_id
            plot = plot or operation.plot_id
        if self.agriculture_harvest_id:
            harvest = self.agriculture_harvest_id
            campaign = campaign or harvest.campaign_id
            farm = farm or campaign.farm_id
            plot = plot or harvest.plot_id
        accounts = self.env["account.analytic.account"]
        for account in (
            farm.analytic_account_id if farm else False,
            campaign.analytic_account_id if campaign else False,
            plot.analytic_account_id if plot else False,
        ):
            if account:
                if account.company_id and account.company_id != self.company_id:
                    continue
                accounts |= account
        if not accounts:
            return {}
        return {",".join(map(str, sorted(accounts.ids))): 100.0}

    def write(self, vals):
        vals = dict(vals)
        budget_id = vals.get("agriculture_budget_id")
        if budget_id:
            budget = self.env["agriculture.farm.crop.budget"].browse(budget_id)
            vals.setdefault("agriculture_campaign_id", budget.campaign_id.id)
            vals.setdefault("agriculture_farm_id", budget.farm_id.id)
        result = super().write(vals)
        analytic_fields = {
            "agriculture_farm_id", "agriculture_campaign_id", "agriculture_plot_id",
            "agriculture_operation_id", "agriculture_harvest_id", "agriculture_budget_id",
        }
        if analytic_fields.intersection(vals):
            for move in self.filtered(lambda rec: rec.move_type in ("out_invoice", "in_invoice", "out_refund", "in_refund")):
                distribution = move._get_agriculture_analytic_distribution()
                if distribution:
                    lines = move.invoice_line_ids.filtered(lambda line: line.display_type == "product" and not line.analytic_distribution)
                    if lines:
                        lines.write({"analytic_distribution": distribution})
        return result
