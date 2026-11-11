# -*- coding: utf-8 -*-
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

# Libellés centralisés pour les messages et la vue.
STATE_SELECTION = [
    ("planned", "Prévue"),
    ("planted", "Implantée"),
    ("in_progress", "En cours"),
    ("done", "Terminée"),
    ("cancelled", "Annulée"),
]


class GestAgriCropCycle(models.Model):
    _name = "gest_agri.crop.cycle"
    _description = "Culture implantée"
    _inherit = ["mail.thread"]
    _order = "date_start desc, id desc"
    _check_company_auto = True

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        index=True,
        help="Référence unique attribuée automatiquement à la création.",
    )
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Relations principales
    # ------------------------------------------------------------------
    plot_id = fields.Many2one(
        "gest_agri.plot",
        string="Parcelle",
        required=True,
        ondelete="restrict",
        index=True,
    )
    farm_id = fields.Many2one(
        "gest_agri.farm",
        string="Exploitation",
        related="plot_id.farm_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    site_id = fields.Many2one(
        "gest_agri.site",
        string="Site",
        related="plot_id.site_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        related="plot_id.company_id",
        store=True,
        readonly=True,
        precompute=True,
        index=True,
    )
    crop_type_id = fields.Many2one(
        "gest_agri.crop.type",
        string="Type de culture",
        required=True,
        check_company=True,
        ondelete="restrict",
        index=True,
    )
    crop_variety_id = fields.Many2one(
        "gest_agri.crop.variety",
        string="Variété",
        check_company=True,
        ondelete="restrict",
        index=True,
        domain="[('crop_type_id', '=', crop_type_id)]",
        help="Variété facultative, obligatoirement rattachée au type de culture choisi.",
    )

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    date_start = fields.Date(
        string="Date de début",
        required=True,
        help="Date de semis ou de plantation.",
    )
    date_end_planned = fields.Date(
        string="Fin prévue",
        help="Date de fin prévue de la culture.",
    )
    date_end_actual = fields.Date(
        string="Fin réelle",
        help="Date de fin réelle. Obligatoire pour terminer la culture.",
    )

    # ------------------------------------------------------------------
    # Surface
    # ------------------------------------------------------------------
    area_ha = fields.Float(
        string="Surface cultivée (ha)",
        digits=(16, 2),
        default=0.0,
        help="Surface occupée par la culture. Initialisée avec la surface de la "
        "parcelle, puis modifiable si la culture n'occupe qu'une partie.",
    )

    # ------------------------------------------------------------------
    # État et suivi
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=STATE_SELECTION,
        string="État",
        default="planned",
        required=True,
        index=True,
        tracking=True,
        copy=False,
    )
    notes = fields.Text(string="Notes internes")

    # ------------------------------------------------------------------
    # Contraintes SQL
    # ------------------------------------------------------------------
    # Empêche deux cultures non annulées de démarrer le même jour sur la
    # même parcelle. Attention : cet index ne protège pas contre les
    # chevauchements dont les dates de début diffèrent. Voir la contrainte
    # Python _check_overlap et la limite de concurrence documentée.
    _plot_start_unique = models.UniqueIndex(
        "(plot_id, date_start) WHERE state <> 'cancelled'",
        "Deux cultures non annulées ne peuvent pas démarrer le même jour "
        "sur la même parcelle.",
    )

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                reference = self.env["ir.sequence"].next_by_code(
                    "gest_agri.crop.cycle"
                )
                if not reference:
                    raise UserError(
                        self.env._(
                            "La séquence « gest_agri.crop.cycle » est introuvable : "
                            "impossible d'attribuer une référence à la culture."
                        )
                    )
                vals["name"] = reference
            if "area_ha" not in vals:
                plot = self.env["gest_agri.plot"].browse(vals.get("plot_id"))
                if plot:
                    vals["area_ha"] = plot.area
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Aides
    # ------------------------------------------------------------------
    def _effective_end_date(self):
        """Fin effective d'une culture, utilisée pour les chevauchements."""
        self.ensure_one()
        return self.date_end_actual or self.date_end_planned or date.max

    @api.onchange("plot_id")
    def _onchange_plot_id(self):
        """Initialise la surface avec celle de la parcelle si elle est vide."""
        if self.plot_id and not self.area_ha:
            self.area_ha = self.plot_id.area

    @api.onchange("crop_type_id")
    def _onchange_crop_type_id(self):
        """Retire une variété devenue incompatible avec le nouveau type."""
        if self.crop_variety_id and self.crop_variety_id.crop_type_id != self.crop_type_id:
            self.crop_variety_id = False

    # ------------------------------------------------------------------
    # Contraintes applicatives
    # ------------------------------------------------------------------
    @api.constrains("crop_type_id", "crop_variety_id")
    def _check_variety_type(self):
        for cycle in self:
            if (
                cycle.crop_variety_id
                and cycle.crop_variety_id.crop_type_id != cycle.crop_type_id
            ):
                raise ValidationError(
                    self.env._(
                        "La variété « %(variety)s » n'appartient pas au type de "
                        "culture « %(crop)s ».",
                        variety=cycle.crop_variety_id.display_name,
                        crop=cycle.crop_type_id.display_name,
                    )
                )

    @api.constrains("date_start", "date_end_planned", "date_end_actual")
    def _check_dates(self):
        for cycle in self:
            if cycle.date_end_planned and cycle.date_end_planned < cycle.date_start:
                raise ValidationError(
                    self.env._(
                        "La fin prévue ne peut pas être antérieure à la date de "
                        "début de la culture."
                    )
                )
            if cycle.date_end_actual and cycle.date_end_actual < cycle.date_start:
                raise ValidationError(
                    self.env._(
                        "La fin réelle ne peut pas être antérieure à la date de "
                        "début de la culture."
                    )
                )

    @api.constrains("state", "date_end_actual")
    def _check_done_requires_end_date(self):
        for cycle in self:
            if cycle.state == "done" and not cycle.date_end_actual:
                raise ValidationError(
                    self.env._(
                        "La date de fin réelle est obligatoire pour terminer la "
                        "culture « %s ».",
                        cycle.display_name,
                    )
                )

    @api.constrains("area_ha", "plot_id")
    def _check_area(self):
        for cycle in self:
            if cycle.area_ha <= 0:
                raise ValidationError(
                    self.env._(
                        "La surface cultivée doit être strictement positive."
                    )
                )
            if cycle.plot_id and cycle.area_ha > cycle.plot_id.area:
                raise ValidationError(
                    self.env._(
                        "La surface cultivée (%(area)s ha) ne peut pas dépasser "
                        "la surface de la parcelle « %(plot)s » (%(plot_area)s ha).",
                        area=cycle.area_ha,
                        plot=cycle.plot_id.display_name,
                        plot_area=cycle.plot_id.area,
                    )
                )

    @api.constrains(
        "plot_id",
        "date_start",
        "date_end_planned",
        "date_end_actual",
        "state",
        "active",
    )
    def _check_overlap(self):
        """Interdit le chevauchement de deux cultures non annulées.

        Les intervalles sont inclusifs. Les cultures archivées participent au
        contrôle ; seules les cultures annulées en sont exclues. Limite :
        une simple vérification applicative ne garantit pas l'absence de
        chevauchement en cas de transactions concurrentes.
        """
        for cycle in self:
            if cycle.state == "cancelled" or not cycle.plot_id or not cycle.date_start:
                continue
            start = cycle.date_start
            end = cycle._effective_end_date()
            domain = [
                ("id", "!=", cycle.id),
                ("plot_id", "=", cycle.plot_id.id),
                ("state", "!=", "cancelled"),
                ("date_start", "<=", end),
            ]
            others = (
                self.env["gest_agri.crop.cycle"]
                .sudo()
                .with_context(active_test=False)
                .search(domain)
            )
            for other in others:
                if start <= other._effective_end_date():
                    raise ValidationError(
                        self.env._(
                            "La parcelle « %(plot)s » est déjà occupée par la "
                            "culture « %(other)s » sur la période "
                            "%(other_start)s – %(other_end)s. Les intervalles "
                            "sont inclusifs : une nouvelle culture ne peut "
                            "commencer qu'après la fin effective de la précédente.",
                            plot=cycle.plot_id.display_name,
                            other=other.display_name,
                            other_start=other.date_start,
                            other_end=other._effective_end_date(),
                        )
                    )

    # ------------------------------------------------------------------
    # Protection des transitions d'état
    # ------------------------------------------------------------------
    def write(self, vals):
        """Empêche la modification directe de l'état hors des boutons prévus."""
        if "state" in vals and not self.env.context.get(
            "gest_agri_state_transition"
        ):
            for cycle in self:
                if cycle.state != vals["state"]:
                    raise AccessError(
                        self.env._(
                            "L'état d'une culture ne peut être modifié que par "
                            "les boutons de transition prévus."
                        )
                    )
        return super().write(vals)

    def _check_allowed_states(self, allowed):
        labels = dict(STATE_SELECTION)
        for cycle in self:
            if cycle.state not in allowed:
                raise UserError(
                    self.env._(
                        "Transition impossible : la culture « %(cycle)s » est "
                        "à l'état « %(current)s ».",
                        cycle=cycle.display_name,
                        current=labels.get(cycle.state, cycle.state),
                    )
                )

    def _apply_state(self, target):
        self.with_context(gest_agri_state_transition=True).write({"state": target})

    # ------------------------------------------------------------------
    # Boutons de transition
    # ------------------------------------------------------------------
    def action_plant(self):
        """Prévue → Implantée."""
        self._check_allowed_states({"planned"})
        self._apply_state("planted")

    def action_start(self):
        """Implantée → En cours."""
        self._check_allowed_states({"planted"})
        self._apply_state("in_progress")

    def action_done(self):
        """En cours → Terminée (date de fin réelle obligatoire)."""
        self._check_allowed_states({"in_progress"})
        for cycle in self:
            if not cycle.date_end_actual:
                raise UserError(
                    self.env._(
                        "Renseignez la date de fin réelle avant de terminer la "
                        "culture « %s ».",
                        cycle.display_name,
                    )
                )
        self._apply_state("done")

    def action_cancel(self):
        """Prévue, implantée ou en cours → Annulée."""
        self._check_allowed_states({"planned", "planted", "in_progress"})
        self._apply_state("cancelled")

    def action_reset(self):
        """Annulée → Prévue, réservé aux responsables et administrateurs."""
        if not (
            self.env.user.has_group("gestion_agricole.group_gest_agri_manager")
            or self.env.user.has_group("gestion_agricole.group_gest_agri_admin")
        ):
            raise AccessError(
                self.env._(
                    "Seul un responsable ou un administrateur agricole peut "
                    "réactiver une culture annulée."
                )
            )
        self._check_allowed_states({"cancelled"})
        self._apply_state("planned")
