# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureCropPortal(http.Controller):

    @http.route("/my/agriculture/crops", type="http", auth="user", website=True)
    def crop_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("code", "ilike", search)]
        crops = request.env["agriculture.farm.crop"].sudo().search(domain, order="name", limit=100)
        return request.render(
            "agriculture_manage_website.crop_list",
            {"crops": crops, "search": search},
        )

    @http.route("/my/agriculture/crops/new", type="http", auth="user", website=True)
    def crop_new(self, **kwargs):
        crop_types = request.env["agriculture.farm.crop.type"].sudo().search([])
        return request.render(
            "agriculture_manage_website.crop_form",
            {"crop": None, "values": {}, "crop_types": crop_types},
        )

    @http.route("/my/agriculture/crops/create", type="http", auth="user", website=True, methods=["POST"])
    def crop_create(self, **kwargs):
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "crop_type_id": int(data.get("crop_type_id") or 0) or False,
                "abbreviation": (data.get("abbreviation") or "").strip().upper(),
                "description": (data.get("description") or "").strip(),
            }
            if not vals["name"] or not vals["crop_type_id"]:
                raise ValueError("Nom et type de culture obligatoires.")
            if not vals["abbreviation"]:
                raise ValueError("Abréviation obligatoire.")
            crop = request.env["agriculture.farm.crop"].sudo().create(vals)
            return request.redirect("/my/agriculture/crops/%s" % crop.id)
        except (ValueError, AccessError, UserError) as error:
            crop_types = request.env["agriculture.farm.crop.type"].sudo().search([])
            return request.render(
                "agriculture_manage_website.crop_form",
                {"crop": None, "values": data, "crop_types": crop_types, "error": str(error)},
            )

    @http.route("/my/agriculture/crops/<int:crop_id>", type="http", auth="user", website=True)
    def crop_detail(self, crop_id, **kwargs):
        crop = request.env["agriculture.farm.crop"].sudo().search([("id", "=", crop_id)], limit=1)
        if not crop:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.crop_detail",
            {"crop": crop},
        )

    @http.route("/my/agriculture/crops/<int:crop_id>/edit", type="http", auth="user", website=True)
    def crop_edit(self, crop_id, **kwargs):
        crop = request.env["agriculture.farm.crop"].sudo().search([("id", "=", crop_id)], limit=1)
        if not crop:
            return request.not_found()
        crop_types = request.env["agriculture.farm.crop.type"].sudo().search([])
        return request.render(
            "agriculture_manage_website.crop_form",
            {"crop": crop, "values": {}, "crop_types": crop_types},
        )

    @http.route("/my/agriculture/crops/<int:crop_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def crop_update(self, crop_id, **kwargs):
        crop = request.env["agriculture.farm.crop"].sudo().search([("id", "=", crop_id)], limit=1)
        if not crop:
            return request.not_found()
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "crop_type_id": int(data.get("crop_type_id") or 0) or False,
                "abbreviation": (data.get("abbreviation") or "").strip().upper(),
                "description": (data.get("description") or "").strip(),
            }
            if not vals["name"] or not vals["crop_type_id"]:
                raise ValueError("Nom et type de culture obligatoires.")
            crop.write(vals)
            return request.redirect("/my/agriculture/crops/%s" % crop.id)
        except (ValueError, AccessError, UserError) as error:
            crop_types = request.env["agriculture.farm.crop.type"].sudo().search([])
            return request.render(
                "agriculture_manage_website.crop_form",
                {"crop": crop, "values": data, "crop_types": crop_types, "error": str(error)},
            )

    @http.route("/my/agriculture/crops/<int:crop_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def crop_delete(self, crop_id, **kwargs):
        crop = request.env["agriculture.farm.crop"].sudo().search([("id", "=", crop_id)], limit=1)
        if not crop:
            return request.not_found()
        try:
            crop.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/crops/%s" % crop_id)
        return request.redirect("/my/agriculture/crops")