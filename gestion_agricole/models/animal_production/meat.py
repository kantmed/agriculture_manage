# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriMeatProduction(models.Model):
    """Production de viande.

    Distingue explicitement le poids vif, le poids de carcasse et le poids
    commercialisable. Le poids vif n'est jamais considéré comme un poids de
    viande produite : le rendement carcasse n'est calculé que lorsque les deux
    poids nécessaires sont disponibles.
    """

    _name = "gest_agri.meat.production"
    _description = "Production de viande"
    _inherit = ["mail.thread"]
    _order = "production_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    animal_id = fields.Many2one("gest_agri.animal", string="Animal", required=True, ondelete="restrict", index=True)
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot concerné", ondelete="restrict", index=True)
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", compute="_compute_farm_id",
        store=True, readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", index=True)
    species_id = fields.Many2one(
        "gest_agri.livestock.species", string="Espèce", compute="_compute_species_breed",
        store=True, readonly=True, index=True,
    )
    breed_id = fields.Many2one(
        "gest_agri.livestock.breed", string="Race", compute="_compute_species_breed",
        store=True, readonly=True, index=True,
    )

    production_type_id = fields.Many2one(
        "gest_agri.production.type", string="Type de production", ondelete="set null", index=True,
    )
    production_date = fields.Date(string="Date de production", required=True, index=True)
    live_weight = fields.Float(string="Poids vif avant abattage", digits=(16, 3))
    carcass_weight = fields.Float(string="Poids de carcasse", digits=(16, 3))
    marketable_weight = fields.Float(string="Poids commercialisable", digits=(16, 3))
    uom_id = fields.Many2one("uom.uom", string="Unité de mesure", ondelete="restrict")
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    slaughterhouse = fields.Char(string="Abattoir / organisme")
    document_reference = fields.Char(string="Référence documentaire")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    carcass_yield = fields.Float(
        string="Rendement carcasse (%)", compute="_compute_carcass_yield", store=True, digits=(16, 2),
    )

    _meat_animal_date_unique = models.UniqueIndex(
        "(animal_id, production_date) WHERE state != 'cancelled' AND animal_id IS NOT NULL",
        "Une production de viande existe déjà pour cet animal à cette date.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.meat.production")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.meat.production » est introuvable."))
                vals["name"] = ref
        return super().create(vals_list)

    @api.depends("animal_id")
    def _compute_farm_id(self):
        for rec in self:
            rec.farm_id = rec.animal_id.farm_id

    @api.depends("animal_id")
    def _compute_species_breed(self):
        for rec in self:
            rec.species_id = rec.animal_id.species_id
            rec.breed_id = rec.animal_id.breed_id

    @api.depends("live_weight", "carcass_weight")
    def _compute_carcass_yield(self):
        for rec in self:
            if rec.live_weight and rec.live_weight > 0 and rec.carcass_weight:
                rec.carcass_yield = rec.carcass_weight / rec.live_weight * 100.0
            else:
                rec.carcass_yield = 0.0

    @api.constrains("animal_id", "farm_id")
    def _check_animal(self):
        for rec in self:
            if not rec.animal_id:
                continue
            if rec.animal_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("L'animal n'appartient pas à l'exploitation."))
            if rec.production_date and rec.animal_id.birth_date and rec.production_date < rec.animal_id.birth_date:
                raise ValidationError(self.env._("La date de production ne peut pas précéder la naissance de l'animal."))
            death_date = rec.animal_id.death_date
            if death_date and rec.production_date and rec.production_date > death_date:
                raise ValidationError(self.env._(
                    "La production de viande ne peut pas être postérieure au décès de l'animal (« %s »).",
                    rec.animal_id.display_name,
                ))

    @api.constrains("lot_id", "farm_id")
    def _check_lot(self):
        for rec in self:
            if rec.lot_id and rec.lot_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le lot n'appartient pas à l'exploitation."))

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    @api.constrains("live_weight", "carcass_weight", "marketable_weight")
    def _check_weights(self):
        for rec in self:
            if rec.live_weight < 0 or rec.carcass_weight < 0 or rec.marketable_weight < 0:
                raise ValidationError(self.env._("Les poids ne peuvent pas être négatifs."))
            if rec.live_weight and rec.carcass_weight and rec.carcass_weight > rec.live_weight:
                raise ValidationError(self.env._("Le poids de carcasse ne peut pas dépasser le poids vif."))
            if rec.carcass_weight and rec.marketable_weight and rec.marketable_weight > rec.carcass_weight:
                raise ValidationError(self.env._("Le poids commercialisable ne peut pas dépasser le poids de carcasse."))

    @api.constrains("animal_id", "production_date", "state")
    def _check_duplicate(self):
        for rec in self:
            if rec.state == "cancelled" or not rec.animal_id:
                continue
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("state", "!=", "cancelled"),
                ("animal_id", "=", rec.animal_id.id),
                ("production_date", "=", rec.production_date),
            ])
            if duplicates:
                raise ValidationError(self.env._("Une production de viande existe déjà pour cet animal à cette date."))

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_meat_production_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_meat_production_state_transition=True).write({"state": target})

    def action_validate(self):
        self._check_allowed({"draft"})
        self._apply_state("validated")

    def action_cancel(self):
        self._check_allowed({"draft", "validated"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "validated": "Validée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : la production de viande « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La production de viande « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()
