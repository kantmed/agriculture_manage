# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimalHealth(models.Model):
    _name = "gest_agri.animal.health"
    _description = "Dossier sanitaire animal"
    _inherit = ["mail.thread"]
    _order = "observation_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    animal_id = fields.Many2one("gest_agri.animal", string="Animal", required=True, ondelete="cascade", index=True)
    farm_id = fields.Many2one(related="animal_id.farm_id", string="Exploitation", store=True, readonly=True, precompute=True, index=True)
    company_id = fields.Many2one(related="farm_id.company_id", string="Société", store=True, readonly=True, precompute=True, index=True)
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", index=True)

    observation_date = fields.Date(string="Date d'observation", required=True, index=True)
    declaration_date = fields.Date(string="Date de déclaration", default=fields.Date.today)
    symptoms = fields.Text(string="Symptômes observés")
    disease_id = fields.Many2one("gest_agri.animal.disease", string="Maladie suspectée/diagnostiquée", ondelete="set null", index=True)
    severity = fields.Selection(
        selection=[("low", "Faible"), ("medium", "Moyenne"), ("high", "Élevée"), ("critical", "Critique")],
        string="Gravité", default="medium",
    )
    notes = fields.Text(string="Observations")
    veterinarian_id = fields.Many2one("res.partner", string="Vétérinaire", ondelete="set null")
    responsible_id = fields.Many2one("res.users", string="Responsable de la déclaration", ondelete="set null")
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validé"), ("cancelled", "Annulé")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal.health")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal.health » est introuvable."))
                vals["name"] = ref
            if vals.get("animal_id") and vals.get("disease_id"):
                animal = self.env["gest_agri.animal"].browse(vals["animal_id"])
                disease = self.env["gest_agri.animal.disease"].browse(vals["disease_id"])
                if disease.species_ids and animal.species_id not in disease.species_ids:
                    raise ValidationError(self.env._("La maladie n'est pas compatible avec l'espèce de l'animal."))
        return super().create(vals_list)

    @api.constrains("animal_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.animal_id.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation de l'animal."))

    @api.constrains("observation_date", "declaration_date")
    def _check_dates(self):
        for rec in self:
            if rec.declaration_date and rec.observation_date and rec.declaration_date < rec.observation_date:
                raise ValidationError(self.env._("La date de déclaration ne peut pas être antérieure à la date d'observation."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_animal_health_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_animal_health_state_transition=True).write({"state": target})

    def action_validate(self):
        self._check_allowed({"draft"})
        self._apply_state("validated")

    def action_cancel(self):
        self._check_allowed({"draft", "validated"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "validated": "Validé", "cancelled": "Annulé"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._("Transition impossible : le dossier « %(d)s » est à l'état « %(s)s ».", d=rec.display_name, s=labels.get(rec.state, rec.state)))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("Le dossier « %s » ne peut être supprimé qu'en brouillon.", rec.display_name))
        return super().unlink()
