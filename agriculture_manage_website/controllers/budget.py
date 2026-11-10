# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class AgricultureBudgetPortal(http.Controller):

    @http.route("/my/agriculture/budgets", type="http", auth="user", website=True)
    def budget_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("code", "ilike", search)]
        budgets = request.env["agriculture.farm.crop.budget"].sudo().search(domain, order="date_start desc, name", limit=100)
        return request.render(
            "agriculture_manage_website.budget_list",
            {"budgets": budgets, "search": search},
        )

    @http.route("/my/agriculture/budgets/<int:budget_id>", type="http", auth="user", website=True)
    def budget_detail(self, budget_id, **kwargs):
        budget = request.env["agriculture.farm.crop.budget"].sudo().search([("id", "=", budget_id)], limit=1)
        if not budget:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.budget_detail",
            {"budget": budget},
        )