from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MesComptesReminder(models.Model):
    _name = "mes.comptes.reminder"
    _description = "Rappel financier Mes Comptes"
    _order = "date desc, id desc"
    _rec_name = "message"

    reminder_type = fields.Selection([
        ("debt_due", "Dette à échéance"),
        ("budget_overdraft", "Budget dépassé"),
    ], required=True, string="Type")
    date = fields.Date(required=True, default=fields.Date.context_today)
    message = fields.Char(required=True, string="Message")
    res_model = fields.Char(required=True, string="Modèle concerné")
    res_id = fields.Integer(required=True, string="Enregistrement concerné")
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, index=True)
    read = fields.Boolean(default=False, string="Lu")

    def action_view_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    def action_mark_read(self):
        self.write({"read": True})
        return True

    @api.model
    def _generate_reminders(self):
        """Génère les rappels pour les dettes à échéance et les budgets dépassés."""
        today = fields.Date.context_today(self)
        Reminder = self.env["mes.comptes.reminder"].sudo()
        Debt = self.env["mes.comptes.debt"].sudo()
        Budget = self.env["mes.comptes.budget"].sudo()

        # Dettes à échéance
        debts = Debt.search([
            ("state", "=", "open"),
            ("due_date", "!=", False),
            ("reminder_days", ">", 0),
        ])
        for debt in debts:
            days_left = (debt.due_date - today).days
            if 0 <= days_left <= debt.reminder_days:
                existing = Reminder.search([
                    ("reminder_type", "=", "debt_due"),
                    ("res_model", "=", "mes.comptes.debt"),
                    ("res_id", "=", debt.id),
                    ("date", "=", today),
                ])
                if not existing:
                    label = _("Dette à échéance : %s") % debt.name
                    users = (debt.account_id.user_ids | debt.account_id.user_id)
                    for user in users:
                        if not user.share:
                            Reminder.create({
                                "reminder_type": "debt_due",
                                "date": today,
                                "message": label,
                                "res_model": "mes.comptes.debt",
                                "res_id": debt.id,
                                "user_id": user.id,
                            })

        # Budgets dépassés
        budgets = Budget.search([
            ("active", "=", True),
            ("is_overdraft", "=", True),
        ])
        for budget in budgets:
            existing = Reminder.search([
                ("reminder_type", "=", "budget_overdraft"),
                ("res_model", "=", "mes.comptes.budget"),
                ("res_id", "=", budget.id),
                ("date", "=", today),
            ])
            if not existing:
                label = _("Budget dépassé : %s (%.0f%%)") % (budget.name, budget.usage_percent)
                users = budget.user_id
                if users and not users.share:
                    Reminder.create({
                        "reminder_type": "budget_overdraft",
                        "date": today,
                        "message": label,
                        "res_model": "mes.comptes.budget",
                        "res_id": budget.id,
                        "user_id": users.id,
                    })
        return True