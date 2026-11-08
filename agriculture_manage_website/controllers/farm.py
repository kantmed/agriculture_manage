# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureFarmPortal(http.Controller):

    def _farm_domain(self):
        user = request.env.user
        partner = user.partner_id.commercial_partner_id

        return [
            "&",
            ("company_id", "in", user.company_ids.ids),
            "|",
            ("partner_id", "child_of", partner.id),
            ("manager_id", "=", user.id),
        ]

    def _get_farm(self, farm_id):
        return request.env["agriculture.farm"].sudo().search(
            [("id", "=", farm_id)] + self._farm_domain(),
            limit=1,
        )

    def _form_options(self, values=None, farm=None, error=None):
        values = values or {}

        country_id = values.get("country_id")
        if country_id is None and farm:
            country_id = farm.country_id.id

        state_id = values.get("state_id")
        if state_id is None and farm:
            state_id = farm.state_id.id

        countries = request.env["res.country"].sudo().search([])
        states = request.env["res.country.state"].sudo().search(
            [("country_id", "=", int(country_id))]
            if country_id else []
        )

        return request.render(
            "agriculture_manage_website.farm_form",
            {
                "farm": farm,
                "values": values,
                "countries": countries,
                "states": states,
                "error": error,
            }
        )

    def _read_values(self):
        data = request.httprequest.form

        try:
            total_area = float(data.get("total_area") or 0)
            country_id = int(data.get("country_id") or 0)
            state_id = int(data.get("state_id") or 0)
        except (ValueError, TypeError):
            raise ValueError("Valeur numérique invalide.")

        if total_area < 0:
            raise ValueError("La superficie ne peut pas être négative.")

        return {
            "name": (data.get("name") or "").strip(),
            "code": (data.get("code") or "").strip(),
            "phone": (data.get("phone") or "").strip(),
            "email": (data.get("email") or "").strip(),
            "street": (data.get("street") or "").strip(),
            "city": (data.get("city") or "").strip(),
            "total_area": total_area,
            "country_id": country_id or False,
            "state_id": state_id or False,
        }

    @http.route(
        "/my/agriculture/farms",
        type="http", auth="user", website=True
    )
    def farm_list(self, search="", **kwargs):
        domain = self._farm_domain()

        if search:
            domain += [
                "|",
                ("name", "ilike", search),
                ("code", "ilike", search),
            ]

        farms = request.env["agriculture.farm"].sudo().search(
            domain, order="name"
        )

        return request.render(
            "agriculture_manage_website.farm_list",
            {"farms": farms, "search": search}
        )

    @http.route(
        "/my/agriculture/farms/new",
        type="http", auth="user", website=True
    )
    def farm_new(self, **kwargs):
        return self._form_options()

    @http.route(
        "/my/agriculture/farms/create",
        type="http", auth="user",
        website=True, methods=["POST"]
    )
    def farm_create(self, **kwargs):
        try:
            values = self._read_values()

            if not values["name"]:
                return self._form_options(
                    values, error="Le nom de l'exploitation est obligatoire."
                )

            if values["country_id"]:
                country = request.env["res.country"].sudo().browse(
                    values["country_id"]
                ).exists()
                if not country:
                    return self._form_options(
                        values, error="Pays invalide."
                    )

            if values["state_id"]:
                state = request.env["res.country.state"].sudo().browse(
                    values["state_id"]
                ).exists()
                if not state or (
                    values["country_id"]
                    and state.country_id.id != values["country_id"]
                ):
                    return self._form_options(
                        values, error="Wilaya invalide."
                    )

            values.update({
                "partner_id": request.env.user.partner_id.id,
                "company_id": request.env.company.id,
                "active": True,
            })

            if request.env.user.has_group("base.group_user"):
                values["manager_id"] = request.env.user.id

            farm = request.env["agriculture.farm"].sudo().create(values)

            return request.redirect(
                "/my/agriculture/farms/%s" % farm.id
            )

        except ValueError as error:
            return self._form_options(
                error=str(error)
            )
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/farms")

    @http.route(
        "/my/agriculture/farms/<int:farm_id>",
        type="http", auth="user", website=True
    )
    def farm_detail(self, farm_id, **kwargs):
        farm = self._get_farm(farm_id)

        if not farm:
            return request.not_found()

        return request.render(
            "agriculture_manage_website.farm_detail",
            {"farm": farm}
        )

    @http.route(
        "/my/agriculture/farms/<int:farm_id>/edit",
        type="http", auth="user", website=True
    )
    def farm_edit(self, farm_id, **kwargs):
        farm = self._get_farm(farm_id)

        if not farm:
            return request.not_found()

        return self._form_options(farm=farm)

    @http.route(
        "/my/agriculture/farms/<int:farm_id>/update",
        type="http", auth="user",
        website=True, methods=["POST"]
    )
    def farm_update(self, farm_id, **kwargs):
        farm = self._get_farm(farm_id)

        if not farm:
            return request.not_found()

        try:
            values = self._read_values()

            if not values["name"]:
                return self._form_options(
                    values, farm=farm,
                    error="Le nom de l'exploitation est obligatoire."
                )

            if values["country_id"]:
                country = request.env["res.country"].sudo().browse(
                    values["country_id"]
                ).exists()
                if not country:
                    return self._form_options(
                        values, farm=farm, error="Pays invalide."
                    )

            if values["state_id"]:
                state = request.env["res.country.state"].sudo().browse(
                    values["state_id"]
                ).exists()
                if not state or (
                    values["country_id"]
                    and state.country_id.id != values["country_id"]
                ):
                    return self._form_options(
                        values, farm=farm, error="Wilaya invalide."
                    )

            farm.write(values)

            return request.redirect(
                "/my/agriculture/farms/%s" % farm.id
            )

        except ValueError as error:
            return self._form_options(
                farm=farm, error=str(error)
            )
        except (AccessError, UserError):
            return request.redirect(
                "/my/agriculture/farms/%s" % farm.id
            )

    @http.route(
        "/my/agriculture/farms/<int:farm_id>/delete",
        type="http", auth="user",
        website=True, methods=["POST"]
    )
    def farm_delete(self, farm_id, **kwargs):
        farm = self._get_farm(farm_id)

        if not farm:
            return request.not_found()

        try:
            farm.unlink()
        except (AccessError, UserError):
            return request.redirect(
                "/my/agriculture/farms/%s" % farm.id
            )

        return request.redirect("/my/agriculture/farms")
