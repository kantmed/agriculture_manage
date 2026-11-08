from odoo import fields, models


class AgricultureFarmOperationLine(models.Model):
    _name = "agriculture.farm.operation.line"
    _description = "Ligne d'opération culturale"
    _order = "operation_id, id"

    operation_id = fields.Many2one(
        "agriculture.farm.operation",
        string="Opération",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        "product.product",
        string="Produit",
    )
    provider_id = fields.Many2one(
        "res.partner",
        string="Prestataire",
        domain="[('supplier_rank', '>', 0)]",
    )
    name = fields.Char(
        string="Intrant / prestation",
        required=True,
    )
    quantity = fields.Float(
        string="Quantité",
        default=1.0,
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unité",
    )
    cost = fields.Float(
        string="Coût",
    )
    notes = fields.Char(string="Notes")
