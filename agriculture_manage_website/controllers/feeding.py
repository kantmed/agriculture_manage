# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureFeedingPortal(http.Controller):

    @http.route("/my/agriculture/feeding", type="http", auth="user", website=True)
    def feeding_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search)]
        rations = request.env["agriculture.livestock.ration"].sudo().search(domain, order="name", limit=100)
        return request.render(
            "agriculture_manage_website.feeding_list",
            {"rations": rations, "search": search},
        )

    @http.route("/my/agriculture/feeding/new", type="http", auth="user", website=True)
    def feeding_new(self, **kwargs):
        farms = request.env["agriculture.farm"].sudo().search([])
        species = request.env["agriculture.livestock.species"].sudo().search([])
        return request.render(
            "agriculture_manage_website.feeding_form",
            {"ration": None, "values": {}, "farms": farms, "species": species},
        )

    @http.route("/my/agriculture/feeding/create", type="http", auth="user", website=True, methods=["POST"])
    def feeding_create(self, **kwargs):
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "farm_id": int(data.get("farm_id") or 0) or False,
                "species_id": int(data.get("species_id") or 0) or False,
                "purpose": data.get("purpose") or "other",
                "notes": (data.get("notes") or "").strip(),
            }
            if not vals["name"] or not vals["farm_id"] or not vals["species_id"]:
                raise ValueError("Nom, exploitation et espèce obligatoires.")
            ration = request.env["agriculture.livestock.ration"].sudo().create(vals)
            return request.redirect("/my/agriculture/feeding/%s" % ration.id)
        except (ValueError, AccessError, UserError) as error:
            farms = request.env["agriculture.farm"].sudo().search([])
            species = request.env["agriculture.livestock.species"].sudo().search([])
            return request.render(
                "agriculture_manage_website.feeding_form",
                {"ration": None, "values": data, "farms": farms, "species": species, "error": str(error)},
            )

    @http.route("/my/agriculture/feeding/<int:ration_id>", type="http", auth="user", website=True)
    def feeding_detail(self, ration_id, **kwargs):
        ration = request.env["agriculture.livestock.ration"].sudo().search([("id", "=", ration_id)], limit=1)
        if not ration:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.feeding_detail",
            {"ration": ration},
        )

    @http.route("/my/agriculture/feeding/<int:ration_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def feeding_delete(self, ration_id, **kwargs):
        ration = request.env["agriculture.livestock.ration"].sudo().search([("id", "=", ration_id)], limit=1)
        if not ration:
            return request.not_found()
        try:
            ration.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/feeding/%s" % ration_id)
        return request.redirect("/my/agriculture/feeding")