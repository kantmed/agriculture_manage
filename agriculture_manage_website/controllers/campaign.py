# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError


class AgricultureCampaignPortal(http.Controller):

    def _campaign_domain(self):
        user = request.env.user
        return [("farm_id.company_id", "in", user.company_ids.ids)]

    def _get_campaign(self, campaign_id):
        return request.env["agriculture.farm.crop.campaign"].sudo().search(
            [("id", "=", campaign_id)] + self._campaign_domain(), limit=1
        )

    def _form_options(self, values=None, campaign=None, error=None):
        values = values or {}
        farms = request.env["agriculture.farm"].sudo().search([])
        crops = request.env["agriculture.farm.crop"].sudo().search([])
        return request.render(
            "agriculture_manage_website.campaign_form",
            {
                "campaign": campaign,
                "values": values,
                "farms": farms,
                "crops": crops,
                "error": error,
            },
        )

    def _read_values(self):
        data = request.httprequest.form
        try:
            farm_id = int(data.get("farm_id") or 0)
            crop_id = int(data.get("crop_id") or 0)
            variety_id = int(data.get("variety_id") or 0)
        except (ValueError, TypeError):
            raise ValueError("Valeur numérique invalide.")
        return {
            "name": (data.get("name") or "").strip(),
            "farm_id": farm_id or False,
            "crop_id": crop_id or False,
            "variety_id": variety_id or False,
            "start_date": data.get("start_date") or False,
            "end_date": data.get("end_date") or False,
            "state": data.get("state") or "draft",
            "notes": (data.get("notes") or "").strip(),
        }

    @http.route("/my/agriculture/campaigns", type="http", auth="user", website=True)
    def campaign_list(self, search="", **kwargs):
        domain = self._campaign_domain()
        if search:
            domain += ["|", ("name", "ilike", search), ("farm_id.name", "ilike", search)]
        campaigns = request.env["agriculture.farm.crop.campaign"].sudo().search(domain, order="start_date desc, name")
        return request.render(
            "agriculture_manage_website.campaign_list",
            {"campaigns": campaigns, "search": search},
        )

    @http.route("/my/agriculture/campaigns/new", type="http", auth="user", website=True)
    def campaign_new(self, **kwargs):
        return self._form_options()

    @http.route("/my/agriculture/campaigns/create", type="http", auth="user", website=True, methods=["POST"])
    def campaign_create(self, **kwargs):
        try:
            values = self._read_values()
            if not values["name"]:
                return self._form_options(values, error="Le nom de la campagne est obligatoire.")
            if not values["farm_id"] or not values["crop_id"]:
                return self._form_options(values, error="L'exploitation et la culture sont obligatoires.")
            campaign = request.env["agriculture.farm.crop.campaign"].sudo().create(values)
            return request.redirect("/my/agriculture/campaigns/%s" % campaign.id)
        except ValueError as error:
            return self._form_options(error=str(error))
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/campaigns")

    @http.route("/my/agriculture/campaigns/<int:campaign_id>", type="http", auth="user", website=True)
    def campaign_detail(self, campaign_id, **kwargs):
        campaign = self._get_campaign(campaign_id)
        if not campaign:
            return request.not_found()
        return request.render(
            "agriculture_manage_website.campaign_detail",
            {"campaign": campaign},
        )

    @http.route("/my/agriculture/campaigns/<int:campaign_id>/edit", type="http", auth="user", website=True)
    def campaign_edit(self, campaign_id, **kwargs):
        campaign = self._get_campaign(campaign_id)
        if not campaign:
            return request.not_found()
        return self._form_options(campaign=campaign)

    @http.route("/my/agriculture/campaigns/<int:campaign_id>/update", type="http", auth="user", website=True, methods=["POST"])
    def campaign_update(self, campaign_id, **kwargs):
        campaign = self._get_campaign(campaign_id)
        if not campaign:
            return request.not_found()
        try:
            values = self._read_values()
            if not values["name"]:
                return self._form_options(values, campaign=campaign, error="Le nom de la campagne est obligatoire.")
            campaign.write(values)
            return request.redirect("/my/agriculture/campaigns/%s" % campaign.id)
        except ValueError as error:
            return self._form_options(campaign=campaign, error=str(error))
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/campaigns/%s" % campaign.id)

    @http.route("/my/agriculture/campaigns/<int:campaign_id>/delete", type="http", auth="user", website=True, methods=["POST"])
    def campaign_delete(self, campaign_id, **kwargs):
        campaign = self._get_campaign(campaign_id)
        if not campaign:
            return request.not_found()
        try:
            campaign.unlink()
        except (AccessError, UserError):
            return request.redirect("/my/agriculture/campaigns/%s" % campaign_id)
        return request.redirect("/my/agriculture/campaigns")