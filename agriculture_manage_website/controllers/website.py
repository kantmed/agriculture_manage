from odoo import http
from odoo.http import request


class AgricultureWebsite(http.Controller):

    @http.route(
        ['/agriculture'],
        type='http',
        auth='public',
        website=True
    )
    def agriculture_home(self, **kwargs):
        dashboard = request.env[
            "agriculture.farm.dashboard"
        ].sudo().create({})
        return request.render(
            'agriculture_manage_website.website_home',
            {'dashboard': dashboard}
        )