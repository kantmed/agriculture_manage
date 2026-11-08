from odoo import http
from odoo.http import request


class AgriculturePortal(http.Controller):

    @http.route(
        ['/my/agriculture'],
        type='http',
        auth='user',
        website=True
    )
    def agriculture_dashboard(self, **kwargs):
        return request.render(
            'agriculture_manage_website.portal_dashboard',
            {}
        )
