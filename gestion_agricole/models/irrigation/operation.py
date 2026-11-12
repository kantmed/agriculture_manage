# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriIrrigationOperation(models.Model):
    _name = "gest_agri.irrigation.operation"
    _description = "Opération d'irrigation"
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
    )
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Rattachement
    # ------------------------------------------------------------------
    sector_id = fields.Many2one(
        "gest_agri.irrigation.sector",
        string="Secteur d'irrigation",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    network_id = fields.Many2one(
        related="sector_id.network_id",
        string="Réseau",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    farm_id = fields.Many2one(
        related="sector_id.farm_id",
        string="Exploitation",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id",
        string="Société",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    plot_ids = fields.Many2many(
        related="sector_id.plot_ids",
        string="Parcelles desservies",
        readonly=True,
    )
    pump_id = fields.Many2one(
        "gest_agri.irrigation.pump",
        string="Pompe",
        ondelete="set null",
        check_company=True,
        index=True,
    )
    cycle_id = fields.Many2one(
        "gest_agri.crop.cycle",
        string="Cycle cultural",
        ondelete="set null",
        index=True,
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
    # Consommation
    # ------------------------------------------------------------------
    volume_m3 = fields.Float(string="Volume d'eau (m³)", digits=(16, 3), default=0.0)
    flow_rate_m3_h = fields.Float(
        string="Débit moyen (m³/h)", compute="_compute_flow_rate", store=True, digits=(16, 3)
    )

    # ------------------------------------------------------------------
    # Responsable et observations
    # ------------------------------------------------------------------
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    notes = fields.Text(string="Observations")

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("done", "Terminée"), ("cancelled", "Annulée")],
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
                reference = self.env["ir.sequence"].next_by_code("gest_agri.irrigation.operation")
                if not reference:
                    raise UserError(self.env._("La séquence « gest_agri.irrigation.operation » est introuvable."))
                vals["name"] = reference
            if vals.get("sector_id"):
                sector = self.env["gest_agri.irrigation.sector"].browse(vals["sector_id"])
                if vals.get("pump_id"):
                    pump = self.env["gest_agri.irrigation.pump"].browse(vals["pump_id"])
                    if pump.network_id != sector.network_id:
                        raise ValidationError(
                            self.env._("La pompe ne appartient pas au réseau du secteur.")
                        )
            if vals.get("cycle_id"):
                cycle = self.env["gest_agri.crop.cycle"].browse(vals["cycle_id"])
                sector = self.env["gest_agri.irrigation.sector"].browse(vals.get("sector_id")) if vals.get("sector_id") else None
                farm_id = sector.farm_id.id if sector else None
                if farm_id and cycle.farm_id.id != farm_id:
                    raise ValidationError(self.env._("Le cycle ne appartient pas à l'exploitation."))
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("start_datetime", "end_datetime")
    def _compute_duration(self):
        for op in self:
            if op.start_datetime and op.end_datetime:
                op.duration_hours = (op.end_datetime - op.start_datetime).total_seconds() / 3600.0
            else:
                op.duration_hours = 0.0

    @api.depends("volume_m3", "duration_hours")
    def _compute_flow_rate(self):
        for op in self:
            if op.duration_hours and op.volume_m3:
                op.flow_rate_m3_h = op.volume_m3 / op.duration_hours
            else:
                op.flow_rate_m3_h = 0.0

    # ------------------------------------------------------------------
    # Contraintes
    # ------------------------------------------------------------------
    @api.constrains("start_datetime", "end_datetime")
    def _check_dates(self):
        for op in self:
            if op.end_datetime and op.start_datetime and op.end_datetime < op.start_datetime:
                raise ValidationError(self.env._("La date de fin doit être postérieure à la date de début."))

    @api.constrains("volume_m3")
    def _check_volume(self):
        for op in self:
            if op.volume_m3 < 0:
                raise ValidationError(self.env._("Le volume d'eau ne peut pas être négatif."))

    @api.constrains("sector_id", "start_datetime", "end_datetime")
    def _check_overlap(self):
        for op in self:
            if not op.sector_id or not op.start_datetime or not op.end_datetime:
                continue
            others = self.search(
                [
                    ("id", "!=", op.id),
                    ("sector_id", "=", op.sector_id.id),
                    ("start_datetime", "<", op.end_datetime),
                    ("end_datetime", ">", op.start_datetime),
                    ("state", "!=", "cancelled"),
                ]
            )
            if others:
                raise ValidationError(
                    self.env._("Une opération d'irrigation chevauchante existe déjà sur ce secteur.")
                )

    # ------------------------------------------------------------------
    # Write / workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        protected = {"sector_id", "network_id", "farm_id", "company_id"}
        for op in self:
            if op.state in ("done", "cancelled") and (protected & set(vals)):
                raise UserError(self.env._("L'opération « %s » est terminée ou annulée.", op.display_name))
            if op.state in ("done", "cancelled") and (set(vals) - {"notes", "active"}):
                raise UserError(self.env._("L'opération « %s » est terminée ou annulée.", op.display_name))
        if "state" in vals and not self.env.context.get("gest_agri_irrigation_operation_state_transition"):
            for op in self:
                if op.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_irrigation_operation_state_transition=True).write({"state": target})

    def action_done(self):
        self._check_allowed({"draft"})
        for op in self:
            if not op.end_datetime:
                op.end_datetime = fields.Datetime.now()
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "done"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "done": "Terminée", "cancelled": "Annulée"}
        for op in self:
            if op.state not in allowed:
                raise UserError(self.env._("Transition impossible : l'opération « %(o)s » est à l'état « %(s)s ».", o=op.display_name, s=labels.get(op.state, op.state)))

    def unlink(self):
        for op in self:
            if op.state != "draft":
                raise UserError(self.env._("L'opération « %s » ne peut être supprimée qu'en brouillon.", op.display_name))
        return super().unlink()
