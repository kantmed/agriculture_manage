# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class AgricultureHarvestPortal(http.Controller):

    @http.route("/my/agriculture/harvests", type="http", auth="user", website=True)
    def harvest_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("campaign_id.name", "ilike", search)]
        harvests = request.env["agriculture.farm.harvest"].sudo().search(domain, order="harvest_date desc, name", limit=100)
        return request.render(
            "agriculture_manage_website.harvest_list",
            {"harvests": harvests, "search": search},
        )

    @http.route("/my/agriculture/harvests/<int:harvest_id>", type="http", auth="user", website=True)
    def harvest_detail(self, harvest_id, **kwargs):
        harvest = request.env["agriculture.farm.harvest"].sudo().search([("id", "=", harvest_id)], limit=1)
        if not harvest:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.harvest_detail",
            {"harvest": harvest},
        )