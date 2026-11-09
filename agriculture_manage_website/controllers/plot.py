# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgriculturePlotPortal(http.Controller):

    def _farm_domain(self):
        user = request.env.user
        partner = user.partner_id.commercial_partner_id
        return [
            ("company_id", "in", user.company_ids.ids),
            "|",
            ("partner_id", "child_of", partner.id),
            ("manager_id", "=", user.id),
        ]

    def _plot_domain(self):
        return [("farm_id", "in", request.env["agriculture.farm"].sudo().search(
            self._farm_domain()
        ).ids)]

    def _get_plot(self, plot_id):
        return request.env["agriculture.farm.plot"].sudo().search(
            [("id", "=", plot_id)] + self._plot_domain(), limit=1
        )

    def _form_options(self, values=None, plot=None, error=None):
        values = values or {}
        farms = request.env["agriculture.farm"].sudo().search(
            self._farm_domain(), order="name"
        )
        selected_farm_id = values.get("farm_id") or (plot.farm_id.id if plot else False)
        try:
            selected_farm_id = int(selected_farm_id) if selected_farm_id else False
        except (TypeError, ValueError):
            selected_farm_id = False
        sites = request.env["agriculture.farm.site"].sudo().search(
            [("farm_id", "=", selected_farm_id)] if selected_farm_id else [("id", "=", 0)],
            order="name",
        )
        return request.render(
            "agriculture_manage_website.plot_form",
            {"plot": plot, "values": values, "farms": farms, "sites": sites, "error": error},
        )

    def _read_values(self):
        data = request.httprequest.form
        try:
            area = float(data.get("area") or 0)
            farm_id = int(data.get("farm_id") or 0)
            site_id = int(data.get("site_id") or 0)
        except (ValueError, TypeError):
            raise ValueError("Valeur numérique invalide.")
        if area <= 0:
            raise ValueError("La superficie doit être supérieure à zéro.")
        if not farm_id:
            raise ValueError("L'exploitation est obligatoire.")
        farm = request.env["agriculture.farm"].sudo().search(
            [("id", "=", farm_id)] + self._farm_domain(), limit=1
        )
        if not farm:
            raise ValueError("Exploitation non autorisée ou inexistante.")
        site = False
        if site_id:
            site = request.env["agriculture.farm.site"].sudo().search(
                [("id", "=", site_id), ("farm_id", "=", farm.id)], limit=1
            )
            if not site:
                raise ValueError("Le site sélectionné n'appartient pas à cette exploitation.")
        area_unit = data.get("area_unit") or "ha"
        if area_unit not in ("ha", "are", "m2"):
            raise ValueError("Unité de superficie invalide.")
        state = data.get("state") or "available"
        if state not in ("available", "cultivated", "fallow", "inactive"):
            raise ValueError("État de parcelle invalide.")
        return {
            "name": (data.get("name") or "").strip(),
            "farm_id": farm.id,
            "site_id": site.id if site else False,
            "area": area,
            "area_unit": area_unit,
            "state": state,
        }

    @http.route("/my/agriculture/plots", type="http", auth="user", website=True)
    def plot_list(self, search="", **kwargs):
        domain = self._plot_domain()
        if search:
            domain += ["|", ("name", "ilike", search), ("farm_id.name", "ilike", search)]
        plots = request.env["agriculture.farm.plot"].sudo().search(domain, order="name")
        return request.render(
            "agriculture_manage_website.plot_list",
            {"plots": plots, "search": search},
        )

    @http.route("/my/agriculture/plots/new", type="http", auth="user", website=True)
    def plot_new(self, **kwargs):
        return self._form_options()

    @http.route("/my/agriculture/plots/create", type="http", auth="user", website=True, methods=["POST"])
    def plot_create(self, **kwargs):
        try:
            values = self._read_values()
            if not values["name"]:
                return self._form_options(values, error="Le nom de la parcelle est obligatoire.")
            plot = request.env["agriculture.farm.plot"].sudo().create(values)
            return request.redirect("/my/agriculture/plots/%s" % plot.id)
        except ValueError as error:
            return self._form_options(error=str(error))
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/plots")

    @http.route("/my/agriculture/plots/<int:plot_id>", type="http", auth="user", website=True)
    def plot_detail(self, plot_id, **kwargs):
        plot = self._get_plot(plot_id)
        if not plot:
            return request.not_found()
        return request.render("agriculture_manage_website.plot_detail", {"plot": plot})

    @http.route("/my/agriculture/plots/<int:plot_id>/edit", type="http", auth="user", website=True)
    def plot_edit(self, plot_id, **kwargs):
        plot = self._get_plot(plot_id)
        if not plot:
            return request.not_found()
        return self._form_options(plot=plot)

    @http.route("/my/agriculture/plots/<int:plot_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def plot_update(self, plot_id, **kwargs):
        plot = self._get_plot(plot_id)
        if not plot:
            return request.not_found()
        try:
            values = self._read_values()
            if not values["name"]:
                return self._form_options(values, plot=plot, error="Le nom de la parcelle est obligatoire.")
            plot.write(values)
            return request.redirect("/my/agriculture/plots/%s" % plot.id)
        except ValueError as error:
            return self._form_options(plot=plot, error=str(error))
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/plots/%s" % plot.id)

    @http.route("/my/agriculture/plots/<int:plot_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def plot_delete(self, plot_id, **kwargs):
        plot = self._get_plot(plot_id)
        if not plot:
            return request.not_found()
        try:
            plot.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/plots/%s" % plot_id)
        return request.redirect("/my/agriculture/plots")
