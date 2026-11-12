# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriWorkTime(models.Model):
    _name = "gest_agri.work.time"
    _description = "Temps de travail agricole"
    _inherit = ["mail.thread"]
    _order = "work_date desc, id desc"
    _check_company_auto = True

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string="Référence", required=True, copy=False, index=True, readonly=True,
    )
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Rattachement
    # ------------------------------------------------------------------
    assignment_id = fields.Many2one(
        "gest_agri.work.assignment", string="Affectation", required=True,
        ondelete="restrict", index=True,
    )
    worker_id = fields.Many2one(
        "gest_agri.worker", string="Travailleur", required=True,
        ondelete="restrict", index=True,
    )
    farm_id = fields.Many2one(
        related="assignment_id.farm_id", string="Exploitation", store=True, readonly=True,
        precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="assignment_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )

    # ------------------------------------------------------------------
    # Temps de travail
    # ------------------------------------------------------------------
    work_date = fields.Date(string="Date de travail", required=True, index=True)
    start_time = fields.Float(string="Heure de début", digits=(16, 2), required=True)
    end_time = fields.Float(string="Heure de fin", digits=(16, 2), required=True)
    break_duration = fields.Float(string="Pause (h)", digits=(16, 2), default=0.0)
    duration = fields.Float(string="Durée (h)", compute="_compute_duration", store=True, digits=(16, 2))
    net_duration = fields.Float(string="Durée nette (h)", compute="_compute_net_duration", store=True, digits=(16, 2))

    notes = fields.Text(string="Observations")

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validé"), ("cancelled", "Annulé")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                reference = self.env["ir.sequence"].next_by_code("gest_agri.work.time")
                if not reference:
                    raise UserError(self.env._("La séquence « gest_agri.work.time » est introuvable."))
                vals["name"] = reference
            if vals.get("assignment_id") and vals.get("worker_id"):
                assignment = self.env["gest_agri.work.assignment"].browse(vals["assignment_id"])
                worker = self.env["gest_agri.worker"].browse(vals["worker_id"])
                if assignment.state == "cancelled":
                    raise ValidationError(self.env._("Impossible d'enregistrer du temps sur une affectation annulée."))
                if worker.farm_id != assignment.farm_id:
                    raise ValidationError(self.env._("Le travailleur doit appartenir à la même exploitation que l'affectation."))
            self._check_overlap(vals)
        return super().create(vals_list)

    @api.model
    def _check_overlap(self, vals):
        if not vals.get("worker_id") or not vals.get("work_date"):
            return
        start = vals.get("start_time", 0.0)
        end = vals.get("end_time", 0.0)
        if end <= start:
            return
        domain = [
            ("worker_id", "=", vals["worker_id"]),
            ("work_date", "=", vals["work_date"]),
            ("state", "!=", "cancelled"),
        ]
        if vals.get("id"):
            domain.append(("id", "!=", vals["id"]))
        existing = self.search(domain)
        for t in existing:
            if t.end_time > start and t.start_time < end:
                raise ValidationError(
                    self.env._("Chevauchement horaire pour le travailleur sur cette date.")
                )

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("start_time", "end_time")
    def _compute_duration(self):
        for t in self:
            t.duration = max(t.end_time - t.start_time, 0.0)

    @api.depends("duration", "break_duration")
    def _compute_net_duration(self):
        for t in self:
            t.net_duration = max(t.duration - t.break_duration, 0.0)

    # ------------------------------------------------------------------
    # Contraintes
    # ------------------------------------------------------------------
    @api.constrains("start_time", "end_time", "break_duration")
    def _check_times(self):
        for t in self:
            if t.end_time <= t.start_time:
                raise ValidationError(self.env._("L'heure de fin doit être strictement postérieure à l'heure de début."))
            if t.net_duration <= 0:
                raise ValidationError(self.env._("La durée nette doit être positive."))
            if t.break_duration < 0:
                raise ValidationError(self.env._("La pause ne peut pas être négative."))

    # ------------------------------------------------------------------
    # Write / workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        protected = {"assignment_id", "worker_id", "farm_id", "company_id"}
        for t in self:
            if t.state == "validated" and (protected & set(vals)):
                raise UserError(self.env._("La feuille de temps « %s » est validée : seules les observations et l'archivage sont modifiables.", t.display_name))
            if t.state == "validated" and set(vals) - {"notes", "active"}:
                raise UserError(self.env._("La feuille de temps « %s » est validée : seules les observations et l'archivage sont modifiables.", t.display_name))
            if t.state == "cancelled" and set(vals) - {"active"}:
                raise AccessError(self.env._("La feuille de temps « %s » est annulée : aucune modification directe n'est autorisée.", t.display_name))
        if "state" in vals and not self.env.context.get("gest_agri_work_time_state_transition"):
            for t in self:
                if t.state != vals["state"]:
                    raise AccessError(self.env._("Le statut d'une feuille de temps ne peut être modifié qu'à travers les actions métier."))
        # overlap check on update
        if "start_time" in vals or "end_time" in vals or "work_date" in vals:
            for t in self:
                self._check_overlap({
                    "worker_id": vals.get("worker_id", t.worker_id.id),
                    "work_date": vals.get("work_date", t.work_date),
                    "start_time": vals.get("start_time", t.start_time),
                    "end_time": vals.get("end_time", t.end_time),
                    "id": t.id,
                })
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_work_time_state_transition=True).write({"state": target})

    def action_validate(self):
        self._check_allowed({"draft"})
        self._apply_state("validated")

    def action_cancel(self):
        self._check_allowed({"draft", "validated"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "validated": "Validé", "cancelled": "Annulé"}
        for t in self:
            if t.state not in allowed:
                raise UserError(self.env._("Transition impossible : la feuille « %(t)s » est à l'état « %(s)s ».", t=t.display_name, s=labels.get(t.state, t.state)))

    def unlink(self):
        for t in self:
            if t.state != "draft":
                raise UserError(self.env._("La feuille « %s » ne peut être supprimée qu'en brouillon.", t.display_name))
        return super().unlink()
