from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AgricultureLivestockProduction(models.Model):
    _name = "agriculture.livestock.production"
    _description = "Production animale"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Référence", readonly=True, copy=False,
        default="Nouveau", tracking=True,
    )
    date = fields.Date(
        string="Date de production / collecte", required=True,
        default=fields.Date.context_today, tracking=True, index=True,
    )
    production_type = fields.Selection([
        ("milk", "Lait"),
        ("eggs", "Œufs"),
        ("wool", "Laine"),
        ("honey", "Miel"),
        ("meat", "Viande"),
        ("other", "Autre production"),
    ], string="Type de production", required=True, default="milk", tracking=True)

    animal_id = fields.Many2one(
        "agriculture.livestock.animal", string="Animal",
        ondelete="restrict", index=True,
        domain="[('state', '=', 'active')]",
    )
    herd_id = fields.Many2one(
        "agriculture.livestock.herd", string="Lot",
        ondelete="restrict", index=True,
        domain="[('active', '=', True)]",
    )
    farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation",
        compute="_compute_target", store=True, readonly=True, index=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Société",
        compute="_compute_target", store=True, readonly=True, index=True,
    )
    species_id = fields.Many2one(
        "agriculture.livestock.species", string="Espèce",
        compute="_compute_target", store=True, readonly=True, index=True,
    )
    headcount = fields.Float(
        string="Effectif concerné", required=True, default=1.0,
        readonly=True, tracking=True,
        help="Effectif mémorisé au moment de l'enregistrement de la production.",
    )

    product_description = fields.Char(
        string="Produit / variété", tracking=True,
        help="Précisez le produit si le type est « Autre production ».",
    )
    quantity = fields.Float(
        string="Quantité produite", required=True, default=0.0,
        digits="Product Unit of Measure", tracking=True,
    )
    uom_id = fields.Many2one(
        "uom.uom", string="Unité de mesure", required=True,
        ondelete="restrict",
    )
    quantity_per_head = fields.Float(
        string="Quantité par tête", compute="_compute_quantity_per_head",
        digits="Product Unit of Measure",
    )
    quality = fields.Selection([
        ("standard", "Standard"),
        ("good", "Bonne"),
        ("premium", "Premium"),
        ("rejected", "Non conforme"),
    ], string="Qualité")
    collection_reference = fields.Char(
        string="Référence de collecte / lot",
        help="Référence facultative du bidon, lot, collecte ou contenant.",
    )
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("done", "Enregistrée"),
        ("cancel", "Annulée"),
    ], string="État", default="draft", required=True, tracking=True)
    recorded_by = fields.Many2one(
        "res.users", string="Enregistré par",
        default=lambda self: self.env.user, readonly=True,
    )
    notes = fields.Text(string="Observations")

    @api.depends(
        "animal_id.farm_id", "animal_id.company_id", "animal_id.species_id",
        "herd_id.farm_id", "herd_id.company_id", "herd_id.species_id",
    )
    def _compute_target(self):
        for rec in self:
            farm = rec.animal_id.farm_id or rec.herd_id.farm_id
            rec.farm_id = farm
            rec.company_id = farm.company_id
            rec.species_id = rec.animal_id.species_id or rec.herd_id.species_id

    @api.depends("quantity", "headcount")
    def _compute_quantity_per_head(self):
        for rec in self:
            rec.quantity_per_head = rec.quantity / rec.headcount if rec.headcount else 0.0

    @api.onchange("animal_id", "herd_id")
    def _onchange_target(self):
        for rec in self:
            if rec.animal_id:
                rec.headcount = 1.0
                rec.herd_id = False
            elif rec.herd_id:
                rec.headcount = rec.herd_id.headcount
                rec.animal_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "agriculture.livestock.production"
                ) or "Nouveau"
            if vals.get("animal_id"):
                vals["headcount"] = 1.0
            elif vals.get("herd_id") and "headcount" not in vals:
                herd = self.env["agriculture.livestock.herd"].browse(vals["herd_id"])
                vals["headcount"] = herd.headcount
        return super().create(vals_list)

    @api.constrains(
        "animal_id", "herd_id", "headcount", "quantity", "uom_id",
        "date", "production_type", "product_description",
    )
    def _check_production(self):
        for rec in self:
            if bool(rec.animal_id) == bool(rec.herd_id):
                raise ValidationError(_(
                    "Un enregistrement de production doit concerner exactement un animal ou un lot."
                ))
            if rec.animal_id and rec.animal_id.state != "active":
                raise ValidationError(_("La production ne peut concerner qu'un animal actif."))
            if rec.herd_id and not rec.herd_id.active:
                raise ValidationError(_("La production ne peut concerner qu'un lot actif."))
            if rec.headcount <= 0:
                raise ValidationError(_("L'effectif concerné doit être strictement positif."))
            if rec.quantity <= 0:
                raise ValidationError(_("La quantité produite doit être strictement positive."))
            if not rec.uom_id:
                raise ValidationError(_("Une unité de mesure est obligatoire."))
            if rec.production_type == "other" and not rec.product_description:
                raise ValidationError(_("Précisez le produit pour une autre production."))

    def action_mark_done(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Seul un enregistrement en brouillon peut être validé."))
            super(AgricultureLivestockProduction, rec).write({"state": "done"})
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Seul un enregistrement en brouillon peut être annulé."))
            super(AgricultureLivestockProduction, rec).write({"state": "cancel"})
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_(
                    "Une production enregistrée ne peut pas être remise en brouillon. "
                    "Créez un enregistrement correctif si nécessaire."
                ))
        return True

    def write(self, vals):
        if "state" in vals:
            raise UserError(_("Utilisez les boutons de validation ou d'annulation pour changer l'état."))
        protected_fields = {
            "date", "production_type", "animal_id", "herd_id", "headcount",
            "product_description", "quantity", "uom_id", "quality",
            "collection_reference", "notes",
        }
        if protected_fields.intersection(vals):
            locked = self.filtered(lambda rec: rec.state != "draft")
            if locked:
                raise UserError(_(
                    "Une production enregistrée ou annulée ne peut plus être modifiée."
                ))
        return super().write(vals)

    def unlink(self):
        if any(rec.state != "draft" for rec in self):
            raise UserError(_("Seuls les enregistrements de production en brouillon peuvent être supprimés."))
        return super().unlink()
