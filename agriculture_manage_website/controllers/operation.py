# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class AgricultureOperationPortal(http.Controller):

    @http.route("/my/agriculture/operations", type="http", auth="user", website=True)
    def operation_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("operation_type", "ilike", search)]
        operations = request.env["agriculture.farm.operation"].sudo().search(domain, order="date desc, name", limit=100)
        return request.render(
            "agriculture_manage_website.operation_list",
            {"operations": operations, "search": search},
        )

    @http.route("/my/agriculture/operations/<int:operation_id>", type="http", auth="user", website=True)
    def operation_detail(self, operation_id, **kwargs):
        operation = request.env["agriculture.farm.operation"].sudo().search([("id", "=", operation_id)], limit=1)
        if not operation:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.operation_detail",
            {"operation": operation},
        )