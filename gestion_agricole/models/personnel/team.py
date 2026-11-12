# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class GestAgriTeam(models.Model):
    _name = "gest_agri.team"
    _description = "Équipe agricole"
    _inherit = ["mail.thread"]
    _order = "farm_id, name"
    _check_company_auto = True

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(string="Nom de l'équipe", required=True, index=True)
    reference = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        index=True,
        readonly=True,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Organisation
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
    leader_id = fields.Many2one("gest_agri.worker", string="Responsable", ondelete="set null", index=True)
    member_ids = fields.Many2many("gest_agri.worker", string="Membres")

    # ------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------
    member_count = fields.Integer(string="Nombre de membres", compute="_compute_member_count")
    assignment_count = fields.Integer(string="Nombre d'affectations", compute="_compute_assignment_count")
    total_hours = fields.Float(string="Heures travaillées", compute="_compute_total_hours", digits=(16, 2))
    last_activity_date = fields.Date(string="Dernière activité", compute="_compute_last_activity_date")

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                reference = self.env["ir.sequence"].next_by_code("gest_agri.team")
                if not reference:
                    raise UserError(self.env._("La séquence « gest_agri.team » est introuvable."))
                vals["reference"] = reference
            if not vals.get("name"):
                vals["name"] = vals["reference"]
        return super().create(vals_list)

    @api.constrains("farm_id", "leader_id", "member_ids")
    def _check_farm_coherence(self):
        for team in self:
            if team.leader_id and team.leader_id.farm_id != team.farm_id:
                raise ValidationError(
                    self.env._("Le responsable doit appartenir à l'exploitation de l'équipe.")
                )
            for member in team.member_ids:
                if member.farm_id != team.farm_id:
                    raise ValidationError(
                        self.env._("Le membre « %s » n'appartient pas à l'exploitation de l'équipe.", member.display_name)
                    )

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("member_ids")
    def _compute_member_count(self):
        for team in self:
            team.member_count = len(team.member_ids)

    @api.depends("member_ids")
    def _compute_assignment_count(self):
        for team in self:
            team.assignment_count = self.env["gest_agri.work.assignment"].search_count(
                [("team_id", "=", team.id)]
            )

    @api.depends("member_ids")
    def _compute_total_hours(self):
        for team in self:
            assignments = self.env["gest_agri.work.assignment"].search([("team_id", "=", team.id)])
            team.total_hours = sum(a.actual_duration for a in assignments)

    @api.depends("member_ids")
    def _compute_last_activity_date(self):
        for team in self:
            assignments = self.env["gest_agri.work.assignment"].search([("team_id", "=", team.id)])
            dates = [a.planned_start for a in assignments if a.planned_start]
            team.last_activity_date = max(dates).date() if dates else False

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_view_assignments(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("gestion_agricole.action_gest_agri_work_assignment")
        action["domain"] = [("team_id", "=", self.id)]
        action["context"] = {"default_team_id": self.id}
        return action
