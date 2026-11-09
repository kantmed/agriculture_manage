# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureSitePortal(http.Controller):

    def _farm_domain(self):
        user = request.env.user
        partner = user.partner_id.commercial_partner_id
        return [
            ("company_id", "in", user.company_ids.ids),
            "|",
            ("partner_id", "child_of", partner.id),
            ("manager_id", "=", user.id),
        ]

    def _site_domain(self):
        farms = request.env["agriculture.farm"].sudo().search(self._farm_domain())
        return [("farm_id", "in", farms.ids)]

    def _get_site(self, site_id):
        return request.env["agriculture.farm.site"].sudo().search(
            [("id", "=", site_id)] + self._site_domain(), limit=1
        )

    def _form_options(self, values=None, site=None, error=None):
        farms = request.env["agriculture.farm"].sudo().search(
            self._farm_domain(), order="name"
        )
        return request.render(
            "agriculture_manage_website.site_form",
            {"site": site, "values": values or {}, "farms": farms, "error": error},
        )

    def _read_values(self):
        data = request.httprequest.form
        try:
            farm_id = int(data.get("farm_id") or 0)
            latitude = float(data.get("latitude") or 0)
            longitude = float(data.get("longitude") or 0)
        except (ValueError, TypeError):
            raise ValueError("Les coordonnées GPS doivent être numériques.")
        farm = request.env["agriculture.farm"].sudo().search(
            [("id", "=", farm_id)] + self._farm_domain(), limit=1
        )
        if not farm:
            raise ValueError("Exploitation non autorisée ou inexistante.")
        site_type = data.get("site_type") or "production"
        allowed_types = {
            "production", "storage", "livestock", "greenhouse",
            "administration", "mixed", "other",
        }
        if site_type not in allowed_types:
            raise ValueError("Type de site invalide.")
        has_coordinates = bool(data.get("has_coordinates"))
        if has_coordinates and not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Latitude ou longitude hors limites.")
        return {
            "name": (data.get("name") or "").strip(),
            "farm_id": farm.id,
            "site_type": site_type,
            "address": (data.get("address") or "").strip(),
            "city": (data.get("city") or "").strip(),
            "notes": (data.get("notes") or "").strip(),
            "has_coordinates": has_coordinates,
            "latitude": latitude if has_coordinates else 0,
            "longitude": longitude if has_coordinates else 0,
            "active": bool(data.get("active")) if "active" in data else True,
        }

    @http.route("/my/agriculture/sites", type="http", auth="user", website=True)
    def site_list(self, search="", **kwargs):
        domain = self._site_domain()
        if search:
            domain += ["|", ("name", "ilike", search), ("farm_id.name", "ilike", search)]
        sites = request.env["agriculture.farm.site"].sudo().search(domain, order="farm_id, name")
        site_type_labels = {
            "production": "Production", "storage": "Stockage",
            "livestock": "Élevage", "greenhouse": "Serres",
            "administration": "Administration", "mixed": "Mixte",
            "other": "Autre",
        }
        return request.render(
            "agriculture_manage_website.site_list",
            {"sites": sites, "search": search, "site_type_labels": site_type_labels},
        )

    @http.route("/my/agriculture/sites/new", type="http", auth="user", website=True)
    def site_new(self, **kwargs):
        return self._form_options()

    @http.route("/my/agriculture/sites/create", type="http", auth="user", website=True, methods=["POST"])
    def site_create(self, **kwargs):
        try:
            values = self._read_values()
            if not values["name"]:
                return self._form_options(values, error="Le nom du site est obligatoire.")
            site = request.env["agriculture.farm.site"].sudo().create(values)
            return request.redirect("/my/agriculture/sites/%s" % site.id)
        except ValueError as error:
            return self._form_options(error=str(error))
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/sites")

    @http.route("/my/agriculture/sites/<int:site_id>", type="http", auth="user", website=True)
    def site_detail(self, site_id, **kwargs):
        site = self._get_site(site_id)
        if not site:
            return request.not_found()
        site_type_labels = {
            "production": "Production", "storage": "Stockage",
            "livestock": "Élevage", "greenhouse": "Serres",
            "administration": "Administration", "mixed": "Mixte",
            "other": "Autre",
        }
        return request.render(
            "agriculture_manage_website.site_detail",
            {"site": site, "site_type_labels": site_type_labels},
        )

    @http.route("/my/agriculture/sites/<int:site_id>/edit", type="http", auth="user", website=True)
    def site_edit(self, site_id, **kwargs):
        site = self._get_site(site_id)
        if not site:
            return request.not_found()
        return self._form_options(site=site)

    @http.route("/my/agriculture/sites/<int:site_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def site_update(self, site_id, **kwargs):
        site = self._get_site(site_id)
        if not site:
            return request.not_found()
        try:
            values = self._read_values()
            if not values["name"]:
                return self._form_options(values, site=site, error="Le nom du site est obligatoire.")
            site.write(values)
            return request.redirect("/my/agriculture/sites/%s" % site.id)
        except ValueError as error:
            return self._form_options(site=site, error=str(error))
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/sites/%s" % site.id)

    @http.route("/my/agriculture/sites/<int:site_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def site_delete(self, site_id, **kwargs):
        site = self._get_site(site_id)
        if not site:
            return request.not_found()
        try:
            site.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/sites/%s" % site_id)
        return request.redirect("/my/agriculture/sites")
