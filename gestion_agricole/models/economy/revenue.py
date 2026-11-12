# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class GestAgriEconomicRevenue(models.Model):
    _name = "gest_agri.economic.revenue"
    _description = "Recette agricole"
    _inherit = ["mail.thread"]
    _order = "revenue_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)
    description = fields.Text(string="Description")

    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", check_company=True, index=True)
    plot_id = fields.Many2one("gest_agri.plot", string="Parcelle", ondelete="set null", index=True)
    campaign_id = fields.Many2one("gest_agri.crop.campaign", string="Campagne", ondelete="set null", index=True)
    cycle_id = fields.Many2one("gest_agri.crop.cycle", string="Cycle cultural", ondelete="set null", index=True)
    harvest_id = fields.Many2one("gest_agri.crop.harvest", string="Récolte associée", ondelete="set null", index=True)

    category_id = fields.Many2one(
        "gest_agri.economic.category", string="Catégorie de recette", required=True,
        ondelete="restrict", check_company=True, index=True,
        domain="[('nature', '=', 'revenue')]",
    )

    revenue_date = fields.Date(string="Date de recette", required=True, index=True)
    amount = fields.Float(string="Montant", digits=(16, 2), required=True, default=0.0)
    currency_id = fields.Many2one("res.currency", string="Devise", default=lambda self: self.env.company.currency_id)
    quantity = fields.Float(string="Quantité", digits=(16, 3), default=0.0)
    uom_id = fields.Many2one("uom.uom", string="Unité de mesure", ondelete="set null")
    unit_price = fields.Float(string="Prix unitaire", digits=(16, 4), compute="_compute_unit_price", store=True)

    partner_id = fields.Many2one("res.partner", string="Client", ondelete="set null", index=True)
    reference = fields.Char(string="Référence du document")
    notes = fields.Text(string="Observations")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.economic.revenue")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.economic.revenue » est introuvable."))
                vals["name"] = ref
            self._check_coherence(vals)
        return super().create(vals_list)

    @api.model
    def _check_coherence(self, vals):
        if vals.get("category_id"):
            cat = self.env["gest_agri.economic.category"].browse(vals["category_id"])
            if cat.nature != "revenue":
                raise ValidationError(self.env._("La catégorie doit être de nature 'recette'."))
        farm_id = vals.get("farm_id")
        for field, model in [("plot_id", "gest_agri.plot"), ("campaign_id", "gest_agri.crop.campaign"),
                             ("cycle_id", "gest_agri.crop.cycle"), ("harvest_id", "gest_agri.crop.harvest")]:
            if vals.get(field) and farm_id:
                rec = self.env[model].browse(vals[field])
                if hasattr(rec, "farm_id") and rec.farm_id.id != farm_id:
                    raise ValidationError(self.env._("Incohérence d'exploitation."))

    @api.depends("amount", "quantity")
    def _compute_unit_price(self):
        for rev in self:
            if rev.quantity:
                rev.unit_price = rev.amount / rev.quantity
            else:
                rev.unit_price = 0.0

    @api.constrains("amount")
    def _check_amount(self):
        for rev in self:
            if rev.amount < 0:
                raise ValidationError(self.env._("Le montant ne peut pas être négatif."))

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rev in self:
            if rev.site_id and rev.site_id.farm_id != rev.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    @api.constrains("farm_id", "plot_id")
    def _check_plot_farm(self):
        for rev in self:
            if rev.plot_id and rev.plot_id.farm_id != rev.farm_id:
                raise ValidationError(self.env._("La parcelle n'appartient pas à l'exploitation."))
