from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AgricultureFinancialAccount(models.Model):
    _name = "agriculture.farm.financial.account"
    _description = "Compte financier agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "company_id, name"

    name = fields.Char(string="Nom du compte", required=True, tracking=True)
    code = fields.Char(string="Référence", required=True, copy=False, tracking=True)
    account_type = fields.Selection(
        [("cash", "Caisse"), ("bank", "Banque"), ("other", "Autre")],
        string="Type", required=True, default="cash", tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Société", required=True,
        default=lambda self: self.env.company, index=True,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    journal_id = fields.Many2one(
        "account.journal", string="Journal comptable",
        domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]",
        help="Lien facultatif vers le journal comptable Odoo correspondant.",
    )
    opening_balance = fields.Monetary(
        string="Solde initial", currency_field="currency_id", default=0.0,
        help="Solde disponible à la date de mise en service du compte.",
    )
    active = fields.Boolean(default=True)
    payment_ids = fields.One2many(
        "agriculture.farm.financial.payment", "account_id", string="Règlements",
    )
    incoming_transfer_ids = fields.One2many(
        "agriculture.farm.financial.transaction", "destination_account_id",
        string="Virements entrants", domain=[("transaction_type", "=", "transfer"), ("state", "=", "posted")],
    )
    outgoing_transfer_ids = fields.One2many(
        "agriculture.farm.financial.transaction", "account_id",
        string="Virements sortants", domain=[("transaction_type", "=", "transfer"), ("state", "=", "posted")],
    )
    balance = fields.Monetary(
        string="Solde", currency_field="currency_id", compute="_compute_balance",
    )

    _company_code_unique = models.Constraint(
        "UNIQUE(company_id, code)",
        "Cette référence existe déjà pour cette société.",
    )

    @api.depends(
        "opening_balance", "payment_ids.amount", "payment_ids.state", "payment_ids.transaction_id.transaction_type",
        "incoming_transfer_ids.amount", "incoming_transfer_ids.state",
        "outgoing_transfer_ids.amount", "outgoing_transfer_ids.state",
    )
    def _compute_balance(self):
        for account in self:
            balance = account.opening_balance or 0.0
            for payment in account.payment_ids.filtered(lambda p: p.state == "posted"):
                sign = 1.0 if payment.transaction_id.transaction_type == "income" else -1.0
                balance += sign * payment.amount
            balance += sum(account.incoming_transfer_ids.mapped("amount"))
            balance -= sum(account.outgoing_transfer_ids.mapped("amount"))
            account.balance = account.currency_id.round(balance)

    @api.constrains("journal_id", "company_id", "currency_id")
    def _check_journal_company(self):
        for account in self:
            if account.journal_id and account.journal_id.company_id != account.company_id:
                raise ValidationError(_("Le journal doit appartenir à la même société que le compte financier."))
            if account.journal_id and account.journal_id.currency_id and account.journal_id.currency_id != account.currency_id:
                raise ValidationError(_("La devise du journal doit correspondre à celle du compte financier."))
