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

    @http.route(
        ['/my/agriculture/plots'],
        type='http',
        auth='user',
        website=True
    )
    def agriculture_plots(self, **kwargs):
        plots = request.env['agriculture.farm.plot'].search([])
        return request.render(
            'agriculture_manage_website.portal_plots',
            {'plots': plots}
        )

    @http.route(
        ['/my/agriculture/activities'],
        type='http',
        auth='user',
        website=True
    )
    def agriculture_activities(self, **kwargs):
        activities = request.env['agriculture.farm.activity.type'].search([])
        return request.render(
            'agriculture_manage_website.portal_activities',
            {'activities': activities}
        )