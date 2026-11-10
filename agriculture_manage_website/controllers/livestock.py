# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class AgricultureLivestockPortal(http.Controller):

    @http.route("/my/agriculture/livestock", type="http", auth="user", website=True)
    def livestock_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("code", "ilike", search)]
        animals = request.env["agriculture.livestock.animal"].sudo().search(domain, order="name", limit=100)
        return request.render(
            "agriculture_manage_website.livestock_list",
            {"animals": animals, "search": search},
        )

    @http.route("/my/agriculture/livestock/<int:animal_id>", type="http", auth="user", website=True)
    def livestock_detail(self, animal_id, **kwargs):
        animal = request.env["agriculture.livestock.animal"].sudo().search([("id", "=", animal_id)], limit=1)
        if not animal:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.livestock_detail",
            {"animal": animal},
        )