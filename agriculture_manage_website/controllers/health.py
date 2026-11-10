# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureHealthPortal(http.Controller):

    @http.route("/my/agriculture/health", type="http", auth="user", website=True)
    def health_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("event_type", "ilike", search)]
        records = request.env["agriculture.livestock.health"].sudo().search(domain, order="date desc, id desc", limit=100)
        return request.render(
            "agriculture_manage_website.health_list",
            {"records": records, "search": search},
        )

    @http.route("/my/agriculture/health/new", type="http", auth="user", website=True)
    def health_new(self, **kwargs):
        animals = request.env["agriculture.livestock.animal"].sudo().search([])
        herds = request.env["agriculture.livestock.herd"].sudo().search([])
        return request.render(
            "agriculture_manage_website.health_form",
            {"record": None, "values": {}, "animals": animals, "herds": herds},
        )

    @http.route("/my/agriculture/health/create", type="http", auth="user", website=True, methods=["POST"])
    def health_create(self, **kwargs):
        data = request.httprequest.form
        try:
            vals = {
                "event_type": data.get("event_type") or "treatment",
                "animal_id": int(data.get("animal_id") or 0) or False,
                "herd_id": int(data.get("herd_id") or 0) or False,
                "date": data.get("date") or False,
                "veterinarian": (data.get("veterinarian") or "").strip(),
                "diagnosis": (data.get("diagnosis") or "").strip(),
                "treatment": (data.get("treatment") or "").strip(),
                "cost": float(data.get("cost") or 0),
                "notes": (data.get("notes") or "").strip(),
            }
            if not vals["animal_id"] and not vals["herd_id"]:
                raise ValueError("Animal ou lot obligatoire.")
            rec = request.env["agriculture.livestock.health"].sudo().create(vals)
            return request.redirect("/my/agriculture/health/%s" % rec.id)
        except (ValueError, AccessError, UserError) as error:
            animals = request.env["agriculture.livestock.animal"].sudo().search([])
            herds = request.env["agriculture.livestock.herd"].sudo().search([])
            return request.render(
                "agriculture_manage_website.health_form",
                {"record": None, "values": data, "animals": animals, "herds": herds, "error": str(error)},
            )

    @http.route("/my/agriculture/health/<int:record_id>", type="http", auth="user", website=True)
    def health_detail(self, record_id, **kwargs):
        rec = request.env["agriculture.livestock.health"].sudo().search([("id", "=", record_id)], limit=1)
        if not rec:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.health_detail",
            {"record": rec},
        )

    @http.route("/my/agriculture/health/<int:record_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def health_delete(self, record_id, **kwargs):
        rec = request.env["agriculture.livestock.health"].sudo().search([("id", "=", record_id)], limit=1)
        if not rec:
            return request.not_found()
        try:
            rec.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/health/%s" % record_id)
        return request.redirect("/my/agriculture/health")