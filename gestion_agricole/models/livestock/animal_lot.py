# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimalLot(models.Model):
    _name = "gest_agri.animal.lot"
    _description = "Lot d'animaux"
    _inherit = ["mail.thread"]
    _order = "farm_id, name"
    _check_company_auto = True

    name = fields.Char(string="Désignation", required=True, index=True)
    reference = fields.Char(
        string="Référence", required=True, copy=False, index=True, readonly=True,
    )
    species_id = fields.Many2one(
        "gest_agri.livestock.species", string="Espèce", required=True,
        ondelete="restrict", check_company=True, index=True,
    )
    breed_id = fields.Many2one(
        "gest_agri.livestock.breed", string="Race", ondelete="restrict",
        check_company=True, index=True,
    )
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", check_company=True, index=True)
    constitution_date = fields.Date(string="Date de constitution")
    member_ids = fields.One2many("gest_agri.animal", "lot_id", string="Animaux membres")
    member_count = fields.Integer(string="Effectif", compute="_compute_member_count")
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("active", "Actif"), ("closed", "Clôturé")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )
    notes = fields.Text(string="Observations")
    active = fields.Boolean(string="Actif", default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal.lot")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal.lot » est introuvable."))
                vals["reference"] = ref
            if not vals.get("name"):
                vals["name"] = vals["reference"]
            if vals.get("breed_id") and vals.get("species_id"):
                breed = self.env["gest_agri.livestock.breed"].browse(vals["breed_id"])
                if breed.species_id.id != vals["species_id"]:
                    raise ValidationError(self.env._("La race ne correspond pas à l'espèce."))
            if vals.get("farm_id") and vals.get("site_id"):
                site = self.env["gest_agri.site"].browse(vals["site_id"])
                if site.farm_id.id != vals["farm_id"]:
                    raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))
        return super().create(vals_list)

    @api.depends("member_ids")
    def _compute_member_count(self):
        for lot in self:
            lot.member_count = len(lot.with_context(active_test=False).member_ids)

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for lot in self:
            if lot.site_id and lot.site_id.farm_id != lot.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    @api.constrains("species_id", "breed_id")
    def _check_breed_species(self):
        for lot in self:
            if lot.breed_id and lot.breed_id.species_id != lot.species_id:
                raise ValidationError(self.env._("La race ne correspond pas à l'espèce."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_animal_lot_state_transition"):
            for lot in self:
                if lot.state != vals["state"]:
                    raise AccessError(self.env._("L'état d'un lot ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_animal_lot_state_transition=True).write({"state": target})

    def action_activate(self):
        self._check_allowed({"draft"})
        self._apply_state("active")

    def action_close(self):
        self._check_allowed({"active"})
        self._apply_state("closed")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "active": "Actif", "closed": "Clôturé"}
        for lot in self:
            if lot.state not in allowed:
                raise UserError(self.env._("Transition impossible : le lot « %(l)s » est à l'état « %(s)s ».", l=lot.display_name, s=labels.get(lot.state, lot.state)))

    def unlink(self):
        for lot in self:
            if lot.member_ids:
                raise UserError(self.env._("Le lot « %s » contient des animaux : impossible de le supprimer.", lot.display_name))
        return super().unlink()
