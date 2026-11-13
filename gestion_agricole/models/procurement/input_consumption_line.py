# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GestAgriInputConsumptionLine(models.Model):
    _name = "gest_agri.input.consumption.line"
    _description = "Ligne de consommation d'intrant"
    _order = "sequence, id"

    consumption_id = fields.Many2one(
        "gest_agri.input.consumption", string="Consommation", required=True,
        ondelete="cascade", index=True,
    )
    farm_id = fields.Many2one(
        related="consumption_id.farm_id", string="Exploitation", store=True,
        readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="consumption_id.company_id", string="Société", store=True,
        readonly=True, precompute=True, index=True,
    )

    product_id = fields.Many2one(
        "product.product", string="Produit / Intrant", required=True,
        ondelete="restrict", index=True,
    )
    product_uom_id = fields.Many2one(
        "uom.uom", string="Unité de mesure", ondelete="restrict",
    )
    quantity = fields.Float(string="Quantité consommée", required=True, digits=(16, 3))
    notes = fields.Text(string="Observations")
    sequence = fields.Integer(string="Séquence", default=10)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(self.env._("La quantité consommée doit être strictement positive."))