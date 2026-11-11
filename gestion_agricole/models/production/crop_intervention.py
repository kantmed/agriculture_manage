# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

STATE_SELECTION = [
    ("draft", "Brouillon"),
    ("planned", "Planifiée"),
    ("done", "Réalisée"),
    ("cancelled", "Annulée"),
]

# Champs strictement dérivés du cycle de culture : ils ne sont jamais saisis
# ni modifiés directement. Toute tentative est refusée côté serveur.
DERIVED_FIELDS = frozenset(
    {
        "campaign_id",
        "plot_id",
        "farm_id",
        "company_id",
    }
)

# Champs figés une fois l'intervention réalisée : l'historique ne doit plus
# être réécrit.
LOCKED_ON_DONE = frozenset(
    {
        "crop_cycle_id",
        "operation_type_id",
        "date_planned",
        "date_actual",
    }
)


class GestAgriCropIntervention(models.Model):
    _name = "gest_agri.crop.intervention"
    _description = "Intervention agricole"
    _inherit = ["mail.thread"]
    _order = "date_actual desc nulls last, date_planned desc nulls last, id desc"
    _check_company_auto = True

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string="Libellé",
        required=True,
        index=True,
        help="Libellé de l'intervention agricole.",
    )
    code = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        index=True,
        help="Référence unique attribuée automatiquement à la création.",
    )
    sequence = fields.Integer(string="Séquence", default=10, required=True)
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Rattachement au cycle de culture
    # ------------------------------------------------------------------
    crop_cycle_id = fields.Many2one(
        "gest_agri.crop.cycle",
        string="Cycle de culture",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
        help="Culture implantée sur laquelle l'intervention est enregistrée.",
    )
    campaign_id = fields.Many2one(
        "gest_agri.crop.campaign",
        string="Campagne agricole",
        related="crop_cycle_id.campaign_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    plot_id = fields.Many2one(
        "gest_agri.plot",
        string="Parcelle",
        related="crop_cycle_id.plot_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    farm_id = fields.Many2one(
        "gest_agri.farm",
        string="Exploitation",
        related="crop_cycle_id.farm_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        related="crop_cycle_id.company_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Type d'intervention
    # ------------------------------------------------------------------
    operation_type_id = fields.Many2one(
        "gest_agri.operation.type",
        string="Type d'intervention",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
        domain="[('active', '=', True), '|', ('company_id', '=', False), "
        "('company_id', '=', company_id)]",
        help="Type de travail agricole effectué (labour, semis, fertilisation...).",
    )

    # ------------------------------------------------------------------
    # Planification et réalisation
    # ------------------------------------------------------------------
    date_planned = fields.Date(
        string="Date prévue",
        help="Date prévue de réalisation de l'intervention.",
    )
    date_actual = fields.Date(
        string="Date réelle",
        help="Date effective de réalisation de l'intervention.",
    )

    # ------------------------------------------------------------------
    # État et suivi
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=STATE_SELECTION,
        string="État",
        default="draft",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )
    description = fields.Text(string="Description des travaux")
    notes = fields.Text(string="Notes internes")

    _code_unique = models.UniqueIndex(
        "(UPPER(BTRIM(code)))",
        "Le code de l'intervention doit être unique.",
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                reference = self.env["ir.sequence"].next_by_code(
                    "gest_agri.crop.intervention"
                )
                if not reference:
                    raise UserError(
                        self.env._(
                            "La séquence « gest_agri.crop.intervention » est "
                            "introuvable : impossible d'attribuer une référence "
                            "à l'intervention."
                        )
                    )
                vals["code"] = reference
            self._check_derived_values(vals)
        return super().create(vals_list)

    @api.model
    def _check_derived_values(self, vals):
        """Refuse des valeurs dérivées incohérentes avec le cycle choisi."""
        cycle_id = vals.get("crop_cycle_id")
        if not cycle_id:
            return
        cycle = self.env["gest_agri.crop.cycle"].browse(cycle_id)
        expected = {
            "campaign_id": cycle.campaign_id.id or False,
            "plot_id": cycle.plot_id.id or False,
            "farm_id": cycle.farm_id.id or False,
            "company_id": cycle.company_id.id or False,
        }
        for fname, expected_id in expected.items():
            given = vals.get(fname)
            if given and given != expected_id:
                raise UserError(
                    self.env._(
                        "Le champ « %s » est déterminé par le cycle de culture et "
                        "ne peut pas être renseigné manuellement.",
                        fname,
                    )
                )

    # ------------------------------------------------------------------
    # Contraintes applicatives
    # ------------------------------------------------------------------
    @api.constrains("code")
    def _check_code_unique(self):
        for intervention in self:
            if not intervention.code:
                continue
            duplicate = (
                self.sudo()
                .with_context(active_test=False)
                .search(
                    [
                        ("id", "!=", intervention.id),
                        ("code", "=ilike", intervention.code.strip()),
                    ],
                    limit=1,
                )
            )
            if duplicate:
                raise ValidationError(
                    self.env._(
                        "Le code d'intervention « %s » est déjà utilisé.",
                        intervention.code,
                    )
                )

    @api.constrains("operation_type_id")
    def _check_operation_type(self):
        for intervention in self:
            operation_type = intervention.operation_type_id
            if not operation_type:
                continue
            if not operation_type.active:
                raise ValidationError(
                    self.env._(
                        "Le type d'intervention « %s » est archivé : il ne peut "
                        "plus être utilisé.",
                        operation_type.display_name,
                    )
                )

    @api.constrains("crop_cycle_id", "date_planned", "date_actual", "state")
    def _check_dates_within_cycle(self):
        """Les dates de l'intervention doivent rester dans la période du cycle.

        Une intervention annulée est sans effet : elle n'est pas contrôlée.
        """
        for intervention in self:
            if intervention.state == "cancelled":
                continue
            cycle = intervention.crop_cycle_id
            if not cycle:
                continue
            cycle_end = cycle.date_end_actual or cycle.date_end_planned
            for label, value in (
                ("prévue", intervention.date_planned),
                ("réelle", intervention.date_actual),
            ):
                if not value:
                    continue
                if value < cycle.date_start:
                    raise ValidationError(
                        self.env._(
                            "La date %(label)s de l'intervention « %(intervention)s » "
                            "(%(value)s) est antérieure au début de la culture "
                            "« %(cycle)s » (%(start)s).",
                            label=label,
                            intervention=intervention.display_name,
                            value=value,
                            cycle=cycle.display_name,
                            start=cycle.date_start,
                        )
                    )
                if cycle_end and value > cycle_end:
                    raise ValidationError(
                        self.env._(
                            "La date %(label)s de l'intervention « %(intervention)s » "
                            "(%(value)s) est postérieure à la fin de la culture "
                            "« %(cycle)s » (%(end)s).",
                            label=label,
                            intervention=intervention.display_name,
                            value=value,
                            cycle=cycle.display_name,
                            end=cycle_end,
                        )
                    )

    @api.constrains("state", "date_actual")
    def _check_done_requires_date(self):
        for intervention in self:
            if intervention.state == "done" and not intervention.date_actual:
                raise ValidationError(
                    self.env._(
                        "La date réelle est obligatoire pour réaliser "
                        "l'intervention « %s ».",
                        intervention.display_name,
                    )
                )

    # ------------------------------------------------------------------
    # Protection des transitions d'état et des champs dérivés
    # ------------------------------------------------------------------
    def write(self, vals):
        if DERIVED_FIELDS.intersection(vals):
            raise UserError(
                self.env._(
                    "La parcelle, l'exploitation, la société et la campagne d'une "
                    "intervention sont déterminées par son cycle de culture et "
                    "ne peuvent pas être modifiées."
                )
            )
        if "state" in vals and not self.env.context.get(
            "gest_agri_intervention_state_transition"
        ):
            for intervention in self:
                if intervention.state != vals["state"]:
                    raise AccessError(
                        self.env._(
                            "L'état d'une intervention ne peut être modifié que "
                            "par les boutons de transition prévus."
                        )
                    )
        for intervention in self:
            if intervention.state == "done" and LOCKED_ON_DONE.intersection(vals):
                raise UserError(
                    self.env._(
                        "L'intervention « %s » est réalisée : ses données "
                        "d'exécution ne sont plus modifiables.",
                        intervention.display_name,
                    )
                )
        return super().write(vals)

    def unlink(self):
        for intervention in self:
            if intervention.state == "done" and not self.env.user.has_group(
                "gestion_agricole.group_gest_agri_admin"
            ):
                raise AccessError(
                    self.env._(
                        "Une intervention réalisée ne peut pas être supprimée par "
                        "les profils ordinaires."
                    )
                )
        return super().unlink()

    def _check_allowed_states(self, allowed):
        labels = dict(STATE_SELECTION)
        for intervention in self:
            if intervention.state not in allowed:
                raise UserError(
                    self.env._(
                        "Transition impossible : l'intervention « %(intervention)s » "
                        "est à l'état « %(current)s ».",
                        intervention=intervention.display_name,
                        current=labels.get(intervention.state, intervention.state),
                    )
                )

    def _apply_state(self, target):
        self.with_context(gest_agri_intervention_state_transition=True).write(
            {"state": target}
        )

    # ------------------------------------------------------------------
    # Boutons de transition
    # ------------------------------------------------------------------
    def action_plan(self):
        """Brouillon → Planifiée."""
        self._check_allowed_states({"draft"})
        self._apply_state("planned")

    def action_done(self):
        """Planifiée → Réalisée (date réelle obligatoire)."""
        self._check_allowed_states({"planned"})
        for intervention in self:
            if not intervention.date_actual:
                raise UserError(
                    self.env._(
                        "Renseignez la date réelle avant de réaliser "
                        "l'intervention « %s ».",
                        intervention.display_name,
                    )
                )
        self._apply_state("done")

    def action_cancel(self):
        """Brouillon ou Planifiée → Annulée."""
        self._check_allowed_states({"draft", "planned"})
        self._apply_state("cancelled")
