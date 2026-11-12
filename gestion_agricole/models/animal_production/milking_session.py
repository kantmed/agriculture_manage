# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriMilkingSession(models.Model):
    """Session de traite.

    Une session regroupe une ou plusieurs lignes détaillant les quantités par
    animal ou par lot. Le total collecté est la somme des lignes : une session
    collective n'impose jamais de quantité individuelle.
    """

    _name = "gest_agri.milking.session"
    _description = "Session de traite"
    _inherit = ["mail.thread"]
    _order = "start_datetime desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", check_company=True, index=True)

    start_datetime = fields.Datetime(string="Début", required=True, default=fields.Datetime.now, index=True)
    end_datetime = fields.Datetime(string="Fin")
    milking_period = fields.Selection(
        selection=[
            ("morning", "Matin"), ("noon", "Midi"), ("evening", "Soir"),
            ("other", "Autre période"),
        ],
        string="Période de traite", required=True, default="morning",
    )
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    notes = fields.Text(string="Observations")

    line_ids = fields.One2many("gest_agri.milking.session.line", "session_id", string="Lignes de traite")
    total_quantity = fields.Float(string="Quantité totale collectée", compute="_compute_totals", store=True, digits=(16, 3))
    animal_count = fields.Integer(string="Nombre d'animaux traits", compute="_compute_totals", store=True)

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("done", "Terminée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.milking.session")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.milking.session » est introuvable."))
                vals["name"] = ref
        return super().create(vals_list)

    @api.depends("line_ids.quantity", "line_ids.animal_id", "line_ids.animal_count")
    def _compute_totals(self):
        for session in self:
            session.total_quantity = sum(session.line_ids.mapped("quantity"))
            session.animal_count = sum(
                1 if line.animal_id else line.animal_count for line in session.line_ids
            )

    @api.constrains("start_datetime", "end_datetime")
    def _check_dates(self):
        for rec in self:
            if rec.end_datetime and rec.start_datetime and rec.end_datetime < rec.start_datetime:
                raise ValidationError(self.env._("La fin de la session ne peut pas précéder son début."))

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_milking_session_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_milking_session_state_transition=True).write({"state": target})

    def action_done(self):
        self._check_allowed({"draft"})
        for rec in self:
            if not rec.line_ids:
                raise UserError(self.env._("Une session de traite doit comporter au moins une ligne."))
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "done"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "done": "Terminée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : la session « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La session de traite « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()


class GestAgriMilkingSessionLine(models.Model):
    _name = "gest_agri.milking.session.line"
    _description = "Ligne de traite"
    _order = "sequence, id"

    session_id = fields.Many2one("gest_agri.milking.session", string="Session", required=True, ondelete="cascade", index=True)
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", related="session_id.farm_id",
        store=True, readonly=True, index=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Société", related="session_id.company_id",
        store=True, readonly=True, index=True,
    )
    animal_id = fields.Many2one("gest_agri.animal", string="Animal", ondelete="restrict", index=True)
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot", ondelete="restrict", index=True)
    quantity = fields.Float(string="Quantité", required=True, digits=(16, 3))
    uom_id = fields.Many2one("uom.uom", string="Unité", ondelete="restrict")
    animal_count = fields.Integer(string="Nombre d'animaux (lot)", default=0)
    sequence = fields.Integer(string="Séquence", default=10)

    @api.constrains("animal_id", "lot_id")
    def _check_target(self):
        for line in self:
            if bool(line.animal_id) == bool(line.lot_id):
                raise ValidationError(self.env._("Une ligne de traite doit concerner soit un animal, soit un lot."))

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(self.env._("La quantité doit être strictement positive."))

    @api.constrains("animal_count")
    def _check_animal_count(self):
        for line in self:
            if line.animal_count < 0:
                raise ValidationError(self.env._("Le nombre d'animaux ne peut pas être négatif."))

    @api.constrains("animal_id", "lot_id", "session_id")
    def _check_farm(self):
        for line in self:
            if not line.session_id.farm_id:
                continue
            if line.animal_id and line.animal_id.farm_id != line.session_id.farm_id:
                raise ValidationError(self.env._("L'animal de la ligne n'appartient pas à l'exploitation de la session."))
            if line.lot_id and line.lot_id.farm_id != line.session_id.farm_id:
                raise ValidationError(self.env._("Le lot de la ligne n'appartient pas à l'exploitation de la session."))
