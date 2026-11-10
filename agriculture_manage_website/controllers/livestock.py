# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureLivestockPortal(http.Controller):

    @http.route("/my/agriculture/livestock", type="http", auth="user", website=True)
    def livestock_list(self, search="", **kwargs):
        domain = []
        if search:
            domain += ["|", ("name", "ilike", search), ("code", "ilike", search)]
        animals = request.env["agriculture.livestock.animal"].sudo().search(domain, order="name", limit=100)
        return request.render(
            "agriculture_manage_website.livestock_list",
            {"animals": animals, "search": search},
        )

    @http.route("/my/agriculture/livestock/new", type="http", auth="user", website=True)
    def livestock_new(self, **kwargs):
        farms = request.env["agriculture.farm"].sudo().search([])
        species = request.env["agriculture.livestock.species"].sudo().search([])
        return request.render(
            "agriculture_manage_website.livestock_form",
            {"animal": None, "values": {}, "farms": farms, "species": species},
        )

    @http.route("/my/agriculture/livestock/create", type="http", auth="user", website=True, methods=["POST"])
    def livestock_create(self, **kwargs):
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "farm_id": int(data.get("farm_id") or 0) or False,
                "species_id": int(data.get("species_id") or 0) or False,
                "sex": data.get("sex") or "unknown",
                "origin": data.get("origin") or "purchase",
                "birth_date": data.get("birth_date") or False,
                "entry_date": data.get("entry_date") or False,
                "notes": (data.get("notes") or "").strip(),
            }
            if not vals["name"] or not vals["farm_id"] or not vals["species_id"]:
                raise ValueError("Nom, exploitation et espèce obligatoires.")
            animal = request.env["agriculture.livestock.animal"].sudo().create(vals)
            return request.redirect("/my/agriculture/livestock/%s" % animal.id)
        except (ValueError, AccessError, UserError) as error:
            farms = request.env["agriculture.farm"].sudo().search([])
            species = request.env["agriculture.livestock.species"].sudo().search([])
            return request.render(
                "agriculture_manage_website.livestock_form",
                {"animal": None, "values": data, "farms": farms, "species": species, "error": str(error)},
            )

    @http.route("/my/agriculture/livestock/<int:animal_id>/edit", type="http", auth="user", website=True)
    def livestock_edit(self, animal_id, **kwargs):
        animal = request.env["agriculture.livestock.animal"].sudo().search([("id", "=", animal_id)], limit=1)
        if not animal:
            return request.not_found()
        farms = request.env["agriculture.farm"].sudo().search([])
        species = request.env["agriculture.livestock.species"].sudo().search([])
        return request.render(
            "agriculture_manage_website.livestock_form",
            {"animal": animal, "values": {}, "farms": farms, "species": species},
        )

    @http.route("/my/agriculture/livestock/<int:animal_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def livestock_update(self, animal_id, **kwargs):
        animal = request.env["agriculture.livestock.animal"].sudo().search([("id", "=", animal_id)], limit=1)
        if not animal:
            return request.not_found()
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "farm_id": int(data.get("farm_id") or 0) or False,
                "species_id": int(data.get("species_id") or 0) or False,
                "sex": data.get("sex") or "unknown",
                "origin": data.get("origin") or "purchase",
                "birth_date": data.get("birth_date") or False,
                "entry_date": data.get("entry_date") or False,
                "notes": (data.get("notes") or "").strip(),
            }
            if not vals["name"] or not vals["farm_id"] or not vals["species_id"]:
                raise ValueError("Nom, exploitation et espèce obligatoires.")
            animal.write(vals)
            return request.redirect("/my/agriculture/livestock/%s" % animal.id)
        except (ValueError, AccessError, UserError) as error:
            farms = request.env["agriculture.farm"].sudo().search([])
            species = request.env["agriculture.livestock.species"].sudo().search([])
            return request.render(
                "agriculture_manage_website.livestock_form",
                {"animal": animal, "values": data, "farms": farms, "species": species, "error": str(error)},
            )

    @http.route("/my/agriculture/livestock/<int:animal_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def livestock_delete(self, animal_id, **kwargs):
        animal = request.env["agriculture.livestock.animal"].sudo().search([("id", "=", animal_id)], limit=1)
        if not animal:
            return request.not_found()
        try:
            animal.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/livestock/%s" % animal_id)
        return request.redirect("/my/agriculture/livestock")

    @http.route("/my/agriculture/livestock/<int:animal_id>", type="http", auth="user", website=True)
    def livestock_detail(self, animal_id, **kwargs):
        animal = request.env["agriculture.livestock.animal"].sudo().search([("id", "=", animal_id)], limit=1)
        if not animal:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.livestock_detail",
            {"animal": animal},
        )

    @http.route("/my/agriculture/livestock/<int:animal_id>/edit", type="http", auth="user", website=True)
    def livestock_edit(self, animal_id, **kwargs):
        animal = request.env["agriculture.livestock.animal"].sudo().search([("id", "=", animal_id)], limit=1)
        if not animal:
            return request.not_found()
        farms = request.env["agriculture.farm"].sudo().search([])
        species = request.env["agriculture.livestock.species"].sudo().search([])
        return request.render(
            "agriculture_manage_website.livestock_form",
            {"animal": animal, "values": {}, "farms": farms, "species": species},
        )

    @http.route("/my/agriculture/livestock/<int:animal_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def livestock_update(self, animal_id, **kwargs):
        animal = request.env["agriculture.livestock.animal"].sudo().search([("id", "=", animal_id)], limit=1)
        if not animal:
            return request.not_found()
        data = request.httprequest.form
        try:
            vals = {
                "name": (data.get("name") or "").strip(),
                "farm_id": int(data.get("farm_id") or 0) or False,
                "species_id": int(data.get("species_id") or 0) or False,
                "sex": data.get("sex") or "unknown",
                "origin": data.get("origin") or "purchase",
                "birth_date": data.get("birth_date") or False,
                "entry_date": data.get("entry_date") or False,
                "notes": (data.get("notes") or "").strip(),
            }
            if not vals["name"] or not vals["farm_id"] or not vals["species_id"]:
                raise ValueError("Nom, exploitation et espèce obligatoires.")
            animal.write(vals)
            return request.redirect("/my/agriculture/livestock/%s" % animal.id)
        except (ValueError, AccessError, UserError) as error:
            farms = request.env["agriculture.farm"].sudo().search([])
            species = request.env["agriculture.livestock.species"].sudo().search([])
            return request.render(
                "agriculture_manage_website.livestock_form",
                {"animal": animal, "values": data, "farms": farms, "species": species, "error": str(error)},
            )

    @http.route("/my/agriculture/livestock/<int:animal_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def livestock_delete(self, animal_id, **kwargs):
        animal = request.env["agriculture.livestock.animal"].sudo().search([("id", "=", animal_id)], limit=1)
        if not animal:
            return request.not_found()
        try:
            animal.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/livestock/%s" % animal_id)
        return request.redirect("/my/agriculture/livestock")