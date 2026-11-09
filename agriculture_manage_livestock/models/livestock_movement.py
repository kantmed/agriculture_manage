from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AgricultureLivestockMovement(models.Model):
    _name = "agriculture.livestock.movement"
    _description = "Mouvement de cheptel"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(readonly=True, copy=False, default="Nouveau")
    date = fields.Date(required=True, default=fields.Date.context_today)
    movement_type = fields.Selection([
        ("incoming", "Entrée / Achat"), ("birth", "Naissance"), ("transfer", "Transfert"),
        ("sale", "Vente"), ("death", "Mortalité"), ("reform", "Réforme"), ("adjustment", "Ajustement")
    ], required=True)
    tracking_mode = fields.Selection([("individual", "Individuel"), ("batch", "Par lot")], required=True)
    farm_id = fields.Many2one("agriculture.farm", required=True, ondelete="restrict")
    company_id = fields.Many2one(related="farm_id.company_id", store=True, readonly=True)
    species_id = fields.Many2one("agriculture.livestock.species", required=True)
    animal_id = fields.Many2one("agriculture.livestock.animal", domain="[('farm_id', '=', farm_id), ('state', '=', 'active')]")
    source_herd_id = fields.Many2one("agriculture.livestock.herd", domain="[('farm_id', '=', farm_id)]")
    destination_herd_id = fields.Many2one("agriculture.livestock.herd", domain="[('farm_id', '=', farm_id)]")
    quantity = fields.Float(default=1.0)
    state = fields.Selection([("draft", "Brouillon"), ("done", "Appliqué"), ("cancel", "Annulé")], default="draft", tracking=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code("agriculture.livestock.movement") or "Nouveau"
        return super().create(vals_list)

    @api.constrains("animal_id", "source_herd_id", "destination_herd_id", "farm_id", "species_id", "tracking_mode", "movement_type", "quantity")
    def _check_movement(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(_("La quantité doit être strictement positive."))
            if rec.tracking_mode == "individual":
                if not rec.animal_id or rec.animal_id.farm_id != rec.farm_id or rec.animal_id.species_id != rec.species_id:
                    raise ValidationError(_("Sélectionnez un animal de l'exploitation et de l'espèce indiquées."))
                if rec.quantity != 1:
                    raise ValidationError(_("Un mouvement individuel porte sur une seule unité."))
                if rec.movement_type == "transfer" and not rec.destination_herd_id:
                    raise ValidationError(_("Sélectionnez le lot de destination pour le transfert."))
                if rec.destination_herd_id and rec.destination_herd_id.tracking_mode != "individual":
                    raise ValidationError(_("Le lot de destination doit être suivi individuellement."))
            else:
                if rec.animal_id:
                    raise ValidationError(_("Ne sélectionnez pas d'animal pour un mouvement par lot."))
                if rec.movement_type not in ("incoming", "birth") and not rec.source_herd_id:
                    raise ValidationError(_("Sélectionnez le lot source."))
                if rec.movement_type in ("incoming", "birth", "transfer") and not rec.destination_herd_id:
                    raise ValidationError(_("Sélectionnez le lot destination."))
            for herd in (rec.source_herd_id, rec.destination_herd_id):
                if herd and (herd.farm_id != rec.farm_id or herd.species_id != rec.species_id):
                    raise ValidationError(_("Les lots doivent correspondre à l'exploitation et à l'espèce."))
            if rec.source_herd_id and rec.destination_herd_id and rec.source_herd_id == rec.destination_herd_id:
                raise ValidationError(_("Les lots source et destination doivent être différents."))

    def action_apply(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Seul un mouvement en brouillon peut être appliqué."))
            if rec.tracking_mode == "individual":
                animal = rec.animal_id
                if rec.movement_type == "transfer":
                    animal.herd_id = rec.destination_herd_id
                    animal.site_id = rec.destination_herd_id.site_id
                elif rec.movement_type == "sale":
                    animal.state = "sold"
                elif rec.movement_type == "death":
                    animal.state = "dead"
                elif rec.movement_type == "reform":
                    animal.state = "reformed"
            else:
                source, dest = rec.source_herd_id, rec.destination_herd_id
                if rec.movement_type in ("incoming", "birth"):
                    dest.quantity += rec.quantity
                elif rec.movement_type == "transfer":
                    if source.quantity < rec.quantity:
                        raise UserError(_("L'effectif du lot source est insuffisant."))
                    source.quantity -= rec.quantity
                    dest.quantity += rec.quantity
                elif rec.movement_type in ("sale", "death", "reform"):
                    if source.quantity < rec.quantity:
                        raise UserError(_("L'effectif du lot source est insuffisant."))
                    source.quantity -= rec.quantity
                elif rec.movement_type == "adjustment":
                    source.quantity += rec.quantity
            rec.state = "done"
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("Un mouvement appliqué ne peut pas être annulé directement. Créez un mouvement correctif."))
            rec.state = "cancel"
        return True
