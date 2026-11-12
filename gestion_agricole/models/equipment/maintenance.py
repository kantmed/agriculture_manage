# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriEquipmentMaintenance(models.Model):
    _name = "gest_agri.equipment.maintenance"
    _description = "Maintenance de matériel agricole"
    _inherit = ["mail.thread"]
    _order = "planned_date desc, id desc"
    _check_company_auto = True

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        index=True,
        readonly=True,
        help="Numéro de maintenance attribué automatiquement.",
    )
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Rattachement
    # ------------------------------------------------------------------
    equipment_id = fields.Many2one(
        "gest_agri.equipment",
        string="Équipement",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    farm_id = fields.Many2one(
        related="equipment_id.farm_id",
        string="Exploitation",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    company_id = fields.Many2one(
        related="equipment_id.company_id",
        string="Société",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Type et dates
    # ------------------------------------------------------------------
    maintenance_type = fields.Selection(
        selection=[
            ("preventive", "Préventive"),
            ("corrective", "Corrective"),
            ("inspection", "Inspection"),
            ("revision", "Révision"),
            ("repair", "Réparation"),
        ],
        string="Type de maintenance",
        required=True,
        default="preventive",
        index=True,
    )
    planned_date = fields.Date(string="Date prévue", index=True)
    realized_date = fields.Date(string="Date de réalisation", index=True)
    duration_hours = fields.Float(string="Durée (h)", digits=(16, 2), default=0.0)

    # ------------------------------------------------------------------
    # Intervenants
    # ------------------------------------------------------------------
    provider_id = fields.Many2one(
        "res.partner", string="Prestataire", ondelete="set null", index=True
    )
    technician_id = fields.Many2one(
        "res.users", string="Technicien / responsable", ondelete="set null", index=True
    )

    # ------------------------------------------------------------------
    # Descriptions
    # ------------------------------------------------------------------
    problem_description = fields.Text(string="Problème constaté")
    work_description = fields.Text(string="Travaux effectués")
    parts_used = fields.Text(string="Pièces / consommables")
    notes = fields.Text(string="Observations")

    # ------------------------------------------------------------------
    # Compteurs
    # ------------------------------------------------------------------
    counter_at_maintenance = fields.Float(
        string="Compteur à la maintenance", digits=(16, 2), default=0.0
    )

    # ------------------------------------------------------------------
    # Coûts
    # ------------------------------------------------------------------
    parts_cost = fields.Float(string="Coût pièces", digits=(16, 2), default=0.0)
    labor_cost = fields.Float(string="Coût main-d'œuvre", digits=(16, 2), default=0.0)
    external_cost = fields.Float(string="Coût externe", digits=(16, 2), default=0.0)
    total_cost = fields.Float(
        string="Coût total", compute="_compute_total_cost", store=True, digits=(16, 2)
    )

    # ------------------------------------------------------------------
    # Échéance préventive
    # ------------------------------------------------------------------
    next_due_date = fields.Date(string="Prochaine échéance (date)")
    next_due_hours = fields.Float(string="Prochaine échéance (heures)", digits=(16, 2), default=0.0)
    next_due_km = fields.Float(string="Prochaine échéance (km)", digits=(16, 2), default=0.0)

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("planned", "Planifiée"),
            ("in_progress", "En cours"),
            ("done", "Terminée"),
            ("cancelled", "Annulée"),
        ],
        string="État",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                reference = self.env["ir.sequence"].next_by_code("gest_agri.equipment.maintenance")
                if not reference:
                    raise UserError(
                        self.env._(
                            "La séquence « gest_agri.equipment.maintenance » est introuvable."
                        )
                    )
                vals["name"] = reference
            if vals.get("equipment_id"):
                equipment = self.env["gest_agri.equipment"].browse(vals["equipment_id"])
                self._check_equipment_available(equipment)
        return super().create(vals_list)

    @api.model
    def _check_equipment_available(self, equipment):
        if not equipment:
            return
        if equipment.state in ("retired", "out_of_service"):
            raise ValidationError(
                self.env._(
                    "L'équipement « %s » n'est pas disponible pour une maintenance.",
                    equipment.display_name,
                )
            )

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("parts_cost", "labor_cost", "external_cost")
    def _compute_total_cost(self):
        for maintenance in self:
            maintenance.total_cost = (
                maintenance.parts_cost + maintenance.labor_cost + maintenance.external_cost
            )

    # ------------------------------------------------------------------
    # Contraintes
    # ------------------------------------------------------------------
    @api.constrains("planned_date", "realized_date")
    def _check_dates(self):
        for maintenance in self:
            if maintenance.realized_date and maintenance.planned_date and maintenance.realized_date < maintenance.planned_date:
                # allowed: realization can be earlier than planned? keep simple: no strict check
                pass

    @api.constrains("counter_at_maintenance")
    def _check_counter(self):
        for maintenance in self:
            if maintenance.counter_at_maintenance < 0:
                raise ValidationError(
                    self.env._("Le compteur ne peut pas être négatif.")
                )

    # ------------------------------------------------------------------
    # Write / workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_equipment_maintenance_state_transition"):
            for maintenance in self:
                if maintenance.state != vals["state"]:
                    raise AccessError(
                        self.env._("Le statut d'une maintenance ne peut être modifié qu'à travers les actions métier.")
                    )
        # Maintenance en cours rend l'équipement indisponible
        if vals.get("state") == "in_progress":
            for maintenance in self:
                if maintenance.equipment_id.state not in ("available", "maintenance"):
                    pass
                maintenance.equipment_id.with_context(gest_agri_equipment_state_transition=True).write(
                    {"state": "maintenance"}
                )
        if vals.get("state") == "done":
            for maintenance in self:
                # remettre à disposition si possible
                if maintenance.equipment_id.state == "maintenance":
                    maintenance.equipment_id.with_context(gest_agri_equipment_state_transition=True).write(
                        {"state": "available"}
                    )
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_equipment_maintenance_state_transition=True).write({"state": target})

    def action_plan(self):
        self._check_allowed_states({"draft"})
        self._apply_state("planned")

    def action_start(self):
        self._check_allowed_states({"planned"})
        self._apply_state("in_progress")

    def action_done(self):
        self._check_allowed_states({"in_progress"})
        for maintenance in self:
            if not maintenance.realized_date:
                maintenance.realized_date = fields.Date.today()
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed_states({"draft", "planned", "in_progress"})
        self._apply_state("cancelled")

    def _check_allowed_states(self, allowed):
        labels = {"draft": "Brouillon", "planned": "Planifiée", "in_progress": "En cours",
                  "done": "Terminée", "cancelled": "Annulée"}
        for maintenance in self:
            if maintenance.state not in allowed:
                raise UserError(
                    self.env._(
                        "Transition impossible : la maintenance « %(m)s » est à "
                        "l'état « %(state)s ».",
                        m=maintenance.display_name,
                        state=labels.get(maintenance.state, maintenance.state),
                    )
                )

    def unlink(self):
        for maintenance in self:
            if maintenance.state != "draft":
                raise UserError(
                    self.env._("La maintenance « %s » ne peut être supprimée qu'en brouillon.", maintenance.display_name)
                )
        return super().unlink()
