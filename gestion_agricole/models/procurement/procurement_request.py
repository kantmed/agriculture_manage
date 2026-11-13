# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriProcurementRequest(models.Model):
    _name = "gest_agri.procurement.request"
    _description = "Demande d'approvisionnement agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"
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

    requester_id = fields.Many2one(
        "res.users", string="Demandeur", default=lambda self: self.env.user, ondelete="set null",
    )
    request_date = fields.Date(string="Date de demande", required=True, default=fields.Date.today, index=True)
    needed_date = fields.Date(string="Date de besoin", index=True)
    motive = fields.Text(string="Motif")
    priority = fields.Selection(
        selection=[("low", "Faible"), ("medium", "Moyenne"), ("high", "Élevée"), ("urgent", "Urgente")],
        string="Priorité", default="medium", index=True,
    )

    line_ids = fields.One2many(
        "gest_agri.procurement.request.line", "request_id", string="Lignes de demande",
    )

    state = fields.Selection(
        selection=[
            ("draft", "Brouillon"), ("submitted", "Soumise"), ("approved", "Approuvée"),
            ("ordered", "Commandée"), ("done", "Terminée"), ("cancelled", "Annulée"),
        ],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    purchase_order_ids = fields.Many2many(
        "purchase.order", string="Commandes fournisseurs",
    )
    purchase_order_count = fields.Integer(string="Nb commandes", compute="_compute_po_count", store=True)

    notes = fields.Text(string="Observations")

    @api.depends("purchase_order_ids")
    def _compute_po_count(self):
        for rec in self:
            rec.purchase_order_count = len(rec.purchase_order_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.procurement.request")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.procurement.request » est introuvable."))
                vals["name"] = ref
            farm = self.env["gest_agri.farm"].browse(vals.get("farm_id"))
            if farm:
                farm.check_access("write")
            if vals.get("site_id"):
                site = self.env["gest_agri.site"].browse(vals["site_id"])
                if site.farm_id != farm:
                    raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))
        return super().create(vals_list)

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    @api.constrains("request_date", "needed_date")
    def _check_dates(self):
        for rec in self:
            if rec.needed_date and rec.request_date and rec.needed_date < rec.request_date:
                raise ValidationError(self.env._("La date de besoin ne peut pas précéder la date de demande."))

    # ------------------------------------------------------------------
    # Write / workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if not self:
            return super().write(vals)
        if "line_ids" in vals:
            self.check_access("write")
        protected = {"farm_id", "site_id", "requester_id"}
        for rec in self:
            if rec.state not in ("draft",) and (protected & set(vals)):
                raise UserError(self.env._("La demande « %s » ne peut plus être modifiée.", rec.display_name))
        if "state" in vals and not self.env.context.get("gest_agri_procurement_request_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_procurement_request_state_transition=True).write({"state": target})

    def action_submit(self):
        self._check_allowed({"draft"})
        for rec in self:
            if not rec.line_ids:
                raise UserError(self.env._("La demande « %s » doit comporter au moins une ligne.", rec.display_name))
        self._apply_state("submitted")

    def action_approve(self):
        self._check_allowed({"submitted"})
        self._apply_state("approved")

    def action_order(self):
        self._check_allowed({"approved"})
        self._apply_state("ordered")

    def action_done(self):
        self._check_allowed({"ordered"})
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "submitted", "approved"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "submitted": "Soumise", "approved": "Approuvée",
                  "ordered": "Commandée", "done": "Terminée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : la demande « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La demande « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Commandes fournisseurs",
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.purchase_order_ids.ids)],
            "context": {"default_partner_id": False},
        }