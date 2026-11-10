from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AgricultureLivestockHerd(models.Model):
    _name = "agriculture.livestock.herd"
    _description = "Lot d'élevage"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "farm_id, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(readonly=True, copy=False, default="Nouveau")
    farm_id = fields.Many2one("agriculture.farm", required=True, ondelete="cascade", tracking=True)
    site_id = fields.Many2one("agriculture.farm.site", domain="[('farm_id', '=', farm_id)]", ondelete="restrict")
    company_id = fields.Many2one(related="farm_id.company_id", store=True, readonly=True)
    species_id = fields.Many2one("agriculture.livestock.species", required=True, ondelete="restrict")
    breed_id = fields.Many2one("agriculture.livestock.breed", domain="[('species_id', '=', species_id)]", ondelete="restrict")
    tracking_mode = fields.Selection([("individual", "Individuel"), ("batch", "Par lot")], required=True, default="batch")
    purpose = fields.Selection([
        ("meat", "Viande"), ("milk", "Lait"), ("breeding", "Reproduction"),
        ("fattening", "Engraissement"), ("eggs", "Œufs"), ("wool", "Laine"), ("other", "Autres productions")
    ], default="other")
    location_id = fields.Many2one("agriculture.livestock.location", domain="[('farm_id', '=', farm_id)]", ondelete="restrict")
    quantity = fields.Float(string="Effectif collectif", default=0.0)
    animal_ids = fields.One2many("agriculture.livestock.animal", "herd_id")
    health_event_ids = fields.One2many("agriculture.livestock.health", "herd_id", string="Suivi sanitaire")
    individual_count = fields.Integer(compute="_compute_individual_count")
    headcount = fields.Float(compute="_compute_headcount", store=True)
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.depends("tracking_mode", "quantity", "animal_ids", "animal_ids.state")
    def _compute_individual_count(self):
        for rec in self:
            alive = rec.animal_ids.filtered(lambda a: a.state == "active")
            rec.individual_count = len(alive)

    @api.depends("tracking_mode", "quantity", "animal_ids", "animal_ids.state")
    def _compute_headcount(self):
        for rec in self:
            alive = rec.animal_ids.filtered(lambda a: a.state == "active")
            rec.headcount = float(len(alive)) if rec.tracking_mode == "individual" else rec.quantity

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                vals["code"] = self.env["ir.sequence"].next_by_code("agriculture.livestock.herd") or "Nouveau"
        return super().create(vals_list)

    @api.constrains("site_id", "farm_id", "location_id", "species_id", "breed_id", "tracking_mode", "quantity")
    def _check_consistency(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(_("Le site doit appartenir à la même exploitation."))
            if rec.location_id and rec.location_id.farm_id != rec.farm_id:
                raise ValidationError(_("L'emplacement doit appartenir à la même exploitation."))
            if rec.breed_id and rec.breed_id.species_id != rec.species_id:
                raise ValidationError(_("La race doit correspondre à l'espèce."))
            if rec.quantity < 0:
                raise ValidationError(_("L'effectif ne peut pas être négatif."))
            if rec.tracking_mode == "individual" and rec.quantity:
                raise ValidationError(_("L'effectif individuel est calculé à partir des fiches animaux."))
