# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriVaccination(models.Model):
    _name = "gest_agri.vaccination"
    _description = "Vaccination animale"
    _inherit = ["mail.thread"]
    _order = "vaccination_date desc, id desc"
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

    vaccine_name = fields.Char(string="Vaccin utilisé", required=True)
    vaccine_lot = fields.Char(string="Numéro de lot du vaccin")
    vaccination_date = fields.Date(string="Date de vaccination", required=True, index=True)
    next_due_date = fields.Date(string="Date de rappel prévue")
    dose = fields.Float(string="Dose", digits=(16, 3), default=0.0)
    uom_id = fields.Many2one("uom.uom", string="Unité", ondelete="set null")
    administration_route = fields.Selection(
        selection=[("oral", "Orale"), ("injection", "Injection"), ("topical", "Topique"), ("other", "Autre")],
        string="Voie d'administration", default="injection",
    )
    veterinarian_id = fields.Many2one("res.partner", string="Vétérinaire / responsable", ondelete="set null")
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("done", "Réalisée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.vaccination")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.vaccination » est introuvable."))
                vals["name"] = ref
            if not vals.get("animal_id") and not vals.get("lot_id"):
                raise ValidationError(self.env._("Une vaccination doit concerner un animal ou un lot."))
            if vals.get("animal_id") and vals.get("lot_id"):
                raise ValidationError(self.env._("Une vaccination ne peut concerner à la fois un animal et un lot."))
            if vals.get("next_due_date") and vals.get("vaccination_date") and vals["next_due_date"] < vals["vaccination_date"]:
                raise ValidationError(self.env._("La date de rappel doit être postérieure à la date de vaccination."))
        return super().create(vals_list)

    @api.constrains("dose")
    def _check_dose(self):
        for vac in self:
            if vac.dose < 0:
                raise ValidationError(self.env._("La dose ne peut pas être négative."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_vaccination_state_transition"):
            for vac in self:
                if vac.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_vaccination_state_transition=True).write({"state": target})

    def action_done(self):
        self._check_allowed({"draft"})
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "done"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "done": "Réalisée", "cancelled": "Annulée"}
        for vac in self:
            if vac.state not in allowed:
                raise UserError(self.env._("Transition impossible : la vaccination « %(v)s » est à l'état « %(s)s ».", v=vac.display_name, s=labels.get(vac.state, vac.state)))

    def unlink(self):
        for vac in self:
            if vac.state != "draft":
                raise UserError(self.env._("La vaccination « %s » ne peut être supprimée qu'en brouillon.", vac.display_name))
        return super().unlink()
