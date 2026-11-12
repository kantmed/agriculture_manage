# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimalGestation(models.Model):
    _name = "gest_agri.animal.gestation"
    _description = "Gestation animale"
    _inherit = ["mail.thread"]
    _order = "start_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    female_id = fields.Many2one(
        "gest_agri.animal", string="Femelle", required=True, ondelete="restrict", index=True,
    )
    reproduction_id = fields.Many2one(
        "gest_agri.animal.reproduction", string="Événement reproductif d'origine",
        ondelete="restrict", index=True,
    )
    male_id = fields.Many2one("gest_agri.animal", string="Mâle reproducteur", ondelete="restrict", index=True)
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

    start_date = fields.Date(string="Date de début", required=True, index=True)
    expected_birth_date = fields.Date(
        string="Date prévue de mise bas", compute="_compute_expected_birth_date",
        store=True, readonly=False, index=True,
    )
    confirmation_date = fields.Date(string="Date de confirmation")
    confirmation_method = fields.Selection(
        selection=[
            ("observation", "Observation"),
            ("ultrasound", "Échographie"),
            ("palpation", "Palpation"),
            ("hormonal_test", "Test hormonal"),
            ("other", "Autre"),
        ],
        string="Méthode de confirmation",
    )
    actual_end_date = fields.Date(string="Date réelle de fin")
    responsible_id = fields.Many2one("res.users", string="Responsable du suivi", ondelete="set null")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[
            ("to_confirm", "À confirmer"),
            ("confirmed", "Confirmée"),
            ("terminated", "Terminée"),
            ("aborted", "Avortée"),
            ("interrupted", "Interrompue"),
        ],
        string="Statut", default="to_confirm", required=True, index=True, tracking=True, copy=False,
    )

    birth_ids = fields.One2many("gest_agri.animal.birth", "gestation_id", string="Mises bas")
    birth_count = fields.Integer(string="Nb mises bas", compute="_compute_birth_count")

    _reproduction_unique = models.UniqueIndex(
        "(reproduction_id) WHERE state != 'cancelled' AND reproduction_id IS NOT NULL",
        "Une gestation existe déjà pour cet événement reproductif.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal.gestation")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal.gestation » est introuvable."))
                vals["name"] = ref
            if not vals.get("male_id") and vals.get("reproduction_id"):
                reproduction = self.env["gest_agri.animal.reproduction"].browse(vals["reproduction_id"])
                if reproduction.male_id:
                    vals["male_id"] = reproduction.male_id.id
            if not vals.get("female_id") and vals.get("reproduction_id"):
                reproduction = self.env["gest_agri.animal.reproduction"].browse(vals["reproduction_id"])
                vals["female_id"] = reproduction.female_id.id
        return super().create(vals_list)

    @api.depends("female_id")
    def _compute_farm_id(self):
        for rec in self:
            rec.farm_id = rec.female_id.farm_id

    @api.depends("start_date", "female_id.species_id.gestation_duration_days")
    def _compute_expected_birth_date(self):
        for rec in self:
            duration = rec.female_id.species_id.gestation_duration_days
            if rec.start_date and duration:
                rec.expected_birth_date = rec.start_date + timedelta(days=duration)
            elif not rec.start_date:
                rec.expected_birth_date = False

    @api.depends("birth_ids")
    def _compute_birth_count(self):
        for rec in self:
            rec.birth_count = len(rec.birth_ids)

    @api.constrains("female_id")
    def _check_female(self):
        for rec in self:
            if rec.female_id and rec.female_id.sex != "female":
                raise ValidationError(self.env._("La gestation doit concerner une femelle."))

    @api.constrains("female_id", "reproduction_id")
    def _check_reproduction_coherence(self):
        for rec in self:
            if rec.reproduction_id and rec.female_id and rec.reproduction_id.female_id != rec.female_id:
                raise ValidationError(self.env._("La femelle ne correspond pas à l'événement reproductif d'origine."))

    @api.constrains("reproduction_id", "state")
    def _check_reproduction_unique(self):
        for rec in self:
            if not rec.reproduction_id or rec.state == "cancelled":
                continue
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("reproduction_id", "=", rec.reproduction_id.id),
                ("state", "!=", "cancelled"),
            ])
            if duplicates:
                raise ValidationError(self.env._("Une gestation existe déjà pour cet événement reproductif."))

    @api.constrains("start_date", "expected_birth_date", "actual_end_date", "reproduction_id")
    def _check_dates(self):
        for rec in self:
            if rec.reproduction_id and rec.start_date and rec.start_date < rec.reproduction_id.event_date:
                raise ValidationError(self.env._("La date de début ne peut pas précéder l'événement reproductif."))
            if rec.expected_birth_date and rec.start_date and rec.expected_birth_date <= rec.start_date:
                raise ValidationError(self.env._("La date prévue de mise bas doit être postérieure à la date de début."))
            if rec.actual_end_date and rec.start_date and rec.actual_end_date < rec.start_date:
                raise ValidationError(self.env._("La date réelle de fin ne peut pas précéder la date de début."))

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation de la femelle."))

    # Workflow
    _LOCKED_FIELDS = ("female_id", "reproduction_id", "start_date", "expected_birth_date")

    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_gestation_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        terminal = {"terminated", "aborted", "interrupted"}
        for rec in self:
            if rec.state in terminal and any(f in vals for f in self._LOCKED_FIELDS):
                raise UserError(self.env._(
                    "La gestation « %s » est clôturée : ses données principales ne peuvent plus être modifiées.",
                    rec.display_name,
                ))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_gestation_state_transition=True).write({"state": target})

    def action_confirm(self):
        self._check_allowed({"to_confirm"})
        for rec in self:
            if not rec.confirmation_date:
                rec.confirmation_date = fields.Date.today()
        self._apply_state("confirmed")

    def action_terminate(self):
        self._check_allowed({"confirmed"})
        for rec in self:
            if not rec.actual_end_date:
                rec.actual_end_date = fields.Date.today()
        self._apply_state("terminated")

    def action_abort(self):
        self._check_allowed({"to_confirm", "confirmed"})
        for rec in self:
            if not rec.actual_end_date:
                rec.actual_end_date = fields.Date.today()
        self._apply_state("aborted")

    def action_interrupt(self):
        self._check_allowed({"to_confirm", "confirmed"})
        for rec in self:
            if not rec.actual_end_date:
                rec.actual_end_date = fields.Date.today()
        self._apply_state("interrupted")

    def _check_allowed(self, allowed):
        labels = {
            "to_confirm": "À confirmer", "confirmed": "Confirmée", "terminated": "Terminée",
            "aborted": "Avortée", "interrupted": "Interrompue",
        }
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : la gestation « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state not in ("to_confirm",):
                raise UserError(self.env._("La gestation « %s » ne peut être supprimée qu'à l'état « À confirmer ».", rec.display_name))
        return super().unlink()
