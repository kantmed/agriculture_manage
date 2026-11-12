# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimalTreatment(models.Model):
    _name = "gest_agri.animal.treatment"
    _description = "Traitement vétérinaire"
    _inherit = ["mail.thread"]
    _order = "start_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    animal_id = fields.Many2one("gest_agri.animal", string="Animal", ondelete="cascade", index=True)
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot", ondelete="cascade", index=True)
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", store=True, readonly=True, precompute=True, index=True,
        compute="_compute_farm_id",
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True, precompute=True, index=True,
    )

    @api.depends("animal_id.farm_id", "lot_id.farm_id")
    def _compute_farm_id(self):
        for rec in self:
            rec.farm_id = rec.animal_id.farm_id or rec.lot_id.farm_id

    product_name = fields.Char(string="Médicament / produit", required=True)
    start_date = fields.Date(string="Date de début", required=True, index=True)
    end_date_planned = fields.Date(string="Date de fin prévue")
    end_date_actual = fields.Date(string="Date de fin réelle")
    dosage = fields.Float(string="Dose", digits=(16, 3), default=0.0)
    uom_id = fields.Many2one("uom.uom", string="Unité", ondelete="set null")
    frequency = fields.Char(string="Fréquence")
    administration_route = fields.Selection(
        selection=[("oral", "Orale"), ("injection", "Injection"), ("topical", "Topique"), ("other", "Autre")],
        string="Voie d'administration", default="oral",
    )
    veterinarian_id = fields.Many2one("res.partner", string="Vétérinaire prescripteur", ondelete="set null")
    responsible_id = fields.Many2one("res.users", string="Responsable de l'administration", ondelete="set null")
    reason = fields.Text(string="Motif du traitement")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("in_progress", "En cours"), ("done", "Terminé"), ("cancelled", "Annulé")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal.treatment")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal.treatment » est introuvable."))
                vals["name"] = ref
            if not vals.get("animal_id") and not vals.get("lot_id"):
                raise ValidationError(self.env._("Un traitement doit concerner un animal ou un lot."))
            if vals.get("animal_id") and vals.get("lot_id"):
                raise ValidationError(self.env._("Un traitement ne peut concerner à la fois un animal et un lot."))
            if vals.get("end_date_planned") and vals.get("start_date") and vals["end_date_planned"] < vals["start_date"]:
                raise ValidationError(self.env._("La date de fin prévue ne peut pas précéder la date de début."))
            if vals.get("dosage", 0) < 0:
                raise ValidationError(self.env._("La dose ne peut pas être négative."))
        return super().create(vals_list)

    @api.constrains("dosage")
    def _check_dosage(self):
        for t in self:
            if t.dosage < 0:
                raise ValidationError(self.env._("La dose ne peut pas être négative."))

    @api.constrains("start_date", "end_date_planned", "end_date_actual")
    def _check_dates(self):
        for t in self:
            if t.end_date_planned and t.end_date_planned < t.start_date:
                raise ValidationError(self.env._("La date de fin prévue ne peut pas précéder la date de début."))
            if t.end_date_actual and t.end_date_actual < t.start_date:
                raise ValidationError(self.env._("La date de fin réelle ne peut pas précéder la date de début."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_animal_treatment_state_transition"):
            for t in self:
                if t.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_animal_treatment_state_transition=True).write({"state": target})

    def action_start(self):
        self._check_allowed({"draft"})
        self._apply_state("in_progress")

    def action_done(self):
        self._check_allowed({"in_progress"})
        for t in self:
            if not t.end_date_actual:
                t.end_date_actual = fields.Date.today()
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "in_progress"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "in_progress": "En cours", "done": "Terminé", "cancelled": "Annulé"}
        for t in self:
            if t.state not in allowed:
                raise UserError(self.env._("Transition impossible : le traitement « %(t)s » est à l'état « %(s)s ».", t=t.display_name, s=labels.get(t.state, t.state)))

    def unlink(self):
        for t in self:
            if t.state != "draft":
                raise UserError(self.env._("Le traitement « %s » ne peut être supprimé qu'en brouillon.", t.display_name))
        return super().unlink()
