from odoo import fields, models, _
from odoo.exceptions import ValidationError


class MesComptesFinancialReportWizard(models.TransientModel):
    _name = "mes.comptes.report.wizard"
    _description = "Assistant de rapport financier"

    date_start = fields.Date(required=True, string="Du", default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_end = fields.Date(required=True, string="Au", default=fields.Date.context_today)

    def _check_dates(self):
        self.ensure_one()
        if self.date_end < self.date_start:
            raise ValidationError(_("La date de fin doit être postérieure ou égale à la date de début."))

    def action_preview_report(self):
        """Ouvre l'aperçu HTML du rapport dans le navigateur (onglet séparé)."""
        self._check_dates()
        return self.env.ref("mes_comptes.action_report_mes_financial_html").report_action(
            self, config=False
        )

    def action_print_report(self):
        """Génère et télécharge le PDF."""
        self._check_dates()
        report = self.env.ref("mes_comptes.action_report_mes_financial")
        return report.report_action(self)

