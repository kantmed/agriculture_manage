from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    agriculture_campaign_id = fields.Many2one(
        "agriculture.farm.crop.campaign", string="Campagne agricole",
        index=True, copy=False, ondelete="restrict",
        domain="[('company_id', '=', company_id)]",
    )
    agriculture_harvest_id = fields.Many2one(
        "agriculture.farm.harvest", string="Récolte liée",
        index=True, copy=False, ondelete="restrict",
        domain="[('campaign_id', '=', agriculture_campaign_id), ('state', '=', 'done')]",
    )
    agriculture_plot_id = fields.Many2one(
        "agriculture.farm.plot", string="Parcelle",
        index=True, copy=False, ondelete="restrict",
    )
    agriculture_farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation", compute="_compute_agriculture_farm",
        store=True, readonly=True,
    )
    agriculture_invoice_count = fields.Integer(compute="_compute_agriculture_invoice_count")

    @api.depends("agriculture_campaign_id", "agriculture_campaign_id.farm_id")
    def _compute_agriculture_farm(self):
        for order in self:
            order.agriculture_farm_id = order.agriculture_campaign_id.farm_id

    @api.depends("invoice_ids", "invoice_ids.state")
    def _compute_agriculture_invoice_count(self):
        for order in self:
            order.agriculture_invoice_count = len(order.invoice_ids.filtered(lambda move: move.move_type == "out_invoice"))

    @api.onchange("agriculture_campaign_id")
    def _onchange_agriculture_campaign_id(self):
        for order in self:
            if order.agriculture_campaign_id:
                if order.agriculture_campaign_id.company_id:
                    order.company_id = order.agriculture_campaign_id.company_id
                if order.agriculture_harvest_id.campaign_id != order.agriculture_campaign_id:
                    order.agriculture_harvest_id = False
                if order.agriculture_plot_id and order.agriculture_plot_id not in order.agriculture_campaign_id.campaign_plot_ids.plot_id:
                    order.agriculture_plot_id = False

    @api.constrains("agriculture_campaign_id", "agriculture_harvest_id", "agriculture_plot_id", "company_id")
    def _check_agriculture_links(self):
        for order in self:
            campaign = order.agriculture_campaign_id
            if campaign and campaign.company_id and campaign.company_id != order.company_id:
                raise ValidationError(_("La campagne agricole doit appartenir à la société de la commande."))
            if order.agriculture_harvest_id:
                if not campaign or order.agriculture_harvest_id.campaign_id != campaign:
                    raise ValidationError(_("La récolte doit appartenir à la campagne sélectionnée."))
                if order.agriculture_harvest_id.state != "done":
                    raise ValidationError(_("Seules les récoltes validées peuvent être vendues."))
            if order.agriculture_plot_id and campaign:
                if order.agriculture_plot_id not in campaign.campaign_plot_ids.plot_id:
                    raise ValidationError(_("La parcelle doit faire partie de la campagne sélectionnée."))

    def _create_invoices(self, grouped=False, final=False, date=None):
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        for invoice in invoices:
            source_orders = invoice.invoice_line_ids.sale_line_ids.order_id
            campaigns = source_orders.mapped("agriculture_campaign_id")
            farms = source_orders.mapped("agriculture_farm_id")
            plots = source_orders.mapped("agriculture_plot_id")
            harvests = source_orders.mapped("agriculture_harvest_id")
            # A grouped invoice may contain several agricultural dimensions.
            # Store move-level dimensions only when each dimension is unambiguous.
            single_source_order = len(source_orders) == 1
            invoice.write({
                "agriculture_farm_id": farms.id if single_source_order and len(farms) == 1 else False,
                "agriculture_campaign_id": campaigns.id if single_source_order and len(campaigns) == 1 else False,
                "agriculture_plot_id": plots.id if single_source_order and len(plots) == 1 else False,
                "agriculture_harvest_id": harvests.id if single_source_order and len(harvests) == 1 else False,
            })
            # Preserve per-order analytic attribution even when Odoo groups several orders.
            for line in invoice.invoice_line_ids.filtered(lambda item: item.display_type == "product" and not item.analytic_distribution):
                line_orders = line.sale_line_ids.order_id
                if len(line_orders) != 1:
                    continue
                order = line_orders[0]
                accounts = self.env["account.analytic.account"]
                for account in (
                    order.agriculture_farm_id.analytic_account_id,
                    order.agriculture_campaign_id.analytic_account_id,
                    order.agriculture_plot_id.analytic_account_id,
                ):
                    if account and (not account.company_id or account.company_id == invoice.company_id):
                        accounts |= account
                if accounts:
                    line.analytic_distribution = {
                        ",".join(map(str, sorted(accounts.ids))): 100.0
                    }
        return invoices

    def action_view_agriculture_invoices(self):
        self.ensure_one()
        invoices = self.invoice_ids.filtered(lambda move: move.move_type == "out_invoice")
        return {
            "type": "ir.actions.act_window",
            "name": _("Factures clients agricoles"),
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", invoices.ids)],
            "context": {"default_move_type": "out_invoice"},
        }

    def action_create_agriculture_financial_income(self):
        self.ensure_one()
        if self.state not in ("sale", "done"):
            raise UserError(_("Confirmez d'abord la commande client."))
        invoices = self.invoice_ids.filtered(lambda move: move.move_type == "out_invoice")
        if not invoices:
            invoices = self._create_invoices()
        invoices.write({
            "agriculture_farm_id": self.agriculture_farm_id.id,
            "agriculture_campaign_id": self.agriculture_campaign_id.id,
            "agriculture_plot_id": self.agriculture_plot_id.id,
            "agriculture_harvest_id": self.agriculture_harvest_id.id,
        })
        return self.action_view_agriculture_invoices()


class AgricultureFarmHarvest(models.Model):
    _inherit = "agriculture.farm.harvest"

    sale_order_ids = fields.One2many(
        "sale.order", "agriculture_harvest_id", string="Commandes clients",
    )
    sale_order_count = fields.Integer(compute="_compute_sale_order_count")

    @api.depends("sale_order_ids")
    def _compute_sale_order_count(self):
        for harvest in self:
            harvest.sale_order_count = len(harvest.sale_order_ids)

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Ventes de cette récolte"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("agriculture_harvest_id", "=", self.id)],
            "context": {"default_agriculture_harvest_id": self.id,
                        "default_agriculture_campaign_id": self.campaign_id.id},
        }
