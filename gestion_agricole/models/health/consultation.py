# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriVeterinaryConsultation(models.Model):
    _name = "gest_agri.veterinary.consultation"
    _description = "Consultation vétérinaire"
    _inherit = ["mail.thread"]
    _order = "consultation_datetime desc, id desc"
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
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", index=True)

    consultation_datetime = fields.Datetime(
        string="Date et heure", required=True, index=True, default=fields.Datetime.now,
    )
    veterinarian_id = fields.Many2one("res.partner", string="Vétérinaire", ondelete="set null")
    reason = fields.Char(string="Motif de consultation")
    symptoms = fields.Text(string="Symptômes constatés")
    diagnosis = fields.Text(string="Diagnostic communiqué")
    acts = fields.Text(string="Actes réalisés")
    recommendations = fields.Text(string="Recommandations")
    next_control_date = fields.Date(string="Date de prochain contrôle", index=True)
    notes = fields.Text(string="Observations")
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("done", "Réalisée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.veterinary.consultation")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.veterinary.consultation » est introuvable."))
                vals["name"] = ref
            if not vals.get("animal_id") and not vals.get("lot_id"):
                raise ValidationError(self.env._("Une consultation doit concerner un animal ou un lot."))
            if vals.get("animal_id") and vals.get("lot_id"):
                raise ValidationError(self.env._("Une consultation ne peut concerner à la fois un animal et un lot."))
        return super().create(vals_list)

    @api.constrains("animal_id", "lot_id", "site_id")
    def _check_scope_coherence(self):
        for rec in self:
            if rec.site_id and rec.animal_id and rec.site_id.farm_id != rec.animal_id.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation de l'animal."))
            if rec.site_id and rec.lot_id and not rec.animal_id and rec.site_id.farm_id != rec.lot_id.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation du lot."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_consultation_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_consultation_state_transition=True).write({"state": target})

    def action_done(self):
        self._check_allowed({"draft"})
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "done"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "done": "Réalisée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._("Transition impossible : la consultation « %(c)s » est à l'état « %(s)s ».", c=rec.display_name, s=labels.get(rec.state, rec.state)))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La consultation « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()
