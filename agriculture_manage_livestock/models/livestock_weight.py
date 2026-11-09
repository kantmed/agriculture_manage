from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AgricultureLivestockWeight(models.Model):
    _name = "agriculture.livestock.weight"
    _description = "Pesée d'un animal"
    _order = "date desc, id desc"

    animal_id = fields.Many2one("agriculture.livestock.animal", required=True, ondelete="cascade")
    date = fields.Date(required=True, default=fields.Date.context_today)
    weight = fields.Float(required=True, digits=(16, 2))
    uom_id = fields.Many2one("uom.uom", required=True, default=lambda self: self.env.ref("uom.product_uom_kgm", raise_if_not_found=False))
    notes = fields.Char()

    @api.constrains("weight")
    def _check_weight(self):
        for rec in self:
            if rec.weight <= 0:
                raise ValidationError(_("Le poids doit être supérieur à zéro."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.animal_id.write({"current_weight": rec.weight, "weight_uom_id": rec.uom_id.id})
        return records
