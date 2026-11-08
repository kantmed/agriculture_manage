from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MesComptesAccount(models.Model):
    _name = "mes.comptes.account"
    _description = "Compte personnel"
    _order = "name"

    name = fields.Char(string="Nom du compte", required=True)
    code = fields.Char(string="Référence")
    account_type = fields.Selection([
        ("cash", "Espèces"),
        ("bank", "Compte bancaire"),
        ("savings", "Épargne"),
        ("other", "Autre"),
    ], string="Type", required=True, default="cash")
    currency_id = fields.Many2one(
        "res.currency", string="Devise",
        required=True, default=lambda self: self.env.company.currency_id
    )
    opening_balance = fields.Monetary(string="Solde initial", currency_field="currency_id", default=0.0)
    transaction_ids = fields.One2many("mes.comptes.transaction", "account_id", string="Opérations")
    outgoing_transfer_ids = fields.One2many("mes.comptes.transfer", "source_account_id", string="Virements sortants")
    incoming_transfer_ids = fields.One2many("mes.comptes.transfer", "destination_account_id", string="Virements entrants")
    current_balance = fields.Monetary(
        string="Solde actuel", currency_field="currency_id",
        compute="_compute_current_balance", store=True
    )
    active = fields.Boolean(default=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    user_ids = fields.Many2many("res.users", string="Utilisateurs partagés")
    note = fields.Text(string="Notes")

    @api.depends(
        "opening_balance",
        "transaction_ids.amount", "transaction_ids.transaction_type", "transaction_ids.state",
        "outgoing_transfer_ids.amount", "outgoing_transfer_ids.state",
        "incoming_transfer_ids.destination_amount", "incoming_transfer_ids.state",
    )
    def _compute_current_balance(self):
        for account in self:
            txs = account.transaction_ids.filtered(lambda x: x.state == "posted")
            income = sum(txs.filtered(lambda x: x.transaction_type == "income").mapped("amount"))
            expense = sum(txs.filtered(lambda x: x.transaction_type == "expense").mapped("amount"))
            outgoing = sum(account.outgoing_transfer_ids.filtered(lambda x: x.state == "posted").mapped("amount"))
            incoming = sum(account.incoming_transfer_ids.filtered(
                lambda x: x.state == "posted"
            ).mapped("destination_amount"))
            account.current_balance = account.opening_balance + income - expense - outgoing + incoming

    def action_refresh_balance(self):
        for account in self:
            account._compute_current_balance()
        return True

    @api.constrains("opening_balance")
    def _check_opening_balance(self):
        for record in self:
            if record.opening_balance < 0:
                raise ValidationError(_("Le solde initial ne peut pas être négatif."))
