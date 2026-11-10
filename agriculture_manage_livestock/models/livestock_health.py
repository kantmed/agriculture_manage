from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AgricultureLivestockHealth(models.Model):
    _name = "agriculture.livestock.health"
    _description = "Événement sanitaire"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Référence", readonly=True, copy=False, default="Nouveau", tracking=True)
    event_type = fields.Selection([
        ("vaccination", "Vaccination"),
        ("treatment", "Traitement"),
        ("disease", "Maladie"),
        ("deworming", "Déparasitage"),
        ("vet_visit", "Visite vétérinaire"),
        ("quarantine", "Mise en quarantaine"),
        ("surgery", "Intervention / chirurgie"),
        ("other", "Autre"),
    ], string="Type d'intervention", required=True, default="treatment", tracking=True)
    state = fields.Selection([
        ("planned", "Planifié"),
        ("done", "Réalisé"),
        ("cancel", "Annulé"),
    ], string="État", required=True, default="planned", tracking=True)

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
    farm_id = fields.Many2one("agriculture.farm", compute="_compute_farm", store=True, index=True)
    company_id = fields.Many2one("res.company", compute="_compute_farm", store=True, index=True)
    species_id = fields.Many2one("agriculture.livestock.species", compute="_compute_farm", store=True)

    date = fields.Date(string="Date prévue / intervention", required=True, default=fields.Date.context_today, tracking=True)
    done_date = fields.Date(string="Date de réalisation", tracking=True)
    next_date = fields.Date(string="Prochain rappel")
    veterinarian = fields.Char(string="Vétérinaire / intervenant")
    diagnosis = fields.Text(string="Diagnostic")
    symptoms = fields.Text(string="Symptômes / observations")
    treatment = fields.Text(string="Protocole / traitement")

    product_id = fields.Many2one(
        "product.product", string="Médicament / vaccin",
        ondelete="restrict",
        domain="[('type', 'in', ('consu', 'product'))]",
    )
    quantity = fields.Float(string="Quantité utilisée", digits="Product Unit of Measure")
    product_uom_id = fields.Many2one("uom.uom", string="Unité", related="product_id.uom_id", readonly=True)
    dosage = fields.Char(string="Posologie")
    cost = fields.Monetary(string="Coût", currency_field="currency_id", tracking=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True, readonly=True)
    stock_move_id = fields.Many2one("stock.move", string="Mouvement de stock", readonly=True, copy=False)

    meat_withdrawal_days = fields.Integer(string="Délai d'attente viande (jours)", default=0)
    milk_withdrawal_days = fields.Integer(string="Délai d'attente lait (jours)", default=0)
    meat_withdrawal_end = fields.Date(string="Fin d'attente viande")
    milk_withdrawal_end = fields.Date(string="Fin d'attente lait")
    notes = fields.Text(string="Notes")

    @api.depends("animal_id.farm_id", "herd_id.farm_id")
    def _compute_farm(self):
        for rec in self:
            farm = rec.animal_id.farm_id or rec.herd_id.farm_id
            rec.farm_id = farm
            rec.company_id = farm.company_id
            rec.species_id = rec.animal_id.species_id or rec.herd_id.species_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code("agriculture.livestock.health") or "Nouveau"
        return super().create(vals_list)

    def action_create_stock_move(self):
        self.ensure_one()
        if not self.product_id or not self.quantity:
            raise UserError(_("Sélectionnez un médicament et une quantité."))
        if self.stock_move_id:
            return
        company = self.company_id or self.env.company
        source_location = self.env.ref("stock.stock_location_stock", raise_if_not_found=False)
        dest_location = self.env.ref("stock.location_production", raise_if_not_found=False) or source_location
        if not source_location:
            raise UserError(_("Emplacement de stock introuvable."))
        move = self.env["stock.move"].with_company(company).create({
            "name": self.name or "Santé animale",
            "product_id": self.product_id.id,
            "uom_id": self.product_id.uom_id.id,
            "product_uom_qty": self.quantity,
            "location_id": source_location.id,
            "location_dest_id": dest_location.id if dest_location else source_location.id,
            "company_id": company.id,
        })
        move._action_confirm()
        move._action_assign()
        move._action_done()
        self.stock_move_id = move
        return True

    @api.constrains(
        "animal_id", "herd_id", "date", "done_date", "next_date",
        "quantity", "cost", "meat_withdrawal_days", "milk_withdrawal_days",
        "meat_withdrawal_end", "milk_withdrawal_end",
    )
    def _check_health_event(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if bool(rec.animal_id) == bool(rec.herd_id):
                raise ValidationError(_("Un événement sanitaire doit concerner exactement un animal ou un lot."))
            if rec.animal_id and rec.animal_id.state != "active":
                raise ValidationError(_("Le suivi sanitaire ne peut être planifié que pour un animal actif."))
            if rec.herd_id and not rec.herd_id.active:
                raise ValidationError(_("Le lot sélectionné doit être actif."))
            if rec.date and rec.date > today and rec.state == "done":
                raise ValidationError(_("La date d'une intervention réalisée ne peut pas être dans le futur."))
            if rec.done_date and rec.done_date > today:
                raise ValidationError(_("La date de réalisation ne peut pas être dans le futur."))
            if rec.next_date and rec.next_date < rec.date:
                raise ValidationError(_("La date du prochain rappel doit être postérieure ou égale à la date de l'intervention."))
            if rec.quantity < 0 or rec.cost < 0:
                raise ValidationError(_("La quantité et le coût ne peuvent pas être négatifs."))
            if rec.meat_withdrawal_days < 0 or rec.milk_withdrawal_days < 0:
                raise ValidationError(_("Les délais d'attente ne peuvent pas être négatifs."))
            if rec.meat_withdrawal_end and rec.meat_withdrawal_end < rec.date:
                raise ValidationError(_("La fin du délai d'attente viande ne peut pas précéder l'intervention."))
            if rec.milk_withdrawal_end and rec.milk_withdrawal_end < rec.date:
                raise ValidationError(_("La fin du délai d'attente lait ne peut pas précéder l'intervention."))

    def action_mark_done(self):
        for rec in self:
            if rec.state != "planned":
                raise UserError(_("Seul un événement planifié peut être marqué comme réalisé."))
            rec.write({
                "state": "done",
                "done_date": rec.done_date or fields.Date.context_today(rec),
            })
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state != "planned":
                raise UserError(_("Seul un événement planifié peut être annulé."))
            rec.state = "cancel"
        return True
