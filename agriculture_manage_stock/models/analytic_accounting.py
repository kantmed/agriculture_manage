from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AgricultureFarm(models.Model):
    _inherit = "agriculture.farm"

    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Compte analytique de l'exploitation",
        ondelete="restrict", check_company=True,
        help="Compte analytique Odoo utilisé pour ventiler les écritures de stock de cette exploitation.",
    )

    @api.constrains("analytic_account_id", "company_id")
    def _check_farm_analytic_company(self):
        for farm in self:
            account = farm.analytic_account_id
            if account and account.company_id and account.company_id != farm.company_id:
                raise ValidationError(_("Le compte analytique de l'exploitation doit appartenir à la même société."))


class AgricultureFarmCropCampaign(models.Model):
    _inherit = "agriculture.farm.crop.campaign"

    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Compte analytique de la campagne",
        ondelete="restrict", check_company=True,
        help="Compte analytique Odoo utilisé pour ventiler les coûts de cette campagne.",
    )

    @api.constrains("analytic_account_id", "company_id")
    def _check_campaign_analytic_company(self):
        for campaign in self:
            account = campaign.analytic_account_id
            if account and account.company_id and account.company_id != campaign.company_id:
                raise ValidationError(_("Le compte analytique de la campagne doit appartenir à la même société."))


class AgricultureFarmPlot(models.Model):
    _inherit = "agriculture.farm.plot"

    company_id = fields.Many2one(
        "res.company", related="farm_id.company_id", store=True, readonly=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account", string="Compte analytique de la parcelle",
        ondelete="restrict", check_company=True,
        help="Compte analytique Odoo utilisé pour ventiler les coûts de cette parcelle.",
    )

    @api.constrains("analytic_account_id", "farm_id")
    def _check_plot_analytic_company(self):
        for plot in self:
            account = plot.analytic_account_id
            if account and account.company_id and account.company_id != plot.farm_id.company_id:
                raise ValidationError(_("Le compte analytique de la parcelle doit appartenir à la même société que l'exploitation."))


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Odoo stock_account links the valuation journal entry to its source stock.move.
        # Apply analytics only to expense counterpart lines, not to the stock asset line,
        # so the analytic cost is not duplicated or cancelled by the balancing entry.
        for line in lines.filtered(lambda aml: not aml.analytic_distribution):
            move = line.move_id
            stock_move = move.stock_move_id if "stock_move_id" in move._fields else self.env["stock.move"]
            operation_line = stock_move.agriculture_operation_line_id if stock_move and "agriculture_operation_line_id" in stock_move._fields else self.env["agriculture.farm.operation.line"]
            if not operation_line:
                continue
            if line.account_id.account_type not in ("expense", "expense_direct_cost"):
                continue
            operation = operation_line.operation_id
            campaign = operation.campaign_id
            farm = operation.farm_id
            plot = operation.plot_id
            analytic_accounts = self.env["account.analytic.account"]
            candidates = [farm.analytic_account_id if farm else False]
            if campaign:
                candidates.append(campaign.analytic_account_id)
            if plot:
                candidates.append(plot.analytic_account_id)
            # A project analytic account is included when the optional project
            # bridge exposes it; stock remains installable without that bridge.
            if "project_id" in operation._fields and operation.project_id and "analytic_account_id" in operation.project_id._fields:
                candidates.append(operation.project_id.analytic_account_id)
            for analytic_account in candidates:
                if analytic_account:
                    if analytic_account.company_id and analytic_account.company_id != line.company_id:
                        raise ValidationError(_("Un compte analytique lié à l'opération ne correspond pas à la société de l'écriture."))
                    analytic_accounts |= analytic_account
            # A single 100% distribution key combines the dimensions (one account per plan).
            # Odoo then creates native analytic items when the journal entry is posted.
            if analytic_accounts:
                distribution_key = ",".join(str(account_id) for account_id in sorted(analytic_accounts.ids))
                line.analytic_distribution = {distribution_key: 100.0}
        return lines
