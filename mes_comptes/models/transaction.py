from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MesComptesTransaction(models.Model):
    _name = "mes.comptes.transaction"
    _description = "Recette ou dépense"
    _order = "date desc, id desc"

    name = fields.Char(string="Libellé", required=True)
    transaction_type = fields.Selection([
        ("income", "Recette"), ("expense", "Dépense")
    ], required=True, default="expense", string="Nature")
    date = fields.Date(required=True, default=fields.Date.context_today)
    account_id = fields.Many2one("mes.comptes.account", required=True, string="Compte", ondelete="restrict")
    category_id = fields.Many2one("mes.comptes.category", string="Catégorie")
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="account_id.currency_id", store=True, readonly=True)
    partner_name = fields.Char(string="Tiers")
    reference = fields.Char(string="Référence")
    payment_method = fields.Selection([
        ("cash", "Espèces"), ("card", "Carte"), ("transfer", "Virement"), ("other", "Autre")
    ], string="Mode de paiement", default="cash")
    state = fields.Selection([
        ("draft", "Brouillon"), ("posted", "Validée"), ("cancel", "Annulée")
    ], default="draft", required=True, string="Statut")
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    note = fields.Text(string="Notes")

    @api.constrains("amount")
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Le montant doit être strictement positif."))

    @api.constrains("category_id", "transaction_type")
    def _check_category_type(self):
        for record in self:
            if record.category_id and record.category_id.transaction_type != record.transaction_type:
                raise ValidationError(_("La catégorie doit correspondre à la nature de l'opération."))

    def action_post(self):
        self.write({"state": "posted"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        self.write({"state": "draft"})
        return True
