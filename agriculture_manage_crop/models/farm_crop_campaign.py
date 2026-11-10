import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AgricultureFarmCropCampaign(models.Model):
    _name = "agriculture.farm.crop.campaign"
    _description = "Campagne culturale"
    _order = "start_date desc, name"

    name = fields.Char(
        string="Campagne",
        required=True,
    )
    code = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default="Nouveau",
    )
    farm_id = fields.Many2one(
        "agriculture.farm",
        string="Exploitation",
        required=True,
        ondelete="cascade",
    )
    crop_id = fields.Many2one(
        "agriculture.farm.crop",
        string="Culture",
        required=True,
    )
    variety_id = fields.Many2one(
        "agriculture.farm.crop.variety",
        string="Variété",
        domain="[('crop_id', '=', crop_id)]",
    )
    start_date = fields.Date(string="Date de début")
    end_date = fields.Date(string="Date de fin")
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("active", "En cours"),
            ("done", "Terminée"),
            ("cancelled", "Annulée"),
        ],
        string="État",
        default="draft",
        required=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id",
        store=True,
        readonly=True,
    )
    campaign_plot_ids = fields.One2many(
        "agriculture.farm.crop.campaign.plot",
        "campaign_id",
        string="Parcelles de la campagne",
    )
    operation_ids = fields.One2many(
        "agriculture.farm.operation",
        "campaign_id",
        string="Opérations",
    )
    harvest_ids = fields.One2many(
        "agriculture.farm.harvest",
        "campaign_id",
        string="Récoltes",
    )
    notes = fields.Html(string="Observations")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code") in (False, None, "Nouveau"):
                years = re.findall(r"(?<!\d)\d{4}(?!\d)", vals.get("name") or "")
                if len(years) == 2:
                    start_year, end_year = years
                else:
                    current_year = str(fields.Date.context_today(self).year)
                    start_year = end_year = current_year
                vals["code"] = f"CAM-{start_year}-{end_year}"
        return super().create(vals_list)
    
    @api.constrains("start_date", "end_date")
    def _check_campaign_dates(self):
        for campaign in self:
            if (
                campaign.start_date
                and campaign.end_date
                and campaign.end_date < campaign.start_date
            ):
                raise ValidationError(
                    _("La date de fin doit être postérieure ou égale à la date de début.")
                )

    @api.constrains("crop_id", "variety_id")
    def _check_variety_crop(self):
        for campaign in self:
            if (
                campaign.variety_id
                and campaign.variety_id.crop_id != campaign.crop_id
            ):
                raise ValidationError(
                    _("La variété sélectionnée doit appartenir à la culture de la campagne.")
                )