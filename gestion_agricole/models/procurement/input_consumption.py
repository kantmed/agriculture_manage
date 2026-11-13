# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriInputConsumption(models.Model):
    _name = "gest_agri.input.consumption"
    _description = "Consommation d'intrants agricoles"
    _inherit = ["mail.thread"]
    _order = "consumption_date desc, id desc"
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
    plot_id = fields.Many2one("gest_agri.plot", string="Parcelle", ondelete="set null", check_company=True, index=True)

    consumption_date = fields.Date(string="Date de consommation", required=True, default=fields.Date.today, index=True)
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    motive = fields.Text(string="Motif / Justification")

    line_ids = fields.One2many(
        "gest_agri.input.consumption.line", "consumption_id", string="Lignes de consommation",
    )

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    notes = fields.Text(string="Observations")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.input.consumption")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.input.consumption » est introuvable."))
                vals["name"] = ref
            farm = self.env["gest_agri.farm"].browse(vals.get("farm_id"))
            if farm:
                farm.check_access("write")
            if vals.get("site_id"):
                site = self.env["gest_agri.site"].browse(vals["site_id"])
                if site.farm_id != farm:
                    raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))
            if vals.get("plot_id"):
                plot = self.env["gest_agri.plot"].browse(vals["plot_id"])
                if plot.farm_id != farm:
                    raise ValidationError(self.env._("La parcelle n'appartient pas à l'exploitation."))
        return super().create(vals_list)

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    @api.constrains("farm_id", "plot_id")
    def _check_plot_farm(self):
        for rec in self:
            if rec.plot_id and rec.plot_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("La parcelle n'appartient pas à l'exploitation."))

    # ------------------------------------------------------------------
    # Write / workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if not self:
            return super().write(vals)
        if "line_ids" in vals:
            self.check_access("write")
        protected = {"farm_id", "site_id", "plot_id"}
        for rec in self:
            if rec.state in ("validated", "cancelled") and (protected & set(vals)):
                raise UserError(self.env._("La consommation « %s » est validée ou annulée.", rec.display_name))
        if "state" in vals and not self.env.context.get("gest_agri_input_consumption_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_input_consumption_state_transition=True).write({"state": target})

    def action_validate(self):
        self._check_allowed({"draft"})
        for rec in self:
            if not rec.line_ids:
                raise UserError(self.env._("La consommation « %s » doit comporter au moins une ligne.", rec.display_name))
        self._apply_state("validated")

    def action_cancel(self):
        self._check_allowed({"draft", "validated"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "validated": "Validée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : la consommation « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La consommation « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()