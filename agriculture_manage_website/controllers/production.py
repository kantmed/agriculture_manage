# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureProductionPortal(http.Controller):

    @http.route("/my/agriculture/productions", type="http", auth="user", website=True)
    def production_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search)]
        records = request.env["agriculture.livestock.production"].sudo().search(domain, order="date desc, id desc", limit=100)
        return request.render(
            "agriculture_manage_website.production_list",
            {"records": records, "search": search},
        )

    @http.route("/my/agriculture/productions/new", type="http", auth="user", website=True)
    def production_new(self, **kwargs):
        animals = request.env["agriculture.livestock.animal"].sudo().search([])
        herds = request.env["agriculture.livestock.herd"].sudo().search([])
        return request.render(
            "agriculture_manage_website.production_form",
            {"record": None, "values": {}, "animals": animals, "herds": herds},
        )

    @http.route("/my/agriculture/productions/create", type="http", auth="user", website=True, methods=["POST"])
    def production_create(self, **kwargs):
        data = request.httprequest.form
        try:
            vals = {
                "production_type": data.get("production_type") or "milk",
                "animal_id": int(data.get("animal_id") or 0) or False,
                "herd_id": int(data.get("herd_id") or 0) or False,
                "date": data.get("date") or False,
                "quantity": float(data.get("quantity") or 0),
                "uom_id": int(data.get("uom_id") or 0) or False,
                "quality": data.get("quality") or "standard",
                "product_description": (data.get("product_description") or "").strip(),
                "notes": (data.get("notes") or "").strip(),
            }
            if not vals["animal_id"] and not vals["herd_id"]:
                raise ValueError("Animal ou lot obligatoire.")
            if vals["quantity"] <= 0:
                raise ValueError("Quantité obligatoire.")
            rec = request.env["agriculture.livestock.production"].sudo().create(vals)
            return request.redirect("/my/agriculture/productions/%s" % rec.id)
        except (ValueError, AccessError, UserError) as error:
            animals = request.env["agriculture.livestock.animal"].sudo().search([])
            herds = request.env["agriculture.livestock.herd"].sudo().search([])
            return request.render(
                "agriculture_manage_website.production_form",
                {"record": None, "values": data, "animals": animals, "herds": herds, "error": str(error)},
            )

    @http.route("/my/agriculture/productions/<int:record_id>", type="http", auth="user", website=True)
    def production_detail(self, record_id, **kwargs):
        rec = request.env["agriculture.livestock.production"].sudo().search([("id", "=", record_id)], limit=1)
        if not rec:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.production_detail",
            {"record": rec},
        )

    @http.route("/my/agriculture/productions/<int:record_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def production_delete(self, record_id, **kwargs):
        rec = request.env["agriculture.livestock.production"].sudo().search([("id", "=", record_id)], limit=1)
        if not rec:
            return request.not_found()
        try:
            rec.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/productions/%s" % record_id)
        return request.redirect("/my/agriculture/productions")