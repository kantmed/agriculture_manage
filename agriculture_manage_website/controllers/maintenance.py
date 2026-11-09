# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class AgricultureMaintenancePortal(http.Controller):
    """Read-only portal access to agricultural equipment and maintenance."""

    def _farm_domain(self):
        user = request.env.user
        partner = user.partner_id.commercial_partner_id
        return [
            ("company_id", "in", user.company_ids.ids),
            "|",
            ("partner_id", "child_of", partner.id),
            ("manager_id", "=", user.id),
        ]

    def _farm_ids(self):
        return request.env["agriculture.farm"].sudo().search(self._farm_domain()).ids

    def _equipment_domain(self):
        return [("agriculture_farm_id", "in", self._farm_ids())]

    def _request_domain(self):
        return [("agriculture_farm_id", "in", self._farm_ids())]

    @http.route("/my/agriculture/maintenance/equipment", type="http", auth="user", website=True)
    def equipment_list(self, search="", **kwargs):
        domain = self._equipment_domain()
        if search:
            domain += ["|", ("name", "ilike", search), ("serial_no", "ilike", search)]
        equipment = request.env["maintenance.equipment"].sudo().search(
            domain, order="agriculture_farm_id, name", limit=100
        )
        return request.render(
            "agriculture_manage_website.portal_maintenance_equipment",
            {"equipment_records": equipment, "search": search},
        )

    @http.route("/my/agriculture/maintenance/equipment/<int:equipment_id>", type="http", auth="user", website=True)
    def equipment_detail(self, equipment_id, **kwargs):
        equipment = request.env["maintenance.equipment"].sudo().search(
            [("id", "=", equipment_id)] + self._equipment_domain(), limit=1
        )
        if not equipment:
            return request.not_found()
        requests = request.env["maintenance.request"].sudo().search(
            [("equipment_id", "=", equipment.id)] + self._request_domain(),
            order="schedule_date desc, id desc",
            limit=100,
        )
        return request.render(
            "agriculture_manage_website.portal_maintenance_equipment_detail",
            {"equipment": equipment, "maintenance_requests": requests},
        )

    @http.route("/my/agriculture/maintenance/requests", type="http", auth="user", website=True)
    def request_list(self, search="", **kwargs):
        domain = self._request_domain()
        if search:
            domain += ["|", ("name", "ilike", search), ("equipment_id.name", "ilike", search)]
        maintenance_requests = request.env["maintenance.request"].sudo().search(
            domain, order="schedule_date desc, id desc", limit=100
        )
        return request.render(
            "agriculture_manage_website.portal_maintenance_requests",
            {"maintenance_requests": maintenance_requests, "search": search},
        )

    @http.route("/my/agriculture/maintenance/requests/<int:request_id>", type="http", auth="user", website=True)
    def request_detail(self, request_id, **kwargs):
        maintenance_request = request.env["maintenance.request"].sudo().search(
            [("id", "=", request_id)] + self._request_domain(), limit=1
        )
        if not maintenance_request:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.portal_maintenance_request_detail",
            {"maintenance_request": maintenance_request},
        )
