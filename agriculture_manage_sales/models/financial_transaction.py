from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AgricultureFinancialTransaction(models.Model):
    _inherit = "agriculture.farm.financial.transaction"

    sale_order_id = fields.Many2one(
        "sale.order", string="Commande client", index=True,
        ondelete="restrict", copy=False,
    )

    @api.constrains("sale_order_id", "partner_id", "campaign_id", "company_id", "transaction_type", "category")
    def _check_sale_order_link(self):
        for transaction in self:
            order = transaction.sale_order_id
            if not order:
                continue
            if transaction.transaction_type != "income" or transaction.category != "crop_sales":
                raise ValidationError(_("Une commande agricole doit être liée à une recette de vente de récolte."))
            if transaction.company_id != order.company_id:
                raise ValidationError(_("La société du mouvement doit correspondre à celle de la commande."))
            if transaction.partner_id and transaction.partner_id != order.partner_id:
                raise ValidationError(_("Le client du mouvement doit correspondre au client de la commande."))
            if transaction.campaign_id and order.agriculture_campaign_id and transaction.campaign_id != order.agriculture_campaign_id:
                raise ValidationError(_("La campagne du mouvement ne correspond pas à la commande."))
