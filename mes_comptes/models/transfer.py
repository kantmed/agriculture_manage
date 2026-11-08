from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MesComptesTransfer(models.Model):
    _name = "mes.comptes.transfer"
    _description = "Virement entre comptes"
    _order = "date desc, id desc"

    name = fields.Char(string="Libellé", required=True, default=lambda self: _("Virement"))
    date = fields.Date(required=True, default=fields.Date.context_today)
    source_account_id = fields.Many2one("mes.comptes.account", required=True, string="Compte source", ondelete="restrict")
    destination_account_id = fields.Many2one("mes.comptes.account", required=True, string="Compte destinataire", ondelete="restrict")
    amount = fields.Monetary(required=True, currency_field="currency_id", string="Montant débité")
    currency_id = fields.Many2one(related="source_account_id.currency_id", store=True, readonly=True)
    destination_currency_id = fields.Many2one(related="destination_account_id.currency_id", store=True, readonly=True)
    exchange_rate = fields.Float(string="Taux de change", digits=(16, 8), default=1.0,
                                 help="Nombre d'unités de la devise destinataire pour une unité de la devise source.")
    exchange_rate_manual = fields.Boolean(string="Taux manuel", default=False)
    destination_amount = fields.Monetary(string="Montant crédité", currency_field="destination_currency_id",
                                         compute="_compute_destination_amount", store=True)
    state = fields.Selection([("draft", "Brouillon"), ("posted", "Validé"), ("cancel", "Annulé")],
                             default="draft", required=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    note = fields.Text()

    @api.model
    def _get_historical_rate(self, source, destination, date):
        if not source or not destination or source == destination:
            return 1.0
        return source._convert(
            1.0, destination, company=self.env.company, date=date, round=False
        )

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals = []
        for vals in vals_list:
            vals = vals.copy()
            if "exchange_rate" in vals and "exchange_rate_manual" not in vals:
                vals["exchange_rate_manual"] = True
            if not vals.get("exchange_rate_manual"):
                source = self.env["mes.comptes.account"].browse(vals.get("source_account_id")).currency_id
                destination = self.env["mes.comptes.account"].browse(vals.get("destination_account_id")).currency_id
                date = fields.Date.to_date(vals.get("date") or fields.Date.context_today(self))
                vals["exchange_rate"] = self._get_historical_rate(source, destination, date)
            prepared_vals.append(vals)
        return super().create(prepared_vals)

    def write(self, vals):
        vals = vals.copy()
        if "exchange_rate" in vals and "exchange_rate_manual" not in vals:
            vals["exchange_rate_manual"] = True
        if "exchange_rate_manual" in vals and vals["exchange_rate_manual"]:
            return super().write(vals)
        rate_inputs_changed = bool(
            {"date", "source_account_id", "destination_account_id", "exchange_rate_manual"} & vals.keys()
        )
        if not rate_inputs_changed:
            return super().write(vals)
        for transfer in self:
            transfer_vals = vals.copy()
            manual = transfer_vals.get("exchange_rate_manual", transfer.exchange_rate_manual)
            if not manual:
                source = self.env["mes.comptes.account"].browse(
                    transfer_vals.get("source_account_id", transfer.source_account_id.id)
                ).currency_id
                destination = self.env["mes.comptes.account"].browse(
                    transfer_vals.get("destination_account_id", transfer.destination_account_id.id)
                ).currency_id
                date = fields.Date.to_date(transfer_vals.get("date", transfer.date))
                transfer_vals["exchange_rate"] = self._get_historical_rate(source, destination, date)
            super(MesComptesTransfer, transfer).write(transfer_vals)
        return True

    @api.onchange("date", "source_account_id", "destination_account_id", "exchange_rate_manual")
    def _onchange_historical_rate(self):
        for rec in self:
            if not rec.exchange_rate_manual:
                rec.exchange_rate = self._get_historical_rate(
                    rec.source_account_id.currency_id,
                    rec.destination_account_id.currency_id,
                    rec.date,
                )

    @api.depends("amount", "exchange_rate", "currency_id", "destination_currency_id")
    def _compute_destination_amount(self):
        for rec in self:
            if rec.currency_id and rec.destination_currency_id and rec.currency_id == rec.destination_currency_id:
                rec.destination_amount = rec.amount
            else:
                rec.destination_amount = rec.amount * rec.exchange_rate

    @api.constrains("source_account_id", "destination_account_id", "exchange_rate")
    def _check_accounts_and_rate(self):
        for rec in self:
            if rec.source_account_id and rec.source_account_id == rec.destination_account_id:
                raise ValidationError(_("Les deux comptes doivent être différents."))
            if rec.currency_id and rec.destination_currency_id and rec.currency_id == rec.destination_currency_id and rec.exchange_rate != 1.0:
                raise ValidationError(_("Le taux doit être égal à 1 lorsque les devises sont identiques."))
            if rec.currency_id and rec.destination_currency_id and rec.currency_id != rec.destination_currency_id and rec.exchange_rate <= 0:
                raise ValidationError(_("Le taux de change doit être strictement positif."))

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Le montant doit être strictement positif."))

    def action_post(self):
        for rec in self:
            if rec.source_account_id.current_balance < rec.amount:
                raise ValidationError(_("Le solde du compte source est insuffisant."))
        self.write({"state": "posted"})
        return True

    def action_cancel(self):
        self.write({"state": "cancel"})
        return True
