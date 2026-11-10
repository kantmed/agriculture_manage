# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


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

    @http.route("/my/agriculture/budgets/new", type="http", auth="user", website=True)
    def budget_new(self, **kwargs):
        campaigns = request.env["agriculture.farm.crop.campaign"].sudo().search([])
        return request.render(
            "agriculture_manage_website.budget_form",
            {"budget": None, "values": {}, "campaigns": campaigns},
        )

    @http.route("/my/agriculture/budgets/create", type="http", auth="user", website=True, methods=["POST"])
    def budget_create(self, **kwargs):
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "campaign_id": int(data.get("campaign_id") or 0) or False,
                "date_start": data.get("date_start") or False,
                "date_end": data.get("date_end") or False,
            }
            if not vals["name"] or not vals["campaign_id"]:
                raise ValueError("Nom et campagne obligatoires.")
            budget = request.env["agriculture.farm.crop.budget"].sudo().create(vals)
            return request.redirect("/my/agriculture/budgets/%s" % budget.id)
        except (ValueError, AccessError, UserError) as error:
            campaigns = request.env["agriculture.farm.crop.campaign"].sudo().search([])
            return request.render(
                "agriculture_manage_website.budget_form",
                {"budget": None, "values": data, "campaigns": campaigns, "error": str(error)},
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

    @http.route("/my/agriculture/budgets/<int:budget_id>/edit", type="http", auth="user", website=True)
    def budget_edit(self, budget_id, **kwargs):
        budget = request.env["agriculture.farm.crop.budget"].sudo().search([("id", "=", budget_id)], limit=1)
        if not budget:
            return request.not_found()
        campaigns = request.env["agriculture.farm.crop.campaign"].sudo().search([])
        return request.render(
            "agriculture_manage_website.budget_form",
            {"budget": budget, "values": {}, "campaigns": campaigns},
        )

    @http.route("/my/agriculture/budgets/<int:budget_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def budget_update(self, budget_id, **kwargs):
        budget = request.env["agriculture.farm.crop.budget"].sudo().search([("id", "=", budget_id)], limit=1)
        if not budget:
            return request.not_found()
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "campaign_id": int(data.get("campaign_id") or 0) or False,
                "date_start": data.get("date_start") or False,
                "date_end": data.get("date_end") or False,
            }
            if not vals["name"] or not vals["campaign_id"]:
                raise ValueError("Nom et campagne obligatoires.")
            budget.write(vals)
            return request.redirect("/my/agriculture/budgets/%s" % budget.id)
        except (ValueError, AccessError, UserError) as error:
            campaigns = request.env["agriculture.farm.crop.campaign"].sudo().search([])
            return request.render(
                "agriculture_manage_website.budget_form",
                {"budget": budget, "values": data, "campaigns": campaigns, "error": str(error)},
            )

    @http.route("/my/agriculture/budgets/<int:budget_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def budget_delete(self, budget_id, **kwargs):
        budget = request.env["agriculture.farm.crop.budget"].sudo().search([("id", "=", budget_id)], limit=1)
        if not budget:
            return request.not_found()
        try:
            budget.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/budgets/%s" % budget_id)
        return request.redirect("/my/agriculture/budgets")