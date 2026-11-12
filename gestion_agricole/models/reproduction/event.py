# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimalReproduction(models.Model):
    _name = "gest_agri.animal.reproduction"
    _description = "Événement reproductif"
    _inherit = ["mail.thread"]
    _order = "event_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    female_id = fields.Many2one(
        "gest_agri.animal", string="Femelle", required=True, ondelete="restrict", index=True,
    )
    male_id = fields.Many2one(
        "gest_agri.animal", string="Mâle reproducteur", ondelete="restrict", index=True,
    )
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
        "gest_agri.livestock.species", string="Espèce", related="female_id.species_id",
        store=True, readonly=True, index=True,
    )
    breed_id = fields.Many2one(
        "gest_agri.livestock.breed", string="Race", related="female_id.breed_id",
        store=True, readonly=True, index=True,
    )

    event_date = fields.Date(string="Date de l'événement", required=True, index=True)
    event_type = fields.Selection(
        selection=[
            ("natural_mating", "Accouplement naturel"),
            ("artificial_insemination", "Insémination artificielle"),
            ("embryo_transfer", "Transfert embryonnaire"),
            ("other", "Autre événement reproductif"),
        ],
        string="Type d'événement", required=True, default="natural_mating",
    )
    method = fields.Char(string="Méthode utilisée")
    semen_origin = fields.Char(string="Reproducteur / origine de la semence")
    responsible_id = fields.Many2one("res.users", string="Responsable de l'opération", ondelete="set null")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("confirmed", "Confirmé"), ("cancelled", "Annulé")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    gestation_ids = fields.One2many(
        "gest_agri.animal.gestation", "reproduction_id", string="Gestations",
    )
    gestation_count = fields.Integer(string="Nb gestations", compute="_compute_gestation_count")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal.reproduction")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal.reproduction » est introuvable."))
                vals["name"] = ref
        return super().create(vals_list)

    @api.depends("female_id")
    def _compute_farm_id(self):
        for rec in self:
            rec.farm_id = rec.female_id.farm_id

    @api.depends("gestation_ids")
    def _compute_gestation_count(self):
        for rec in self:
            rec.gestation_count = len(rec.gestation_ids)

    @api.constrains("female_id")
    def _check_female(self):
        for rec in self:
            if not rec.female_id:
                continue
            if rec.female_id.sex != "female":
                raise ValidationError(self.env._("L'animal femelle doit être de sexe féminin."))
            if rec.female_id.state in ("dead", "sold", "retired"):
                raise ValidationError(
                    self.env._("L'animal « %s » n'est plus en état de participer à un événement reproductif.", rec.female_id.display_name)
                )

    @api.constrains("male_id", "female_id")
    def _check_male(self):
        for rec in self:
            if not rec.male_id:
                continue
            if rec.male_id.sex != "male":
                raise ValidationError(self.env._("Le reproducteur doit être de sexe masculin."))
            if rec.male_id.state in ("dead", "sold", "retired"):
                raise ValidationError(
                    self.env._("Le reproducteur « %s » n'est plus en état de participer à un événement reproductif.", rec.male_id.display_name)
                )
            if rec.female_id and rec.male_id.species_id != rec.female_id.species_id:
                raise ValidationError(self.env._("Le mâle et la femelle doivent appartenir à la même espèce."))

    @api.constrains("event_date", "female_id", "male_id")
    def _check_dates(self):
        for rec in self:
            if not rec.event_date:
                continue
            if rec.female_id.birth_date and rec.event_date < rec.female_id.birth_date:
                raise ValidationError(self.env._("La date de l'événement ne peut pas précéder la naissance de la femelle."))
            if rec.male_id and rec.male_id.birth_date and rec.event_date < rec.male_id.birth_date:
                raise ValidationError(self.env._("La date de l'événement ne peut pas précéder la naissance du mâle."))

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation de la femelle."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_reproduction_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_reproduction_state_transition=True).write({"state": target})

    def action_confirm(self):
        self._check_allowed({"draft"})
        self._apply_state("confirmed")

    def action_cancel(self):
        self._check_allowed({"draft", "confirmed"})
        for rec in self:
            if rec.gestation_ids:
                raise UserError(self.env._(
                    "L'événement reproductif « %s » a des gestations associées : son annulation "
                    "rendrait l'historique incohérent. Supprimez d'abord les gestations concernées "
                    "(uniquement possible à l'état « À confirmer »).",
                    rec.display_name,
                ))
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "confirmed": "Confirmé", "cancelled": "Annulé"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : l'événement « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("L'événement reproductif « %s » ne peut être supprimé qu'en brouillon.", rec.display_name))
            if rec.gestation_ids:
                raise UserError(self.env._(
                    "L'événement reproductif « %s » a des gestations associées : supprimez-les d'abord.",
                    rec.display_name,
                ))
        return super().unlink()
