from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MesComptesDebt(models.Model):
    _name = "mes.comptes.debt"
    _description = "Dette ou créance"
    _order = "date desc, id desc"

    name = fields.Char(required=True, string="Objet")
    debt_type = fields.Selection([("lent", "Somme prêtée (créance)"),
                                  ("borrowed", "Somme empruntée (dette)")],
                                 required=True, default="lent", string="Type")
    partner_name = fields.Char(required=True, string="Personne / organisme")
    date = fields.Date(required=True, default=fields.Date.context_today)
    due_date = fields.Date(string="Date d'échéance")
    reminder_days = fields.Integer(
        string="Rappel (jours avant échéance)",
        default=7,
        help="Nombre de jours avant la date d'échéance auquel un rappel est généré. 0 = pas de rappel."
    )
    account_id = fields.Many2one("mes.comptes.account", string="Compte associé", required=True, ondelete="restrict")
    amount = fields.Monetary(required=True, currency_field="currency_id", string="Montant initial")
    paid_amount = fields.Monetary(compute="_compute_paid_amount", currency_field="currency_id", string="Montant réglé")
    remaining_amount = fields.Monetary(compute="_compute_paid_amount", currency_field="currency_id", string="Reste à régler")
    currency_id = fields.Many2one(related="account_id.currency_id", store=True, readonly=True)
    payment_ids = fields.One2many("mes.comptes.debt.payment", "debt_id", string="Règlements")
    state = fields.Selection([("open", "En cours"), ("paid", "Soldée"), ("cancel", "Annulée")],
                             compute="_compute_state", store=True, string="Statut")
    is_due_soon = fields.Boolean(
        compute="_compute_due_soon", search="_search_is_due_soon",
        string="Échéance approchante",
        help="La date d'échéance est dans moins de N jours (N = rappel)."
    )
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    note = fields.Text()

    @api.depends("due_date", "reminder_days", "state")
    def _compute_due_soon(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.state != "open" or not rec.due_date or rec.reminder_days <= 0:
                rec.is_due_soon = False
                continue
            days_left = (rec.due_date - today).days
            rec.is_due_soon = 0 <= days_left <= rec.reminder_days

    def _search_is_due_soon(self, operator, value):
        """Recherche des échéances proches (champ calculé, donc non stocké)."""
        if operator not in ("=", "!="):
            raise ValidationError(_("Opérateur non pris en charge pour « Échéance approchante »."))
        positive = (operator == "=") == bool(value)
        due_ids = [debt.id for debt in self.search([]) if debt.is_due_soon]
        return [("id", "in" if positive else "not in", due_ids)]

    @api.depends("amount", "payment_ids.amount", "payment_ids.state")
    def _compute_paid_amount(self):
        for rec in self:
            paid = sum(rec.payment_ids.filtered(lambda p: p.state == "posted").mapped("amount"))
            rec.paid_amount = paid
            rec.remaining_amount = max(rec.amount - paid, 0)

    @api.depends("amount", "payment_ids.amount", "payment_ids.state")
    def _compute_state(self):
        for rec in self:
            paid = sum(rec.payment_ids.filtered(lambda p: p.state == "posted").mapped("amount"))
            remaining = max(rec.amount - paid, 0)
            rec.state = "paid" if rec.amount and remaining == 0 else "open"

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Le montant doit être strictement positif."))

    def action_view_reminders(self):
        """Ouvre la liste des dettes avec rappel actif et non soldées."""
        return {
            "name": _("Dettes à échéance"),
            "type": "ir.actions.act_window",
            "res_model": "mes.comptes.debt",
            "view_mode": "list",
            "domain": [
                ("state", "=", "open"),
                ("due_date", "!=", False),
                ("reminder_days", ">", 0),
                "|", ("user_id", "=", self.env.uid), ("account_id.user_ids", "in", [self.env.uid]),
            ],
        }


class MesComptesDebtPayment(models.Model):
    _name = "mes.comptes.debt.payment"
    _description = "Règlement de dette ou créance"
    _order = "date desc, id desc"

    debt_id = fields.Many2one("mes.comptes.debt", required=True, ondelete="cascade")
    date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="debt_id.currency_id", store=True, readonly=True)
    account_id = fields.Many2one("mes.comptes.account", string="Compte utilisé", required=True, ondelete="restrict")
    state = fields.Selection([("draft", "Brouillon"), ("posted", "Validé"), ("cancel", "Annulé")],
                             default="draft", required=True)
    transaction_id = fields.Many2one("mes.comptes.transaction", string="Opération générée", readonly=True, copy=False)
    note = fields.Char()

    @api.constrains("amount", "account_id", "debt_id")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Le montant doit être strictement positif."))
            if rec.debt_id.currency_id and rec.account_id.currency_id != rec.debt_id.currency_id:
                raise ValidationError(_("Le compte de règlement doit utiliser la même devise que la dette ou créance."))

    def action_post(self):
        for rec in self:
            debt = rec.debt_id
            already = sum(debt.payment_ids.filtered(lambda p: p.state == "posted" and p != rec).mapped("amount"))
            if already + rec.amount > debt.amount:
                raise ValidationError(_("Le total des règlements dépasse le montant initial."))
        for rec in self:
            if not rec.transaction_id:
                tx_type = "income" if rec.debt_id.debt_type == "lent" else "expense"
                label = _("Remboursement reçu : %s") % rec.debt_id.name if tx_type == "income" else _("Remboursement payé : %s") % rec.debt_id.name
                tx = self.env["mes.comptes.transaction"].create({
                    "name": label,
                    "transaction_type": tx_type,
                    "date": rec.date,
                    "account_id": rec.account_id.id,
                    "amount": rec.amount,
                    "state": "posted",
                    "user_id": rec.debt_id.user_id.id,
                    "reference": "DEBT-%s" % rec.id,
                })
                rec.transaction_id = tx.id
            else:
                rec.transaction_id.write({"state": "posted"})
            rec.state = "posted"
        return True

    def action_cancel(self):
        for rec in self:
            if rec.transaction_id:
                rec.transaction_id.write({"state": "cancel"})
            rec.state = "cancel"
        return True
