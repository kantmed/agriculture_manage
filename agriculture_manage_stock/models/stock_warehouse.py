from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    farm_id = fields.Many2one(
        "agriculture.farm",
        string="Exploitation agricole",
        index=True,
        ondelete="restrict",
        help="Exploitation à laquelle ce magasin est rattaché. Laisser vide pour un entrepôt général.",
    )

    @api.constrains("farm_id", "company_id")
    def _check_farm_company(self):
        for warehouse in self:
            if warehouse.farm_id and warehouse.farm_id.company_id != warehouse.company_id:
                raise ValidationError(_("Le magasin et l'exploitation doivent appartenir à la même société."))
