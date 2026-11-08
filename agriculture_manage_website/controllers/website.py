from odoo import http
from odoo.http import request


class AgricultureWebsite(http.Controller):
    @http.route("/agriculture", type="http", auth="public", website=True)
    def website_agriculture(self, **kw):
        return request.render("agriculture_manage_website.website_agriculture")