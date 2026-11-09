# -*- coding: utf-8 -*-
from datetime import datetime

import pytz

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError


class AgricultureMaintenancePortal(http.Controller):
    """Portal access to agricultural equipment and maintenance requests."""

    MAINTENANCE_TYPES = {"corrective", "preventive"}

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
        # A portal user may only consult requests that they personally submitted.
        # Farm access alone is not sufficient: several portal users can share a farm.
        return [
            ("agriculture_farm_id", "in", self._farm_ids()),
            ("owner_user_id", "=", request.env.uid),
        ]

    def _get_equipment(self, equipment_id, active_only=False):
        domain = [("id", "=", equipment_id)] + self._equipment_domain()
        if active_only:
            domain.append(("active", "=", True))
        return request.env["maintenance.equipment"].sudo().search(domain, limit=1)

    def _request_form(self, values=None, error=None, default_equipment_id=None):
        values = dict(values or {})
        equipment = request.env["maintenance.equipment"].sudo().search(
            self._equipment_domain() + [("active", "=", True)],
            order="agriculture_farm_id, name",
            limit=500,
        )
        if default_equipment_id and not values.get("equipment_id"):
            try:
                requested_equipment_id = int(default_equipment_id)
            except (TypeError, ValueError):
                requested_equipment_id = 0
            allowed = equipment.filtered(lambda item: item.id == requested_equipment_id)
            values["equipment_id"] = str(allowed.id) if allowed else ""
        return request.render(
            "agriculture_manage_website.portal_maintenance_request_form",
            {
                "equipment_records": equipment,
                "values": values,
                "error": error,
            },
        )

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
        equipment = self._get_equipment(equipment_id)
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

    @http.route("/my/agriculture/maintenance/requests/new", type="http", auth="user", website=True)
    def request_new(self, equipment_id=None, **kwargs):
        return self._request_form(default_equipment_id=equipment_id)

    @http.route(
        "/my/agriculture/maintenance/requests/create",
        type="http", auth="user", website=True, methods=["POST"],
    )
    def request_create(self, **kwargs):
        data = request.httprequest.form
        values = {
            "equipment_id": (data.get("equipment_id") or "").strip(),
            "name": (data.get("name") or "").strip(),
            "maintenance_type": (data.get("maintenance_type") or "corrective").strip(),
            "schedule_date": (data.get("schedule_date") or "").strip(),
            "description": (data.get("description") or "").strip(),
        }
        try:
            try:
                equipment_id = int(values["equipment_id"])
            except (TypeError, ValueError):
                raise ValueError("Veuillez sélectionner un équipement valide.")

            equipment = self._get_equipment(equipment_id, active_only=True)
            if not equipment:
                raise ValueError("L'équipement sélectionné est inexistant ou ne dépend pas d'une exploitation autorisée.")
            if not values["name"]:
                raise ValueError("L'objet de la demande est obligatoire.")
            if values["maintenance_type"] not in self.MAINTENANCE_TYPES:
                raise ValueError("Le type de maintenance sélectionné est invalide.")

            schedule_date = False
            if values["schedule_date"]:
                try:
                    local_datetime = datetime.strptime(values["schedule_date"], "%Y-%m-%dT%H:%M")
                    user_timezone = pytz.timezone(request.env.user.tz or "UTC")
                    schedule_date = user_timezone.localize(
                        local_datetime, is_dst=None
                    ).astimezone(pytz.UTC).replace(tzinfo=None)
                except (ValueError, pytz.AmbiguousTimeError, pytz.NonExistentTimeError):
                    raise ValueError("La date et l'heure souhaitées sont invalides.")

            company = equipment.company_id or equipment.agriculture_farm_id.company_id
            team = equipment.maintenance_team_id
            if not team:
                team = request.env["maintenance.team"].sudo().search(
                    [("company_id", "=", company.id), ("active", "=", True)],
                    limit=1,
                )
            if not team:
                team = request.env["maintenance.team"].sudo().search(
                    [("company_id", "=", False), ("active", "=", True)],
                    limit=1,
                )
            if not team:
                raise ValueError(
                    "Aucune équipe de maintenance n'est configurée pour la société de cet équipement."
                )

            create_values = {
                "name": values["name"][:200],
                "equipment_id": equipment.id,
                "maintenance_type": values["maintenance_type"],
                "description": values["description"],
                "company_id": company.id,
                "maintenance_team_id": team.id,
                "owner_user_id": request.env.uid,
            }
            if schedule_date:
                create_values["schedule_date"] = schedule_date

            maintenance_request = request.env["maintenance.request"].sudo().create(create_values)
            return request.redirect(
                "/my/agriculture/maintenance/requests/%s?created=1" % maintenance_request.id
            )
        except (ValueError, ValidationError, AccessError, UserError) as error:
            return self._request_form(values=values, error=str(error))

    @http.route(
        "/my/agriculture/maintenance/requests/<int:request_id>",
        type="http", auth="user", website=True,
    )
    def request_detail(self, request_id, **kwargs):
        maintenance_request = request.env["maintenance.request"].sudo().search(
            [("id", "=", request_id)] + self._request_domain(), limit=1
        )
        if not maintenance_request:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.portal_maintenance_request_detail",
            {
                "maintenance_request": maintenance_request,
                "created": kwargs.get("created") == "1",
            },
        )
