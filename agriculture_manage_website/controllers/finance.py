# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class AgricultureFinancePortal(http.Controller):

    @http.route("/my/agriculture/finance", type="http", auth="user", website=True)
    def finance_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("code", "ilike", search)]
        accounts = request.env["agriculture.farm.financial.account"].sudo().search(domain, order="name", limit=100)
        return request.render(
            "agriculture_manage_website.finance_list",
            {"accounts": accounts, "search": search},
        )

    @http.route("/my/agriculture/finance/<int:account_id>", type="http", auth="user", website=True)
    def finance_detail(self, account_id, **kwargs):
        account = request.env["agriculture.farm.financial.account"].sudo().search([("id", "=", account_id)], limit=1)
        if not account:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.finance_detail",
            {"account": account},
        )