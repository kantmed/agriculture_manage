# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriCropHarvest(models.Model):
    _name = "gest_agri.crop.harvest"
    _description = "Récolte agricole"
    _inherit = ["mail.thread"]
    _order = "harvest_date desc, id desc"
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
        help="Numéro de récolte attribué automatiquement à la création.",
    )
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Rattachement au cycle
    # ------------------------------------------------------------------
    cycle_id = fields.Many2one(
        "gest_agri.crop.cycle",
        string="Cycle de culture",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
        help="Cycle sur lequel la récolte est effectuée.",
    )
    plot_id = fields.Many2one(
        "gest_agri.plot",
        string="Parcelle",
        related="cycle_id.plot_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    campaign_id = fields.Many2one(
        "gest_agri.crop.campaign",
        string="Campagne agricole",
        related="cycle_id.campaign_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    farm_id = fields.Many2one(
        "gest_agri.farm",
        string="Exploitation",
        related="cycle_id.farm_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        related="cycle_id.company_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )

    harvest_date = fields.Date(
        string="Date de récolte",
        required=True,
        index=True,
        tracking=True,
        help="Date à laquelle la récolte a été réalisée.",
    )
    quantity = fields.Float(
        string="Quantité récoltée",
        required=True,
        digits=(16, 3),
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unité de mesure",
        required=True,
        index=True,
        help="Unité de mesure native Odoo. La quantité est convertie selon les règles de conversion Odoo avant agrégation.",
    )
    harvested_area = fields.Float(
        string="Surface récoltée (ha)",
        required=True,
        digits=(16, 3),
        help="Surface concernée par la récolte en hectares.",
    )
    yield_qty = fields.Float(
        string="Rendement (kg/ha)",
        compute="_compute_yield_qty",
        store=True,
        readonly=True,
        digits=(16, 3),
        help="Rendement calculé selon la quantité convertie vers l'unité de référence de la catégorie (en pratique kg pour les unités de masse) divisée par la surface en hectares.",
    )
    notes = fields.Text(string="Observations")
    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("validated", "Validée"),
            ("cancelled", "Annulée"),
        ],
        string="État",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )

    _name_unique = models.UniqueIndex(
        "(UPPER(BTRIM(name)))",
        "La référence de la récolte doit être unique.",
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("cycle_id"):
                raise ValidationError(
                    self.env._("Une récolte doit être rattachée à un cycle de culture.")
                )
            if not vals.get("name"):
                reference = self.env["ir.sequence"].next_by_code(
                    "gest_agri.crop.harvest"
                )
                if not reference:
                    raise UserError(
                        self.env._(
                            "La séquence « gest_agri.crop.harvest » est introuvable : "
                            "impossible d'attribuer une référence à la récolte."
                        )
                    )
                vals["name"] = reference
            if vals.get("cycle_id"):
                cycle = self.env["gest_agri.crop.cycle"].browse(vals["cycle_id"])
                self._check_cycle_state(cycle)
                self._check_derived_values(vals)
        return super().create(vals_list)

    @api.model
    def _check_cycle_state(self, cycle):
        if not cycle:
            return
        if cycle.state == "cancelled":
            raise ValidationError(
                self.env._(
                    "Une récolte ne peut pas être rattachée à un cycle annulé "
                    "« %s ».",
                    cycle.display_name,
                )
            )

    @api.model
    def _check_derived_values(self, vals):
        cycle_id = vals.get("cycle_id")
        if not cycle_id:
            return
        cycle = self.env["gest_agri.crop.cycle"].browse(cycle_id)
        expected = {
            "plot_id": cycle.plot_id.id or False,
            "campaign_id": cycle.campaign_id.id or False,
            "farm_id": cycle.farm_id.id or False,
            "company_id": cycle.company_id.id or False,
        }
        for field_name, expected_id in expected.items():
            current = vals.get(field_name)
            if current and current != expected_id:
                raise UserError(
                    self.env._(
                        "Le champ « %s » est déterminé par le cycle de culture et "
                        "ne peut pas être renseigné manuellement.",
                        field_name,
                    )
                )

    # ------------------------------------------------------------------
    # Calcul du rendement
    # ------------------------------------------------------------------
    @api.depends("quantity", "uom_id", "harvested_area")
    def _compute_yield_qty(self):
        kg_uom = self.env.ref("uom.product_uom_kgm", raise_if_not_found=False)
        for harvest in self:
            if not harvest.quantity or not harvest.harvested_area or not harvest.uom_id:
                harvest.yield_qty = 0.0
                continue
            reference_uom = harvest.uom_id
            if kg_uom and harvest.uom_id._has_common_reference(kg_uom):
                reference_uom = kg_uom
            try:
                converted_quantity = harvest.uom_id._compute_quantity(
                    harvest.quantity,
                    reference_uom,
                    round=False,
                    raise_if_failure=False,
                )
            except (AttributeError, ValueError):
                converted_quantity = harvest.quantity
            harvest.yield_qty = converted_quantity / harvest.harvested_area

    # ------------------------------------------------------------------
    # Contraintes applicatives
    # ------------------------------------------------------------------
    @api.constrains("quantity")
    def _check_quantity(self):
        for harvest in self:
            if harvest.quantity <= 0:
                raise ValidationError(
                    self.env._("La quantité récoltée doit être strictement positive.")
                )

    @api.constrains("harvested_area")
    def _check_harvested_area(self):
        for harvest in self:
            if harvest.harvested_area <= 0:
                raise ValidationError(
                    self.env._(
                        "La surface récoltée doit être strictement positive."
                    )
                )
            if harvest.cycle_id and harvest.harvested_area > harvest.cycle_id.area_ha:
                raise ValidationError(
                    self.env._(
                        "La surface récoltée (%(area)s ha) ne peut pas dépasser la "
                        "surface du cycle « %(cycle)s » (%(cycle_area)s ha).",
                        area=harvest.harvested_area,
                        cycle=harvest.cycle_id.display_name,
                        cycle_area=harvest.cycle_id.area_ha,
                    )
                )

    @api.constrains("cycle_id", "harvest_date")
    def _check_harvest_date(self):
        for harvest in self:
            cycle = harvest.cycle_id
            if not cycle or not harvest.harvest_date:
                continue
            if harvest.harvest_date < cycle.date_start:
                raise ValidationError(
                    self.env._(
                        "La date de récolte ne peut pas être antérieure à la date "
                        "de début du cycle « %s ».",
                        cycle.display_name,
                    )
                )
            cycle_end = cycle.date_end_actual or cycle.date_end_planned
            if cycle_end and harvest.harvest_date > cycle_end:
                raise ValidationError(
                    self.env._(
                        "La date de récolte ne peut pas dépasser la date de fin "
                        "du cycle « %s ».",
                        cycle.display_name,
                    )
                )

    @api.constrains("cycle_id")
    def _check_cycle_compatibility(self):
        for harvest in self:
            cycle = harvest.cycle_id
            if not cycle:
                continue
            if cycle.state == "cancelled":
                raise ValidationError(
                    self.env._(
                        "Une récolte ne peut pas être rattachée à un cycle annulé "
                        "« %s ».",
                        cycle.display_name,
                    )
                )
            if harvest.plot_id and cycle.plot_id and harvest.plot_id != cycle.plot_id:
                raise ValidationError(
                    self.env._(
                        "La parcelle de la récolte doit correspondre à celle du cycle."
                    )
                )
            if harvest.campaign_id and cycle.campaign_id and harvest.campaign_id != cycle.campaign_id:
                raise ValidationError(
                    self.env._(
                        "La campagne de la récolte doit correspondre à celle du cycle."
                    )
                )
            if harvest.farm_id and cycle.farm_id and harvest.farm_id != cycle.farm_id:
                raise ValidationError(
                    self.env._(
                        "L'exploitation de la récolte doit correspondre à celle du cycle."
                    )
                )
            if harvest.company_id and cycle.company_id and harvest.company_id != cycle.company_id:
                raise ValidationError(
                    self.env._(
                        "La société de la récolte doit correspondre à celle du cycle."
                    )
                )

    @api.constrains("uom_id")
    def _check_uom(self):
        for harvest in self:
            if not harvest.uom_id:
                continue
            if harvest.uom_id.factor <= 0:
                raise ValidationError(
                    self.env._(
                        "L'unité de mesure sélectionnée est invalide et ne peut pas servir au calcul du rendement."
                    )
                )

    # ------------------------------------------------------------------
    # Protection des changements d'état et des modifications
    # ------------------------------------------------------------------
    def write(self, vals):
        protected_fields = {"cycle_id", "plot_id", "campaign_id", "farm_id", "company_id"}
        for harvest in self:
            if protected_fields.intersection(vals):
                forbidden = sorted(protected_fields.intersection(vals))
                raise UserError(
                    self.env._(
                        "Les champs dérivés de la récolte ne sont pas modifiables : %s.",
                        ", ".join(forbidden),
                    )
                )
            if harvest.state == "cancelled" and (set(vals) - {"active", "state"}):
                raise AccessError(
                    self.env._(
                        "La récolte « %s » est annulée : aucune modification directe n'est autorisée.",
                        harvest.display_name,
                    )
                )
            if harvest.state == "validated" and (set(vals) - {"active", "state"}):
                raise UserError(
                    self.env._(
                        "La récolte « %s » est validée : seules l'archivage et les transitions d'état sont autorisés.",
                        harvest.display_name,
                    )
                )
        if "state" in vals and not self.env.context.get("gest_agri_harvest_state_transition"):
            for harvest in self:
                if harvest.state != vals["state"]:
                    raise AccessError(
                        self.env._(
                            "Le statut d'une récolte ne peut être modifié qu'à "
                            "travers les actions métier prévues."
                        )
                    )
        return super().write(vals)

    def unlink(self):
        for harvest in self:
            if harvest.state != "draft":
                raise UserError(
                    self.env._(
                        "La récolte « %s » ne peut être supprimée qu'en brouillon.",
                        harvest.display_name,
                    )
                )
        return super().unlink()

    # ------------------------------------------------------------------
    # Actions métier
    # ------------------------------------------------------------------
    def action_validate(self):
        self._check_allowed_states({"draft"})
        self.with_context(gest_agri_harvest_state_transition=True).write({"state": "validated"})

    def action_cancel(self):
        self._check_allowed_states({"draft", "validated"})
        self.with_context(gest_agri_harvest_state_transition=True).write({"state": "cancelled"})

    def _check_allowed_states(self, allowed):
        labels = {"draft": "Brouillon", "validated": "Validée", "cancelled": "Annulée"}
        for harvest in self:
            if harvest.state not in allowed:
                raise UserError(
                    self.env._(
                        "Transition impossible : la récolte « %(harvest)s » est à "
                        "l'état « %(state)s ».",
                        harvest=harvest.display_name,
                        state=labels.get(harvest.state, harvest.state),
                    )
                )
