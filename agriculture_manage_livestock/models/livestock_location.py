from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AgricultureLivestockLocation(models.Model):
    _name = "agriculture.livestock.location"
    _description = "Emplacement d'élevage"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "farm_id, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(readonly=True, copy=False, default="Nouveau")
    farm_id = fields.Many2one("agriculture.farm", required=True, ondelete="cascade", tracking=True)
    site_id = fields.Many2one("agriculture.farm.site", domain="[('farm_id', '=', farm_id)]", ondelete="restrict")
    company_id = fields.Many2one(related="farm_id.company_id", store=True, readonly=True)
    location_type = fields.Selection([
        ("barn", "Bâtiment / Étable"), ("pen", "Parc / Enclos"),
        ("poultry_house", "Poulailler"), ("pasture", "Pâturage"),
        ("apiary", "Rucher"), ("quarantine", "Quarantaine"), ("other", "Autre")
    ], required=True, default="other")
    capacity = fields.Float()
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                vals["code"] = self.env["ir.sequence"].next_by_code("agriculture.livestock.location") or "Nouveau"
        return super().create(vals_list)

    @api.constrains("site_id", "farm_id", "capacity")
    def _check_location(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(_("Le site doit appartenir à la même exploitation."))
            if rec.capacity < 0:
                raise ValidationError(_("La capacité ne peut pas être négative."))
