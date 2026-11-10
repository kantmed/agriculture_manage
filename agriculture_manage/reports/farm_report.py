from odoo import api, models


class AgricultureFarmReport(models.AbstractModel):
    _name = "report.agriculture_manage.farm_report"
    _description = "Rapport des exploitations agricoles"

    @api.model
    def _get_report_values(self, docids, data=None):
        farms = self.env["agriculture.farm"].browse(docids)
        return {
            "doc_ids": farms.ids,
            "doc_model": "agriculture.farm",
            "docs": farms,
        }
