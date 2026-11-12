# -*- coding: utf-8 -*-
from datetime import date, datetime

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriEquipment(models.Model):
    _name = "gest_agri.equipment"
    _description = "Équipement agricole"
    _inherit = ["mail.thread"]
    _order = "farm_id, sequence, name"
    _check_company_auto = True

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(string="Désignation", required=True, index=True)
    reference = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        index=True,
        readonly=True,
        help="Numéro d'équipement attribué automatiquement.",
    )
    equipment_type_id = fields.Many2one(
        "gest_agri.equipment.type",
        string="Type de matériel",
        required=True,
        ondelete="restrict",
        check_company=True,
        index=True,
    )
    brand = fields.Char(string="Marque")
    model = fields.Char(string="Modèle commercial")
    serial_number = fields.Char(string="Numéro de série", index=True)
    registration_number = fields.Char(string="Immatriculation", index=True)
    description = fields.Text(string="Description")
    image_1920 = fields.Image(string="Photographie", max_width=1920, max_height=1920)

    # ------------------------------------------------------------------
    # Rattachement organisationnel
    # ------------------------------------------------------------------
    farm_id = fields.Many2one(
        "gest_agri.farm",
        string="Exploitation",
        required=True,
        ondelete="cascade",
        check_company=True,
        index=True,
    )
    site_id = fields.Many2one(
        "gest_agri.site",
        string="Site",
        ondelete="set null",
        check_company=True,
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
    location = fields.Char(string="Emplacement / localisation")

    # ------------------------------------------------------------------
    # Informations d'acquisition
    # ------------------------------------------------------------------
    acquisition_date = fields.Date(string="Date d'acquisition")
    acquisition_price = fields.Float(
        string="Prix d'acquisition", digits=(16, 2), default=0.0
    )
    supplier_id = fields.Many2one(
        "res.partner", string="Fournisseur", ondelete="set null", index=True
    )
    commissioning_date = fields.Date(string="Date de mise en service")
    warranty_end_date = fields.Date(string="Fin de garantie")
    condition = fields.Selection(
        selection=[("new", "Neuf"), ("used", "Occasion")],
        string="État d'acquisition",
        default="new",
    )
    notes = fields.Text(string="Observations")

    # ------------------------------------------------------------------
    # Compteurs
    # ------------------------------------------------------------------
    hour_meter = fields.Float(
        string="Compteur horaire (h)", digits=(16, 2), default=0.0
    )
    odometer = fields.Float(
        string="Compteur kilométrique (km)", digits=(16, 2), default=0.0
    )
    cycle_counter = fields.Float(
        string="Compteur de cycles / unités", digits=(16, 2), default=0.0
    )

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("available", "Disponible"),
            ("in_use", "En utilisation"),
            ("maintenance", "En maintenance"),
            ("out_of_service", "Hors service"),
            ("retired", "Retiré du service"),
        ],
        string="État",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    # ------------------------------------------------------------------
    # Relations et statistiques
    # ------------------------------------------------------------------
    usage_ids = fields.One2many(
        "gest_agri.equipment.usage", "equipment_id", string="Utilisations"
    )
    usage_count = fields.Integer(
        string="Nombre d'utilisations", compute="_compute_usage_count"
    )
    maintenance_ids = fields.One2many(
        "gest_agri.equipment.maintenance", "equipment_id", string="Maintenances"
    )
    maintenance_count = fields.Integer(
        string="Nombre de maintenances", compute="_compute_maintenance_count"
    )
    last_usage_date = fields.Datetime(
        string="Dernière utilisation", compute="_compute_last_usage_date", store=False
    )
    last_maintenance_date = fields.Date(
        string="Dernière maintenance", compute="_compute_last_maintenance_date", store=False
    )
    next_maintenance_date = fields.Date(string="Prochaine échéance (date)")
    next_maintenance_hours = fields.Float(
        string="Prochaine échéance (heures)", digits=(16, 2), default=0.0
    )
    next_maintenance_km = fields.Float(
        string="Prochaine échéance (km)", digits=(16, 2), default=0.0
    )
    total_maintenance_cost = fields.Float(
        string="Coût total maintenance", compute="_compute_total_maintenance_cost",
        digits=(16, 2),
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                reference = self.env["ir.sequence"].next_by_code("gest_agri.equipment")
                if not reference:
                    raise UserError(
                        self.env._(
                            "La séquence « gest_agri.equipment » est introuvable : "
                            "impossible d'attribuer une référence à l'équipement."
                        )
                    )
                vals["reference"] = reference
            if not vals.get("name"):
                vals["name"] = vals["reference"]
            if vals.get("farm_id") and vals.get("site_id"):
                farm = self.env["gest_agri.farm"].browse(vals["farm_id"])
                site = self.env["gest_agri.site"].browse(vals["site_id"])
                if site.farm_id != farm:
                    raise ValidationError(
                        self.env._("Le site ne appartient pas à l'exploitation.")
                    )
            if vals.get("farm_id"):
                farm = self.env["gest_agri.farm"].browse(vals["farm_id"])
                if vals.get("company_id") and farm.company_id.id != vals["company_id"]:
                    raise ValidationError(
                        self.env._("Incohérence de société entre l'équipement et l'exploitation.")
                    )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("usage_ids", "usage_ids.active")
    def _compute_usage_count(self):
        for equipment in self:
            equipment.usage_count = len(
                equipment.with_context(active_test=False).usage_ids
            )

    @api.depends("maintenance_ids", "maintenance_ids.active")
    def _compute_maintenance_count(self):
        for equipment in self:
            equipment.maintenance_count = len(
                equipment.with_context(active_test=False).maintenance_ids
            )

    @api.depends("usage_ids", "usage_ids.start_datetime")
    def _compute_last_usage_date(self):
        for equipment in self:
            usages = equipment.with_context(active_test=False).usage_ids
            if usages:
                equipment.last_usage_date = max(u.start_datetime for u in usages if u.start_datetime)
            else:
                equipment.last_usage_date = False

    @api.depends("maintenance_ids", "maintenance_ids.realized_date")
    def _compute_last_maintenance_date(self):
        for equipment in self:
            maints = equipment.with_context(active_test=False).maintenance_ids.filtered(
                lambda m: m.state == "done" and m.realized_date
            )
            if maints:
                equipment.last_maintenance_date = max(m.realized_date for m in maints)
            else:
                equipment.last_maintenance_date = False

    @api.depends("maintenance_ids", "maintenance_ids.total_cost")
    def _compute_total_maintenance_cost(self):
        for equipment in self:
            equipment.total_maintenance_cost = sum(
                m.total_cost for m in equipment.with_context(active_test=False).maintenance_ids
            )

    # ------------------------------------------------------------------
    # Contraintes
    # ------------------------------------------------------------------
    @api.constrains("hour_meter", "odometer", "cycle_counter")
    def _check_counters_positive(self):
        for equipment in self:
            if equipment.hour_meter < 0 or equipment.odometer < 0 or equipment.cycle_counter < 0:
                raise ValidationError(
                    self.env._("Les compteurs ne peuvent pas être négatifs.")
                )

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for equipment in self:
            if equipment.site_id and equipment.site_id.farm_id != equipment.farm_id:
                raise ValidationError(
                    self.env._(
                        "Le site « %(site)s » n'appartient pas à l'exploitation « %(farm)s ».",
                        site=equipment.site_id.display_name,
                        farm=equipment.farm_id.display_name,
                    )
                )

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_equipment_state_transition"):
            for equipment in self:
                if equipment.state != vals["state"]:
                    raise AccessError(
                        self.env._(
                            "L'état d'un équipement ne peut être modifié qu'à travers "
                            "les actions métier prévues."
                        )
                    )
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_equipment_state_transition=True).write({"state": target})

    def action_available(self):
        self._check_allowed_states({"draft", "maintenance", "out_of_service"})
        self._apply_state("available")

    def action_in_use(self):
        self._check_allowed_states({"available"})
        self._apply_state("in_use")

    def action_maintenance(self):
        self._check_allowed_states({"available", "in_use", "out_of_service"})
        self._apply_state("maintenance")

    def action_out_of_service(self):
        self._check_allowed_states({"available", "maintenance", "in_use"})
        self._apply_state("out_of_service")

    def action_retire(self):
        self._check_allowed_states({"available", "out_of_service", "maintenance"})
        self._apply_state("retired")

    def action_reset_draft(self):
        self._check_allowed_states({"retired"})
        self._apply_state("draft")

    def _check_allowed_states(self, allowed):
        labels = {
            "draft": "Brouillon", "available": "Disponible", "in_use": "En utilisation",
            "maintenance": "En maintenance", "out_of_service": "Hors service",
            "retired": "Retiré du service",
        }
        for equipment in self:
            if equipment.state not in allowed:
                raise UserError(
                    self.env._(
                        "Transition impossible : l'équipement « %(eq)s » est à "
                        "l'état « %(state)s ».",
                        eq=equipment.display_name,
                        state=labels.get(equipment.state, equipment.state),
                    )
                )

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_view_usages(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "gestion_agricole.action_gest_agri_equipment_usage"
        )
        action["domain"] = [("equipment_id", "=", self.id)]
        action["context"] = {"default_equipment_id": self.id}
        return action

    def action_view_maintenances(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "gestion_agricole.action_gest_agri_equipment_maintenance"
        )
        action["domain"] = [("equipment_id", "=", self.id)]
        action["context"] = {"default_equipment_id": self.id}
        return action
