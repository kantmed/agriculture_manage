# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

STATE_SELECTION = [
    ("draft", "Brouillon"),
    ("active", "En cours"),
    ("closed", "Clôturée"),
    ("cancelled", "Annulée"),
]

# Données métier verrouillées une fois la campagne clôturée ou annulée.
# L'archivage et l'ordre d'affichage restent modifiables.
PROTECTED_FIELDS = frozenset(
    {
        "name",
        "code",
        "farm_id",
        "date_start",
        "date_end",
        "date_end_actual",
        "description",
        "notes",
    }
)


class GestAgriCropCampaign(models.Model):
    _name = "gest_agri.crop.campaign"
    _description = "Campagne agricole"
    _inherit = ["mail.thread"]
    _order = "date_start desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(
        string="Code",
        required=True,
        copy=False,
        index=True,
        help="Référence unique attribuée automatiquement à la création.",
    )
    farm_id = fields.Many2one(
        "gest_agri.farm",
        string="Exploitation",
        required=True,
        ondelete="cascade",
        check_company=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        related="farm_id.company_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    date_start = fields.Date(string="Date de début", required=True)
    date_end = fields.Date(string="Date de fin prévue")
    date_end_actual = fields.Date(string="Date de clôture réelle")
    state = fields.Selection(
        selection=STATE_SELECTION,
        string="État",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )
    description = fields.Text(string="Description")
    notes = fields.Text(string="Notes internes")
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)
    crop_cycle_ids = fields.One2many(
        "gest_agri.crop.cycle",
        "campaign_id",
        string="Cycles de culture",
    )
    crop_cycle_count = fields.Integer(
        string="Nombre de cycles",
        compute="_compute_crop_cycle_count",
    )

    _code_unique = models.UniqueIndex(
        "(UPPER(BTRIM(code)))",
        "Le code de la campagne doit être unique.",
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                reference = self.env["ir.sequence"].next_by_code(
                    "gest_agri.crop.campaign"
                )
                if not reference:
                    raise UserError(
                        self.env._(
                            "La séquence « gest_agri.crop.campaign » est introuvable : "
                            "impossible d'attribuer un code à la campagne."
                        )
                    )
                vals["code"] = reference
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Contraintes applicatives
    # ------------------------------------------------------------------
    @api.constrains("code")
    def _check_code_unique(self):
        for campaign in self:
            if not campaign.code:
                continue
            duplicate = (
                self.sudo()
                .with_context(active_test=False)
                .search(
                    [
                        ("id", "!=", campaign.id),
                        ("code", "=ilike", campaign.code.strip()),
                    ],
                    limit=1,
                )
            )
            if duplicate:
                raise ValidationError(
                    self.env._(
                        "Le code de campagne « %s » est déjà utilisé.",
                        campaign.code,
                    )
                )

    @api.constrains("date_start", "date_end")
    def _check_date_end(self):
        for campaign in self:
            if campaign.date_end and campaign.date_end < campaign.date_start:
                raise ValidationError(
                    self.env._(
                        "La date de fin prévue ne peut pas être antérieure à la "
                        "date de début de la campagne."
                    )
                )

    @api.constrains("date_start", "date_end_actual")
    def _check_date_end_actual(self):
        for campaign in self:
            if campaign.date_end_actual and campaign.date_end_actual < campaign.date_start:
                raise ValidationError(
                    self.env._(
                        "La date de clôture réelle ne peut pas être antérieure à "
                        "la date de début de la campagne."
                    )
                )

    @api.constrains("state", "date_end_actual")
    def _check_closed_requires_end_date(self):
        for campaign in self:
            if campaign.state == "closed" and not campaign.date_end_actual:
                raise ValidationError(
                    self.env._(
                        "La date de clôture réelle est obligatoire pour clôturer "
                        "la campagne « %s ».",
                        campaign.display_name,
                    )
                )

    # ------------------------------------------------------------------
    # Protection des données et des transitions d'état
    # ------------------------------------------------------------------
    def write(self, vals):
        if {"farm_id", "date_start", "date_end"}.intersection(vals):
            for campaign in self:
                campaign._check_cycles_compatible(
                    self.env["gest_agri.farm"].browse(vals["farm_id"])
                    if "farm_id" in vals
                    else campaign.farm_id,
                    vals.get("date_start", campaign.date_start),
                    vals.get("date_end", campaign.date_end),
                )
        if PROTECTED_FIELDS.intersection(vals):
            for campaign in self:
                if campaign.state in ("closed", "cancelled"):
                    raise UserError(
                        self.env._(
                            "La campagne « %(campaign)s » est %(state)s : ses "
                            "données métier ne peuvent plus être modifiées.",
                            campaign=campaign.display_name,
                            state=dict(STATE_SELECTION).get(
                                campaign.state, campaign.state
                            ).lower(),
                        )
                    )
        if "state" in vals and not self.env.context.get(
            "gest_agri_campaign_state_transition"
        ):
            for campaign in self:
                if campaign.state != vals["state"]:
                    raise AccessError(
                        self.env._(
                            "L'état d'une campagne ne peut être modifié que par "
                            "les boutons de transition prévus."
                        )
                    )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Cycles rattachés
    # ------------------------------------------------------------------
    @api.depends("crop_cycle_ids")
    def _compute_crop_cycle_count(self):
        Cycle = self.env["gest_agri.crop.cycle"].with_context(active_test=False)
        for campaign in self:
            campaign.crop_cycle_count = Cycle.search_count(
                [("campaign_id", "=", campaign.id)]
            )

    def _check_cycles_compatible(self, farm, date_start, date_end):
        """Vérifie qu'une modification de campagne reste compatible.

        Contrôle effectué côté serveur sur tous les cycles rattachés, y
        compris archivés, avant toute modification de l'exploitation ou des
        dates de la campagne.
        """
        cycles = (
            self.env["gest_agri.crop.cycle"]
            .sudo()
            .with_context(active_test=False)
            .search([("campaign_id", "=", self.id)])
        )
        for cycle in cycles:
            if farm and cycle.farm_id != farm:
                raise ValidationError(
                    self.env._(
                        "La campagne ne peut pas être rattachée à l'exploitation "
                        "« %(farm)s » : le cycle « %(cycle)s » appartient à "
                        "l'exploitation « %(cycle_farm)s ».",
                        farm=farm.display_name,
                        cycle=cycle.display_name,
                        cycle_farm=cycle.farm_id.display_name,
                    )
                )
            if date_start and cycle.date_start < date_start:
                raise ValidationError(
                    self.env._(
                        "La date de début de la campagne (%(start)s) est postérieure "
                        "au début du cycle « %(cycle)s » (%(cycle_start)s).",
                        start=date_start,
                        cycle=cycle.display_name,
                        cycle_start=cycle.date_start,
                    )
                )
            if date_end:
                cycle_end = cycle.date_end_actual or cycle.date_end_planned
                if not cycle_end:
                    raise ValidationError(
                        self.env._(
                            "La campagne ne peut pas avoir de date de fin : le "
                            "cycle « %s » a une fin ouverte.",
                            cycle.display_name,
                        )
                    )
                if cycle_end > date_end:
                    raise ValidationError(
                        self.env._(
                            "La fin prévue de la campagne (%(end)s) précède la fin "
                            "du cycle « %(cycle)s » (%(cycle_end)s).",
                            end=date_end,
                            cycle=cycle.display_name,
                            cycle_end=cycle_end,
                        )
                    )

    def _check_allowed_states(self, allowed):
        labels = dict(STATE_SELECTION)
        for campaign in self:
            if campaign.state not in allowed:
                raise UserError(
                    self.env._(
                        "Transition impossible : la campagne « %(campaign)s » est "
                        "à l'état « %(current)s ».",
                        campaign=campaign.display_name,
                        current=labels.get(campaign.state, campaign.state),
                    )
                )

    def _apply_state(self, target):
        self.with_context(gest_agri_campaign_state_transition=True).write(
            {"state": target}
        )

    # ------------------------------------------------------------------
    # Boutons de transition
    # ------------------------------------------------------------------
    def action_activate(self):
        """Brouillon → En cours."""
        self._check_allowed_states({"draft"})
        self._apply_state("active")

    def action_close(self):
        """En cours → Clôturée (date de clôture réelle obligatoire)."""
        self._check_allowed_states({"active"})
        for campaign in self:
            if not campaign.date_end_actual:
                raise UserError(
                    self.env._(
                        "Renseignez la date de clôture réelle avant de clôturer "
                        "la campagne « %s ».",
                        campaign.display_name,
                    )
                )
        self._apply_state("closed")

    def action_cancel(self):
        """Brouillon ou En cours → Annulée."""
        self._check_allowed_states({"draft", "active"})
        self._apply_state("cancelled")
