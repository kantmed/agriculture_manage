# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureActivityPortal(http.Controller):

    def _get_activity(self, activity_id):
        return request.env["agriculture.farm.activity.type"].sudo().search([("id", "=", activity_id)], limit=1)

    @http.route("/my/agriculture/activities", type="http", auth="user", website=True)
    def activity_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("code", "ilike", search)]
        activities = request.env["agriculture.farm.activity.type"].sudo().search(domain, order="sequence, name")
        return request.render(
            "agriculture_manage_website.activity_list",
            {"activities": activities, "search": search},
        )

    @http.route("/my/agriculture/activities/new", type="http", auth="user", website=True)
    def activity_new(self, **kwargs):
        return request.render("agriculture_manage_website.activity_form", {"activity": None, "values": {}})

    @http.route("/my/agriculture/activities/create", type="http", auth="user", website=True, methods=["POST"])
    def activity_create(self, **kwargs):
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "code": (data.get("code") or "").strip(),
                "sequence": int(data.get("sequence") or 10),
                "active": bool(data.get("active")),
                "description": (data.get("description") or "").strip(),
            }
            if not vals["name"] or not vals["code"]:
                raise ValueError("Nom et code obligatoires.")
            activity = request.env["agriculture.farm.activity.type"].sudo().create(vals)
            return request.redirect("/my/agriculture/activities/%s" % activity.id)
        except (ValueError, AccessError, UserError) as error:
            return request.render("agriculture_manage_website.activity_form", {"activity": None, "values": data, "error": str(error)})

    @http.route("/my/agriculture/activities/<int:activity_id>", type="http", auth="user", website=True)
    def activity_detail(self, activity_id, **kwargs):
        activity = self._get_activity(activity_id)
        if not activity:
            return request.not_found()
        return request.render("agriculture_manage_website.activity_detail", {"activity": activity})

    @http.route("/my/agriculture/activities/<int:activity_id>/edit", type="http", auth="user", website=True)
    def activity_edit(self, activity_id, **kwargs):
        activity = self._get_activity(activity_id)
        if not activity:
            return request.not_found()
        return request.render("agriculture_manage_website.activity_form", {"activity": activity, "values": {}})

    @http.route("/my/agriculture/activities/<int:activity_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def activity_update(self, activity_id, **kwargs):
        activity = self._get_activity(activity_id)
        if not activity:
            return request.not_found()
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "code": (data.get("code") or "").strip(),
                "sequence": int(data.get("sequence") or 10),
                "active": bool(data.get("active")),
                "description": (data.get("description") or "").strip(),
            }
            if not vals["name"] or not vals["code"]:
                raise ValueError("Nom et code obligatoires.")
            activity.write(vals)
            return request.redirect("/my/agriculture/activities/%s" % activity.id)
        except (ValueError, AccessError, UserError) as error:
            return request.render("agriculture_manage_website.activity_form", {"activity": activity, "values": data, "error": str(error)})

    @http.route("/my/agriculture/activities/<int:activity_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def activity_delete(self, activity_id, **kwargs):
        activity = self._get_activity(activity_id)
        if not activity:
            return request.not_found()
        try:
            activity.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/activities/%s" % activity_id)
        return request.redirect("/my/agriculture/activities")