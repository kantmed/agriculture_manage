from odoo import api, fields, models, _


def _sum_harvest_quantity(harvests):
    """Return a comparable quantity and its UoM; never add incompatible units."""
    harvests = harvests.filtered(lambda h: h.state == "done")
    if not harvests:
        return 0.0, False
    if any(not harvest.uom_id for harvest in harvests):
        if all(not harvest.uom_id for harvest in harvests):
            return sum(h.quantity for h in harvests), False
        return 0.0, False
    first_uom = harvests[0].uom_id
    if any(not h.uom_id._has_common_reference(first_uom) for h in harvests):
        return 0.0, False
    total = 0.0
    for harvest in harvests:
        total += harvest.uom_id._compute_quantity(harvest.quantity, first_uom)
    return total, first_uom


class AgricultureFarmOperationLine(models.Model):
    _inherit = "agriculture.farm.operation.line"

    analysis_currency_id = fields.Many2one(
        "res.currency", related="operation_id.company_id.currency_id", readonly=True
    )
    analysis_cost = fields.Monetary(
        string="Coût réel retenu",
        currency_field="analysis_currency_id",
        compute="_compute_analysis_cost",
        store=True,
        help="Pour une ligne consommant du stock, utilise en priorité les couches de valorisation natives Odoo (`stock.valuation.layer`) après validation du mouvement. Sinon, utilise le coût saisi sur la ligne.",
    )

    @api.depends("cost", "consume_stock", "stock_valuation_value", "stock_cost_updated")
    def _compute_analysis_cost(self):
        for line in self:
            amount = line.stock_valuation_value if line.consume_stock and line.stock_cost_updated else (line.cost or 0.0)
            currency = line.operation_id.company_id.currency_id
            line.analysis_cost = currency.round(amount) if currency else amount


class AgricultureFarmHarvest(models.Model):
    _inherit = "agriculture.farm.harvest"

    analysis_currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )
    sale_unit_price = fields.Monetary(
        string="Prix de vente unitaire",
        currency_field="analysis_currency_id",
        help="Prix réellement obtenu ou prix estimé par unité de récolte. La recette est calculée à partir de ce prix et de la quantité.",
    )
    sale_total = fields.Monetary(
        string="Recette de la récolte",
        currency_field="analysis_currency_id",
        compute="_compute_sale_total",
        store=True,
    )

    @api.depends("quantity", "sale_unit_price", "analysis_currency_id")
    def _compute_sale_total(self):
        for harvest in self:
            amount = (harvest.quantity or 0.0) * (harvest.sale_unit_price or 0.0)
            currency = harvest.analysis_currency_id
            harvest.sale_total = currency.round(amount) if currency else amount


class AgricultureFarmCropCampaign(models.Model):
    _inherit = "agriculture.farm.crop.campaign"

    analysis_currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True
    )
    analysis_area_ha = fields.Float(
        string="Surface totale (ha)", compute="_compute_analysis_totals", store=True
    )
    analysis_operation_cost = fields.Monetary(
        string="Coût des travaux",
        currency_field="analysis_currency_id",
        compute="_compute_analysis_totals",
        store=True,
    )
    analysis_harvest_quantity = fields.Float(
        string="Quantité récoltée",
        compute="_compute_analysis_totals",
        store=True,
        help="Somme affichée uniquement lorsque les unités des récoltes sont compatibles.",
    )
    analysis_harvest_uom_id = fields.Many2one(
        "uom.uom", string="Unité récoltée", compute="_compute_analysis_totals", store=True
    )
    analysis_revenue = fields.Monetary(
        string="Recettes des récoltes",
        currency_field="analysis_currency_id",
        compute="_compute_analysis_totals",
        store=True,
    )
    analysis_gross_margin = fields.Monetary(
        string="Marge brute",
        currency_field="analysis_currency_id",
        compute="_compute_analysis_totals",
        store=True,
    )
    analysis_cost_per_ha = fields.Monetary(
        string="Coût par hectare",
        currency_field="analysis_currency_id",
        compute="_compute_analysis_totals",
        store=True,
    )
    analysis_margin_per_ha = fields.Monetary(
        string="Marge par hectare",
        currency_field="analysis_currency_id",
        compute="_compute_analysis_totals",
        store=True,
    )
    analysis_cost_per_unit = fields.Monetary(
        string="Coût par unité récoltée",
        currency_field="analysis_currency_id",
        compute="_compute_analysis_totals",
        store=True,
    )

    @api.depends(
        "campaign_plot_ids.area_ha",
        "operation_ids.state",
        "operation_ids.line_ids.analysis_cost",
        "harvest_ids.state",
        "harvest_ids.quantity",
        "harvest_ids.uom_id",
        "harvest_ids.sale_total",
    )
    def _compute_analysis_totals(self):
        for campaign in self:
            plots = campaign.campaign_plot_ids
            area = sum(plots.mapped("area_ha"))
            operations = campaign.operation_ids.filtered(lambda op: op.state == "done")
            cost = sum(operations.mapped("line_ids.analysis_cost"))
            harvests = campaign.harvest_ids.filtered(lambda h: h.state == "done")
            revenue = sum(harvests.mapped("sale_total"))
            quantity, uom = _sum_harvest_quantity(harvests)
            margin = revenue - cost
            currency = campaign.analysis_currency_id
            if currency:
                cost = currency.round(cost)
                revenue = currency.round(revenue)
                margin = currency.round(margin)
            campaign.analysis_area_ha = area
            campaign.analysis_operation_cost = cost
            campaign.analysis_harvest_quantity = quantity
            campaign.analysis_harvest_uom_id = uom
            campaign.analysis_revenue = revenue
            campaign.analysis_gross_margin = margin
            campaign.analysis_cost_per_ha = currency.round(cost / area) if currency and area else (cost / area if area else 0.0)
            campaign.analysis_margin_per_ha = currency.round(margin / area) if currency and area else (margin / area if area else 0.0)
            campaign.analysis_cost_per_unit = (
                currency.round(cost / quantity) if currency and quantity else (cost / quantity if quantity else 0.0)
            )


class AgricultureFarmCropCampaignPlot(models.Model):
    _inherit = "agriculture.farm.crop.campaign.plot"

    analysis_currency_id = fields.Many2one(
        "res.currency", related="campaign_id.company_id.currency_id", readonly=True
    )
    analysis_operation_cost = fields.Monetary(
        string="Coût des travaux",
        currency_field="analysis_currency_id",
        compute="_compute_plot_analysis",
        store=True,
    )
    analysis_harvest_quantity = fields.Float(
        string="Quantité récoltée", compute="_compute_plot_analysis", store=True
    )
    analysis_harvest_uom_id = fields.Many2one(
        "uom.uom", string="Unité récoltée", compute="_compute_plot_analysis", store=True
    )
    analysis_revenue = fields.Monetary(
        string="Recettes",
        currency_field="analysis_currency_id",
        compute="_compute_plot_analysis",
        store=True,
    )
    analysis_gross_margin = fields.Monetary(
        string="Marge brute",
        currency_field="analysis_currency_id",
        compute="_compute_plot_analysis",
        store=True,
    )
    analysis_cost_per_ha = fields.Monetary(
        string="Coût par hectare",
        currency_field="analysis_currency_id",
        compute="_compute_plot_analysis",
        store=True,
    )
    analysis_margin_per_ha = fields.Monetary(
        string="Marge par hectare",
        currency_field="analysis_currency_id",
        compute="_compute_plot_analysis",
        store=True,
    )

    @api.depends(
        "area_ha",
        "campaign_id.operation_ids.state",
        "campaign_id.operation_ids.plot_id",
        "campaign_id.operation_ids.line_ids.analysis_cost",
        "campaign_id.harvest_ids.state",
        "campaign_id.harvest_ids.plot_id",
        "campaign_id.harvest_ids.quantity",
        "campaign_id.harvest_ids.uom_id",
        "campaign_id.harvest_ids.sale_total",
        "plot_id",
    )
    def _compute_plot_analysis(self):
        for campaign_plot in self:
            campaign = campaign_plot.campaign_id
            operations = campaign.operation_ids.filtered(
                lambda op: op.state == "done" and op.plot_id == campaign_plot.plot_id
            )
            cost = sum(operations.mapped("line_ids.analysis_cost"))
            harvests = campaign.harvest_ids.filtered(
                lambda h: h.state == "done" and h.plot_id == campaign_plot.plot_id
            )
            revenue = sum(harvests.mapped("sale_total"))
            quantity, uom = _sum_harvest_quantity(harvests)
            margin = revenue - cost
            currency = campaign_plot.analysis_currency_id
            if currency:
                cost = currency.round(cost)
                revenue = currency.round(revenue)
                margin = currency.round(margin)
            area = campaign_plot.area_ha
            campaign_plot.analysis_operation_cost = cost
            campaign_plot.analysis_harvest_quantity = quantity
            campaign_plot.analysis_harvest_uom_id = uom
            campaign_plot.analysis_revenue = revenue
            campaign_plot.analysis_gross_margin = margin
            campaign_plot.analysis_cost_per_ha = currency.round(cost / area) if currency and area else (cost / area if area else 0.0)
            campaign_plot.analysis_margin_per_ha = currency.round(margin / area) if currency and area else (margin / area if area else 0.0)
