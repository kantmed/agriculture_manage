# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GestAgriProcurementRequestLine(models.Model):
    _name = "gest_agri.procurement.request.line"
    _description = "Ligne de demande d'approvisionnement"
    _order = "sequence, id"

    request_id = fields.Many2one(
        "gest_agri.procurement.request", string="Demande", required=True,
        ondelete="cascade", index=True,
    )
    farm_id = fields.Many2one(
        related="request_id.farm_id", string="Exploitation", store=True,
        readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="request_id.company_id", string="Société", store=True,
        readonly=True, precompute=True, index=True,
    )

    product_id = fields.Many2one(
        "product.product", string="Produit / Intrant", required=True,
        ondelete="restrict", index=True,
    )
    product_uom_id = fields.Many2one(
        "uom.uom", string="Unité de mesure", ondelete="restrict",
    )
    quantity = fields.Float(string="Quantité demandée", required=True, digits=(16, 3))
    needed_date = fields.Date(string="Date de besoin")
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
                raise ValidationError(self.env._("La quantité demandée doit être strictement positive."))

    @api.constrains("product_id", "request_id")
    def _check_farm_coherence(self):
        for line in self:
            if line.request_id and line.product_id:
                # Product must be accessible (read) by the user
                line.product_id.check_access("read")