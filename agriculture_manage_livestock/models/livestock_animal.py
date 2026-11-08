from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AgricultureLivestockAnimal(models.Model):
    _name = "agriculture.livestock.animal"
    _description = "Animal"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "farm_id, name"

    name = fields.Char(string="Nom / Identification", required=True, tracking=True)
    code = fields.Char(string="Numéro interne", readonly=True, copy=False, default="Nouveau", index=True)
    identification_number = fields.Char(string="Boucle / Identifiant externe", index=True, tracking=True)
    farm_id = fields.Many2one("agriculture.farm", required=True, ondelete="cascade", tracking=True)
    site_id = fields.Many2one("agriculture.farm.site", domain="[('farm_id', '=', farm_id)]", ondelete="restrict")
    company_id = fields.Many2one(related="farm_id.company_id", store=True, readonly=True)
    species_id = fields.Many2one("agriculture.livestock.species", required=True, ondelete="restrict")
    breed_id = fields.Many2one("agriculture.livestock.breed", domain="[('species_id', '=', species_id)]", ondelete="restrict")
    herd_id = fields.Many2one("agriculture.livestock.herd", domain="[('farm_id', '=', farm_id), ('tracking_mode', '=', 'individual')]", ondelete="restrict")
    sex = fields.Selection([("male", "Mâle"), ("female", "Femelle"), ("unknown", "Inconnu")], default="unknown", required=True)
    birth_date = fields.Date()
    entry_date = fields.Date(default=fields.Date.context_today, required=True)
    origin = fields.Selection([("purchase", "Achat"), ("birth", "Naissance"), ("transfer", "Transfert"), ("other", "Autre")], default="purchase", required=True)
    state = fields.Selection([("active", "Actif"), ("sold", "Vendu"), ("dead", "Mort"), ("reformed", "Réformé"), ("transferred", "Transféré")], default="active", required=True, tracking=True)
    current_weight = fields.Float(digits=(16, 2))
    weight_uom_id = fields.Many2one("uom.uom", default=lambda self: self.env.ref("uom.product_uom_kgm", raise_if_not_found=False))
    weight_ids = fields.One2many("agriculture.livestock.weight", "animal_id")
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                vals["code"] = self.env["ir.sequence"].next_by_code("agriculture.livestock.animal") or "Nouveau"
        return super().create(vals_list)

    @api.constrains("site_id", "farm_id", "herd_id", "species_id", "breed_id", "birth_date", "entry_date")
    def _check_consistency(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(_("Le site doit appartenir à la même exploitation."))
            if rec.herd_id:
                if rec.herd_id.farm_id != rec.farm_id or rec.herd_id.tracking_mode != "individual":
                    raise ValidationError(_("Le lot doit appartenir à la même exploitation et être suivi individuellement."))
                if rec.herd_id.species_id != rec.species_id:
                    raise ValidationError(_("L'espèce de l'animal doit correspondre à celle du lot."))
            if rec.breed_id and rec.breed_id.species_id != rec.species_id:
                raise ValidationError(_("La race doit correspondre à l'espèce."))
            if rec.birth_date and rec.entry_date and rec.birth_date > rec.entry_date:
                raise ValidationError(_("La date de naissance doit précéder la date d'entrée."))
            if rec.birth_date and rec.birth_date > fields.Date.context_today(rec):
                raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))
