# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgriculturePlotPortal(http.Controller):

    def _plot_domain(self):
        user = request.env.user
        return [("farm_id.company_id", "in", user.company_ids.ids)]

    def _get_plot(self, plot_id):
        return request.env["agriculture.farm.plot"].sudo().search(
            [("id", "=", plot_id)] + self._plot_domain(), limit=1
        )

    def _form_options(self, values=None, plot=None, error=None):
        values = values or {}
        farms = request.env["agriculture.farm"].sudo().search(self._plot_domain() if False else [])
        # farms available to user
        farms = request.env["agriculture.farm"].sudo().search([])
        return request.render(
            "agriculture_manage_website.plot_form",
            {
                "plot": plot,
                "values": values,
                "farms": farms,
                "error": error,
            },
        )

    def _read_values(self):
        data = request.httprequest.form
        try:
            area = float(data.get("area") or 0)
            farm_id = int(data.get("farm_id") or 0)
        except (ValueError, TypeError):
            raise ValueError("Valeur numérique invalide.")
        if area < 0:
            raise ValueError("La superficie ne peut pas être négative.")
        return {
            "name": (data.get("name") or "").strip(),
            "farm_id": farm_id or False,
            "area": area,
            "area_unit": data.get("area_unit") or "ha",
            "state": data.get("state") or "available",
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
            if not values["farm_id"]:
                return self._form_options(values, error="L'exploitation est obligatoire.")
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
        return request.render(
            "agriculture_manage_website.plot_detail",
            {"plot": plot},
        )

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