# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, ValidationError


class AgricultureInfrastructurePortal(http.Controller):

    INFRASTRUCTURE_TYPES = {
        "warehouse", "greenhouse", "well", "reservoir", "pump_station",
        "livestock_building", "workshop", "office", "irrigation_network", "other",
    }
    CONDITIONS = {"excellent", "good", "average", "poor", "out_of_service"}

    def _farm_domain(self):
        user = request.env.user
        partner = user.partner_id.commercial_partner_id
        return [
            ("company_id", "in", user.company_ids.ids),
            "|",
            ("partner_id", "child_of", partner.id),
            ("manager_id", "=", user.id),
        ]

    def _infrastructure_domain(self):
        farms = request.env["agriculture.farm"].sudo().search(self._farm_domain())
        return [("farm_id", "in", farms.ids)]

    def _get_infrastructure(self, infrastructure_id):
        return request.env["agriculture.farm.infrastructure"].sudo().search(
            [("id", "=", infrastructure_id)] + self._infrastructure_domain(),
            limit=1,
        )

    def _form_options(self, values=None, infrastructure=None, error=None):
        values = values or {}
        farms = request.env["agriculture.farm"].sudo().search(
            self._farm_domain(), order="name"
        )
        selected_farm_id = values.get("farm_id")
        if not selected_farm_id and infrastructure:
            selected_farm_id = infrastructure.farm_id.id
        try:
            selected_farm_id = int(selected_farm_id or 0)
        except (TypeError, ValueError):
            selected_farm_id = 0
        farm_ids = farms.ids
        sites = request.env["agriculture.farm.site"].sudo().search(
            [("farm_id", "=", selected_farm_id), ("farm_id", "in", farm_ids), ("active", "=", True)],
            order="name",
        ) if selected_farm_id else request.env["agriculture.farm.site"].sudo().browse()
        return request.render(
            "agriculture_manage_website.infrastructure_form",
            {
                "infrastructure": infrastructure,
                "values": values,
                "farms": farms,
                "sites": sites,
                "error": error,
            },
        )

    def _read_values(self, infrastructure=None):
        data = request.httprequest.form
        try:
            farm_id = int(data.get("farm_id") or 0)
            site_id = int(data.get("site_id") or 0)
            area = float(data.get("area") or 0)
            capacity = float(data.get("capacity") or 0)
        except (TypeError, ValueError):
            raise ValueError("Les identifiants, la surface et la capacité doivent être valides.")

        if area < 0 or capacity < 0:
            raise ValueError("La surface et la capacité ne peuvent pas être négatives.")

        farm = request.env["agriculture.farm"].sudo().search(
            [("id", "=", farm_id)] + self._farm_domain(), limit=1
        )
        if not farm:
            raise ValueError("Exploitation non autorisée ou inexistante.")

        site = False
        if site_id:
            site = request.env["agriculture.farm.site"].sudo().search(
                [("id", "=", site_id), ("farm_id", "=", farm.id), ("active", "=", True)],
                limit=1,
            )
            if not site:
                raise ValueError("Le site sélectionné ne correspond pas à l'exploitation.")

        infrastructure_type = data.get("infrastructure_type") or "other"
        condition = data.get("condition") or "good"
        if infrastructure_type not in self.INFRASTRUCTURE_TYPES:
            raise ValueError("Type d'infrastructure invalide.")
        if condition not in self.CONDITIONS:
            raise ValueError("État de l'infrastructure invalide.")

        construction_date = (data.get("construction_date") or "").strip()
        if construction_date:
            try:
                datetime.strptime(construction_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("La date de construction est invalide.")

        values = {
            "name": (data.get("name") or "").strip(),
            "farm_id": farm.id,
            "site_id": site.id if site else False,
            "infrastructure_type": infrastructure_type,
            "construction_date": construction_date or False,
            "area": area,
            "capacity": capacity,
            "capacity_unit": (data.get("capacity_unit") or "").strip(),
            "condition": condition,
            "description": (data.get("description") or "").strip(),
        }
        if infrastructure:
            values["active"] = bool(data.get("active"))
        return values

    @http.route("/my/agriculture/infrastructures", type="http", auth="user", website=True)
    def infrastructure_list(self, search="", **kwargs):
        domain = self._infrastructure_domain()
        if search:
            domain += ["|", "|", "|", ("name", "ilike", search), ("code", "ilike", search), ("farm_id.name", "ilike", search), ("site_id.name", "ilike", search)]
        infrastructures = request.env["agriculture.farm.infrastructure"].sudo().search(
            domain, order="farm_id, name"
        )
        return request.render(
            "agriculture_manage_website.infrastructure_list",
            {"infrastructures": infrastructures, "search": search},
        )

    @http.route("/my/agriculture/infrastructures/new", type="http", auth="user", website=True)
    def infrastructure_new(self, **kwargs):
        return self._form_options()

    @http.route("/my/agriculture/infrastructures/create", type="http", auth="user", website=True, methods=["POST"])
    def infrastructure_create(self, **kwargs):
        try:
            values = self._read_values()
            if not values["name"]:
                return self._form_options(values, error="Le nom de l'infrastructure est obligatoire.")
            infrastructure = request.env["agriculture.farm.infrastructure"].sudo().create(values)
            return request.redirect("/my/agriculture/infrastructures/%s" % infrastructure.id)
        except (ValueError, ValidationError) as error:
            return self._form_options(error=str(error))
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/infrastructures")

    @http.route("/my/agriculture/infrastructures/<int:infrastructure_id>", type="http", auth="user", website=True)
    def infrastructure_detail(self, infrastructure_id, **kwargs):
        infrastructure = self._get_infrastructure(infrastructure_id)
        if not infrastructure:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.infrastructure_detail",
            {"infrastructure": infrastructure},
        )

    @http.route("/my/agriculture/infrastructures/<int:infrastructure_id>/edit", type="http", auth="user", website=True)
    def infrastructure_edit(self, infrastructure_id, **kwargs):
        infrastructure = self._get_infrastructure(infrastructure_id)
        if not infrastructure:
            return request.not_found()
        return self._form_options(infrastructure=infrastructure)

    @http.route("/my/agriculture/infrastructures/<int:infrastructure_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def infrastructure_update(self, infrastructure_id, **kwargs):
        infrastructure = self._get_infrastructure(infrastructure_id)
        if not infrastructure:
            return request.not_found()
        try:
            values = self._read_values(infrastructure=infrastructure)
            if not values["name"]:
                return self._form_options(values, infrastructure=infrastructure, error="Le nom de l'infrastructure est obligatoire.")
            infrastructure.write(values)
            return request.redirect("/my/agriculture/infrastructures/%s" % infrastructure.id)
        except (ValueError, ValidationError) as error:
            return self._form_options(infrastructure=infrastructure, error=str(error))
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/infrastructures/%s" % infrastructure.id)

    @http.route("/my/agriculture/infrastructures/<int:infrastructure_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def infrastructure_delete(self, infrastructure_id, **kwargs):
        infrastructure = self._get_infrastructure(infrastructure_id)
        if not infrastructure:
            return request.not_found()
        try:
            infrastructure.unlink()
        except (AccessError, UserError, ValidationError):
            return request.redirect("/my/agriculture/infrastructures/%s" % infrastructure_id)
        return request.redirect("/my/agriculture/infrastructures")
