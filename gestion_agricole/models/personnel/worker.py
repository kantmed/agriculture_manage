# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriWorker(models.Model):
    _name = "gest_agri.worker"
    _description = "Travailleur agricole"
    _inherit = ["mail.thread"]
    _order = "farm_id, name"
    _check_company_auto = True

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(string="Nom", required=True, index=True)
    firstname = fields.Char(string="Prénom")
    full_name = fields.Char(string="Nom complet", compute="_compute_full_name", store=True)
    reference = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        index=True,
        readonly=True,
    )
    image_1920 = fields.Image(string="Photo", max_width=1920, max_height=1920)
    description = fields.Text(string="Description")
    notes = fields.Text(string="Observations")
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Informations personnelles et professionnelles
    # ------------------------------------------------------------------
    birth_date = fields.Date(string="Date de naissance")
    phone = fields.Char(string="Téléphone")
    email = fields.Char(string="Adresse électronique")
    address = fields.Text(string="Adresse")
    partner_id = fields.Many2one("res.partner", string="Partenaire associé", ondelete="set null")
    user_id = fields.Many2one("res.users", string="Utilisateur Odoo", ondelete="set null")
    function = fields.Char(string="Fonction / spécialité")
    entry_date = fields.Date(string="Date d'entrée")
    exit_date = fields.Date(string="Date de sortie")
    worker_type = fields.Selection(
        selection=[("permanent", "Permanent"), ("seasonal", "Saisonnier"), ("contractor", "Prestataire")],
        string="Type de travailleur",
        default="permanent",
    )

    # ------------------------------------------------------------------
    # Rattachement organisationnel
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
    team_id = fields.Many2one("gest_agri.team", string="Équipe principale", ondelete="set null", index=True)

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("active", "Actif"), ("suspended", "Suspendu"), ("exited", "Sorti")],
        string="État",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Relations et statistiques
    # ------------------------------------------------------------------
    assignment_ids = fields.One2many("gest_agri.work.assignment", "worker_id", string="Affectations")
    assignment_count = fields.Integer(string="Nombre d'affectations", compute="_compute_assignment_count")
    time_ids = fields.One2many("gest_agri.work.time", "worker_id", string="Feuilles de temps")
    time_count = fields.Integer(string="Nombre de feuilles de temps", compute="_compute_time_count")
    total_hours = fields.Float(string="Heures travaillées", compute="_compute_total_hours", digits=(16, 2))
    last_work_date = fields.Date(string="Dernière date de travail", compute="_compute_last_work_date")
    team_ids = fields.Many2many("gest_agri.team", string="Équipes", compute="_compute_team_ids", store=False)

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                reference = self.env["ir.sequence"].next_by_code("gest_agri.worker")
                if not reference:
                    raise UserError(self.env._("La séquence « gest_agri.worker » est introuvable."))
                vals["reference"] = reference
            if not vals.get("name"):
                vals["name"] = vals["reference"]
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("firstname", "name")
    def _compute_full_name(self):
        for worker in self:
            parts = [p for p in (worker.firstname, worker.name) if p]
            worker.full_name = " ".join(parts)

    @api.depends("assignment_ids")
    def _compute_assignment_count(self):
        for worker in self:
            worker.assignment_count = len(worker.with_context(active_test=False).assignment_ids)

    @api.depends("time_ids")
    def _compute_time_count(self):
        for worker in self:
            worker.time_count = len(worker.with_context(active_test=False).time_ids)

    @api.depends("time_ids", "time_ids.net_duration")
    def _compute_total_hours(self):
        for worker in self:
            worker.total_hours = sum(t.net_duration for t in worker.with_context(active_test=False).time_ids if t.state == "validated")

    @api.depends("time_ids", "time_ids.work_date")
    def _compute_last_work_date(self):
        for worker in self:
            times = worker.with_context(active_test=False).time_ids
            if times:
                worker.last_work_date = max(t.work_date for t in times if t.work_date)
            else:
                worker.last_work_date = False

    @api.depends("team_id")
    def _compute_team_ids(self):
        for worker in self:
            teams = self.env["gest_agri.team"].search([("member_ids", "in", worker.id)])
            worker.team_ids = teams

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_worker_state_transition"):
            for worker in self:
                if worker.state != vals["state"]:
                    raise AccessError(self.env._("L'état d'un travailleur ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_worker_state_transition=True).write({"state": target})

    def action_activate(self):
        self._check_allowed({"draft", "suspended"})
        self._apply_state("active")

    def action_suspend(self):
        self._check_allowed({"active"})
        self._apply_state("suspended")

    def action_exit(self):
        self._check_allowed({"active", "suspended"})
        self._apply_state("exited")

    def action_reset_draft(self):
        self._check_allowed({"exited"})
        self._apply_state("draft")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "active": "Actif", "suspended": "Suspendu", "exited": "Sorti"}
        for worker in self:
            if worker.state not in allowed:
                raise UserError(self.env._("Transition impossible : le travailleur « %(w)s » est à l'état « %(s)s ».", w=worker.display_name, s=labels.get(worker.state, worker.state)))

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_view_assignments(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("gestion_agricole.action_gest_agri_work_assignment")
        action["domain"] = [("worker_id", "=", self.id)]
        action["context"] = {"default_worker_id": self.id}
        return action

    def action_view_times(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("gestion_agricole.action_gest_agri_work_time")
        action["domain"] = [("worker_id", "=", self.id)]
        action["context"] = {"default_worker_id": self.id}
        return action
