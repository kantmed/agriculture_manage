# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimal(models.Model):
    _name = "gest_agri.animal"
    _description = "Animal"
    _inherit = ["mail.thread"]
    _order = "farm_id, name"
    _check_company_auto = True

    name = fields.Char(string="Désignation", required=True, index=True)
    reference = fields.Char(
        string="Référence", required=True, copy=False, index=True, readonly=True,
    )
    official_id = fields.Char(string="Numéro d'identification officiel", index=True)
    species_id = fields.Many2one(
        "gest_agri.livestock.species", string="Espèce", required=True,
        ondelete="restrict", check_company=True, index=True,
    )
    breed_id = fields.Many2one(
        "gest_agri.livestock.breed", string="Race", ondelete="restrict",
        check_company=True, index=True,
    )
    sex = fields.Selection(
        selection=[("male", "Mâle"), ("female", "Femelle")],
        string="Sexe", required=True, index=True,
    )
    birth_date = fields.Date(string="Date de naissance")
    entry_date = fields.Date(string="Date d'entrée")
    origin = fields.Char(string="Origine / provenance")
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", check_company=True, index=True)
    lot_id = fields.Many2one(
        "gest_agri.animal.lot", string="Lot actuel", ondelete="set null",
        check_company=True, index=True,
    )
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("active", "Actif"), ("sold", "Vendu"),
                   ("dead", "Mort"), ("retired", "Retiré")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )
    notes = fields.Text(string="Observations")
    active = fields.Boolean(string="Actif", default=True)

    _official_id_unique = models.UniqueIndex(
        "(official_id) WHERE official_id IS NOT NULL AND active IS TRUE",
        "Le numéro d'identification officiel doit être unique.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal » est introuvable."))
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
            if vals.get("lot_id") and vals.get("farm_id"):
                lot = self.env["gest_agri.animal.lot"].browse(vals["lot_id"])
                if lot.farm_id.id != vals["farm_id"]:
                    raise ValidationError(self.env._("Le lot n'appartient pas à l'exploitation."))
                if vals.get("site_id") and lot.site_id and lot.site_id.id != vals["site_id"]:
                    raise ValidationError(self.env._("Le site de l'animal diffère du site du lot."))
        return super().create(vals_list)

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for animal in self:
            if animal.site_id and animal.site_id.farm_id != animal.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    @api.constrains("species_id", "breed_id")
    def _check_breed_species(self):
        for animal in self:
            if animal.breed_id and animal.breed_id.species_id != animal.species_id:
                raise ValidationError(self.env._("La race ne correspond pas à l'espèce."))

    @api.constrains("farm_id", "lot_id", "site_id")
    def _check_lot_farm(self):
        for animal in self:
            if animal.lot_id and animal.lot_id.farm_id != animal.farm_id:
                raise ValidationError(self.env._("Le lot n'appartient pas à l'exploitation."))
            if animal.lot_id and animal.site_id and animal.lot_id.site_id and animal.site_id != animal.lot_id.site_id:
                raise ValidationError(self.env._("Le site de l'animal diffère du site du lot."))

    # Workflow
    def write(self, vals):
        if "state" in vals:
            for animal in self:
                if animal.state != vals["state"]:
                    raise AccessError(self.env._("L'état d'un animal ne peut être modifié qu'à travers les actions métier."))
        if {"farm_id", "site_id", "lot_id"} & vals.keys():
            Farm = self.env["gest_agri.farm"]
            Site = self.env["gest_agri.site"]
            Lot = self.env["gest_agri.animal.lot"]
            for animal in self:
                farm = Farm.browse(vals.get("farm_id") or animal.farm_id.id)
                farm.check_access("write")
                site = Site.browse(vals.get("site_id", animal.site_id.id))
                lot = Lot.browse(vals.get("lot_id", animal.lot_id.id))
                if site:
                    site.check_access("read")
                    if site.farm_id != farm:
                        raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))
                if lot:
                    lot.check_access("read")
                    if lot.farm_id != farm:
                        raise ValidationError(self.env._("Le lot n'appartient pas à l'exploitation."))
                    if site and lot.site_id and site != lot.site_id:
                        raise ValidationError(self.env._("Le site de l'animal diffère du site du lot."))
        return super().write(vals)

    def _apply_state(self, target):
        return super(GestAgriAnimal, self).write({"state": target})

    def action_activate(self):
        self._check_allowed({"draft"})
        self._apply_state("active")

    def action_sell(self):
        self._check_allowed({"active"})
        self._apply_state("sold")

    def action_die(self):
        self._check_allowed({"active"})
        self._apply_state("dead")

    def action_retire(self):
        self._check_allowed({"active"})
        self._apply_state("retired")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "active": "Actif", "sold": "Vendu", "dead": "Mort", "retired": "Retiré"}
        for animal in self:
            if animal.state not in allowed:
                raise UserError(self.env._("Transition impossible : l'animal « %(a)s » est à l'état « %(s)s ».", a=animal.display_name, s=labels.get(animal.state, animal.state)))

    # Navigation
    def action_view_lot(self):
        self.ensure_one()
        if not self.lot_id:
            return
        return {
            "type": "ir.actions.act_window",
            "res_model": "gest_agri.animal.lot",
            "view_mode": "form",
            "res_id": self.lot_id.id,
        }
