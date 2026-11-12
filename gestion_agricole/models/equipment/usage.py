# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriEquipmentUsage(models.Model):
    _name = "gest_agri.equipment.usage"
    _description = "Utilisation de matériel agricole"
    _inherit = ["mail.thread"]
    _order = "start_datetime desc, id desc"
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
        help="Numéro d'utilisation attribué automatiquement.",
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
    plot_id = fields.Many2one(
        "gest_agri.plot", string="Parcelle", ondelete="set null", index=True
    )
    intervention_id = fields.Many2one(
        "gest_agri.crop.intervention",
        string="Intervention agricole",
        ondelete="set null",
        index=True,
    )
    operator_id = fields.Many2one(
        "res.users", string="Opérateur", ondelete="set null", index=True
    )

    # ------------------------------------------------------------------
    # Période
    # ------------------------------------------------------------------
    start_datetime = fields.Datetime(string="Début", required=True, index=True)
    end_datetime = fields.Datetime(string="Fin", index=True)
    duration_hours = fields.Float(
        string="Durée (h)", compute="_compute_duration", store=True, digits=(16, 2)
    )

    # ------------------------------------------------------------------
    # Compteurs
    # ------------------------------------------------------------------
    counter_start = fields.Float(string="Compteur début", digits=(16, 2), default=0.0)
    counter_end = fields.Float(string="Compteur fin", digits=(16, 2), default=0.0)
    counter_delta = fields.Float(
        string="Quantité utilisée", compute="_compute_counter_delta", store=True, digits=(16, 2)
    )

    notes = fields.Text(string="Observations")
    state = fields.Selection(
        [("draft", "Brouillon"), ("done", "Terminé"), ("cancelled", "Annulé")],
        string="État",
        default="draft",
        required=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                reference = self.env["ir.sequence"].next_by_code("gest_agri.equipment.usage")
                if not reference:
                    raise UserError(
                        self.env._(
                            "La séquence « gest_agri.equipment.usage » est introuvable."
                        )
                    )
                vals["name"] = reference
            if vals.get("equipment_id"):
                equipment = self.env["gest_agri.equipment"].browse(vals["equipment_id"])
                if equipment.state in ("retired", "out_of_service", "maintenance"):
                    raise ValidationError(
                        self.env._(
                            "L'équipement « %s » n'est pas disponible pour une utilisation.",
                            equipment.display_name,
                        )
                    )
            self._check_derived_coherence(vals)
        return super().create(vals_list)

    @api.model
    def _check_derived_coherence(self, vals):
        equipment = None
        if vals.get("equipment_id"):
            equipment = self.env["gest_agri.equipment"].browse(vals["equipment_id"])
        farm_id = vals.get("farm_id") or (equipment.farm_id.id if equipment else None)
        if equipment and farm_id and equipment.farm_id.id != farm_id:
            raise ValidationError(
                self.env._("L'exploitation doit correspondre à celle de l'équipement.")
            )
        if vals.get("plot_id") and farm_id:
            plot = self.env["gest_agri.plot"].browse(vals["plot_id"])
            if plot.farm_id.id != farm_id:
                raise ValidationError(
                    self.env._("La parcelle n'appartient pas à l'exploitation.")
                )

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("start_datetime", "end_datetime")
    def _compute_duration(self):
        for usage in self:
            if usage.start_datetime and usage.end_datetime:
                delta = usage.end_datetime - usage.start_datetime
                usage.duration_hours = delta.total_seconds() / 3600.0
            else:
                usage.duration_hours = 0.0

    @api.depends("counter_start", "counter_end")
    def _compute_counter_delta(self):
        for usage in self:
            usage.counter_delta = usage.counter_end - usage.counter_start

    # ------------------------------------------------------------------
    # Contraintes
    # ------------------------------------------------------------------
    @api.constrains("start_datetime", "end_datetime")
    def _check_dates(self):
        for usage in self:
            if usage.end_datetime and usage.start_datetime and usage.end_datetime < usage.start_datetime:
                raise ValidationError(
                    self.env._("La date de fin doit être postérieure à la date de début.")
                )

    @api.constrains("counter_start", "counter_end")
    def _check_counters(self):
        for usage in self:
            if usage.counter_end and usage.counter_end < usage.counter_start:
                raise ValidationError(
                    self.env._("Le compteur final doit être supérieur ou égal au compteur initial.")
                )
            if usage.counter_start < 0 or usage.counter_end < 0:
                raise ValidationError(
                    self.env._("Les compteurs ne peuvent pas être négatifs.")
                )

    @api.constrains("equipment_id", "start_datetime", "end_datetime")
    def _check_overlap(self):
        for usage in self:
            if not usage.equipment_id or not usage.start_datetime or not usage.end_datetime:
                continue
            others = self.search(
                [
                    ("id", "!=", usage.id),
                    ("equipment_id", "=", usage.equipment_id.id),
                    ("start_datetime", "<", usage.end_datetime),
                    ("end_datetime", ">", usage.start_datetime),
                ]
            )
            if others:
                raise ValidationError(
                    self.env._(
                        "L'équipement « %s » est déjà utilisé sur une période chevauchante.",
                        usage.equipment_id.display_name,
                    )
                )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_equipment_usage_state_transition"):
            for usage in self:
                if usage.state != vals["state"]:
                    raise AccessError(
                        self.env._("Le statut d'une utilisation ne peut être modifié qu'à travers les actions métier.")
                    )
        return super().write(vals)

    def action_done(self):
        self.with_context(gest_agri_equipment_usage_state_transition=True).write({"state": "done"})

    def action_cancel(self):
        self.with_context(gest_agri_equipment_usage_state_transition=True).write({"state": "cancelled"})
