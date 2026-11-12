# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriWorkAssignment(models.Model):
    _name = "gest_agri.work.assignment"
    _description = "Affectation aux travaux agricoles"
    _inherit = ["mail.thread"]
    _order = "planned_start desc, id desc"
    _check_company_auto = True

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(string="Intitulé", required=True, index=True)
    reference = fields.Char(
        string="Référence", required=True, copy=False, index=True, readonly=True,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Rattachement
    # ------------------------------------------------------------------
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", check_company=True, index=True)
    plot_id = fields.Many2one("gest_agri.plot", string="Parcelle", ondelete="set null", index=True)

    worker_id = fields.Many2one("gest_agri.worker", string="Travailleur", ondelete="set null", index=True)
    team_id = fields.Many2one("gest_agri.team", string="Équipe", ondelete="set null", index=True)

    # Production végétale
    cycle_id = fields.Many2one("gest_agri.crop.cycle", string="Cycle cultural", ondelete="set null", index=True)
    intervention_id = fields.Many2one("gest_agri.crop.intervention", string="Intervention agricole", ondelete="set null", index=True)

    # ------------------------------------------------------------------
    # Planification
    # ------------------------------------------------------------------
    planned_start = fields.Datetime(string="Début prévu", index=True)
    planned_end = fields.Datetime(string="Fin prévue", index=True)
    planned_duration = fields.Float(string="Durée prévue (h)", compute="_compute_planned_duration", store=True, digits=(16, 2))
    work_type = fields.Char(string="Type de travail")
    priority = fields.Selection(
        selection=[("0", "Basse"), ("1", "Normale"), ("2", "Haute"), ("3", "Urgente")],
        string="Priorité", default="1",
    )
    instructions = fields.Text(string="Instructions")
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")

    # ------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------
    worker_count = fields.Integer(string="Nombre de travailleurs", compute="_compute_worker_count")
    time_ids = fields.One2many("gest_agri.work.time", "assignment_id", string="Feuilles de temps")
    time_count = fields.Integer(string="Nombre de feuilles de temps", compute="_compute_time_count")
    actual_duration = fields.Float(string="Durée réelle (h)", compute="_compute_actual_duration", digits=(16, 2))
    duration_variance = fields.Float(string="Écart durée (h)", compute="_compute_duration_variance", digits=(16, 2))

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("planned", "Planifiée"), ("in_progress", "En cours"),
                   ("done", "Terminée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                reference = self.env["ir.sequence"].next_by_code("gest_agri.work.assignment")
                if not reference:
                    raise UserError(self.env._("La séquence « gest_agri.work.assignment » est introuvable."))
                vals["reference"] = reference
            if not vals.get("name"):
                vals["name"] = vals["reference"]
            if not vals.get("worker_id") and not vals.get("team_id"):
                raise ValidationError(
                    self.env._("Une affectation doit concerner au minimum un travailleur ou une équipe.")
                )
            self._check_coherence(vals)
        return super().create(vals_list)

    @api.model
    def _check_coherence(self, vals):
        farm_id = vals.get("farm_id")
        if vals.get("plot_id") and farm_id:
            plot = self.env["gest_agri.plot"].browse(vals["plot_id"])
            if plot.farm_id.id != farm_id:
                raise ValidationError(self.env._("La parcelle n'appartient pas à l'exploitation."))
        if vals.get("worker_id") and farm_id:
            worker = self.env["gest_agri.worker"].browse(vals["worker_id"])
            if worker.farm_id.id != farm_id:
                raise ValidationError(self.env._("Le travailleur n'appartient pas à l'exploitation."))
        if vals.get("team_id") and farm_id:
            team = self.env["gest_agri.team"].browse(vals["team_id"])
            if team.farm_id.id != farm_id:
                raise ValidationError(self.env._("L'équipe n'appartient pas à l'exploitation."))
        if vals.get("cycle_id") and farm_id:
            cycle = self.env["gest_agri.crop.cycle"].browse(vals["cycle_id"])
            if cycle.farm_id.id != farm_id:
                raise ValidationError(self.env._("Le cycle ne appartient pas à l'exploitation."))
        if vals.get("intervention_id") and farm_id:
            inter = self.env["gest_agri.crop.intervention"].browse(vals["intervention_id"])
            if inter.farm_id.id != farm_id:
                raise ValidationError(self.env._("L'intervention ne appartient pas à l'exploitation."))

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("planned_start", "planned_end")
    def _compute_planned_duration(self):
        for a in self:
            if a.planned_start and a.planned_end:
                a.planned_duration = (a.planned_end - a.planned_start).total_seconds() / 3600.0
            else:
                a.planned_duration = 0.0

    @api.depends("worker_id", "team_id")
    def _compute_worker_count(self):
        for a in self:
            if a.worker_id:
                a.worker_count = 1
            elif a.team_id:
                a.worker_count = a.team_id.member_count
            else:
                a.worker_count = 0

    @api.depends("time_ids")
    def _compute_time_count(self):
        for a in self:
            a.time_count = len(a.with_context(active_test=False).time_ids)

    @api.depends("time_ids", "time_ids.net_duration", "time_ids.state")
    def _compute_actual_duration(self):
        for a in self:
            a.actual_duration = sum(
                t.net_duration for t in a.with_context(active_test=False).time_ids if t.state == "validated"
            )

    @api.depends("planned_duration", "actual_duration")
    def _compute_duration_variance(self):
        for a in self:
            a.duration_variance = a.actual_duration - a.planned_duration

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        protected = {"farm_id", "worker_id", "team_id", "cycle_id", "intervention_id", "plot_id", "site_id"}
        for a in self:
            if a.state in ("done", "cancelled") and (protected & set(vals)):
                raise UserError(self.env._("L'affectation « %s » est terminée ou annulée : seules l'état et les observations sont modifiables.", a.display_name))
        if "state" in vals and not self.env.context.get("gest_agri_work_assignment_state_transition"):
            for a in self:
                if a.state != vals["state"]:
                    raise AccessError(self.env._("Le statut d'une affectation ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_work_assignment_state_transition=True).write({"state": target})

    def action_plan(self):
        self._check_allowed({"draft"})
        self._apply_state("planned")

    def action_start(self):
        self._check_allowed({"planned"})
        self._apply_state("in_progress")

    def action_done(self):
        self._check_allowed({"in_progress"})
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "planned", "in_progress"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "planned": "Planifiée", "in_progress": "En cours", "done": "Terminée", "cancelled": "Annulée"}
        for a in self:
            if a.state not in allowed:
                raise UserError(self.env._("Transition impossible : l'affectation « %(a)s » est à l'état « %(s)s ».", a=a.display_name, s=labels.get(a.state, a.state)))

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_view_times(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("gestion_agricole.action_gest_agri_work_time")
        action["domain"] = [("assignment_id", "=", self.id)]
        action["context"] = {"default_assignment_id": self.id}
        return action
