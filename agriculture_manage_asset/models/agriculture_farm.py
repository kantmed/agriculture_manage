from odoo import fields, models


class AgricultureFarm(models.Model):
    _inherit = "agriculture.farm"

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Compte analytique",
        check_company=True,
        ondelete="restrict",
        domain="[('company_id', '=', company_id)]",
        help="Compte analytique utilisé pour imputer les amortissements des immobilisations agricoles à cette exploitation.",
    )
