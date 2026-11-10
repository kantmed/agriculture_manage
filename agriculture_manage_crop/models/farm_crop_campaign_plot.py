from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AgricultureFarmCropCampaignPlot(models.Model):
    _name = "agriculture.farm.crop.campaign.plot"
    _description = "Parcelle de campagne"
    _order = "campaign_id, plot_id"

    campaign_id = fields.Many2one(
        "agriculture.farm.crop.campaign",
        string="Campagne",
        required=True,
        ondelete="cascade",
    )
    plot_id = fields.Many2one(
        "agriculture.farm.plot",
        string="Parcelle",
        required=True,
    )
    area_ha = fields.Float(
        string="Surface (ha)",
        related="plot_id.area_ha",
        readonly=True,
    )
    planting_date = fields.Date(string="Date de semis/plantation")
    expected_harvest_date = fields.Date(
        string="Date de récolte prévue",
    )
    state = fields.Selection(
        [
            ("planned", "Prévue"),
            ("planted", "Semée"),
            ("growing", "En croissance"),
            ("harvested", "Récoltée"),
        ],
        string="État",
        default="planned",
    )
    notes = fields.Text(string="Notes")

    @api.constrains("campaign_id", "plot_id")
    def _check_plot_farm(self):
        for record in self:
            if (
                record.campaign_id
                and record.plot_id
                and record.campaign_id.farm_id != record.plot_id.farm_id
            ):
                raise ValidationError(
                    _(
                        "La parcelle doit appartenir à la même exploitation "
                        "que la campagne."
                    )
                )

    @api.constrains("planting_date", "expected_harvest_date")
    def _check_planting_harvest_dates(self):
        for record in self:
            if (
                record.planting_date
                and record.expected_harvest_date
                and record.expected_harvest_date < record.planting_date
            ):
                raise ValidationError(
                    _(
                        "La date de récolte prévue doit être postérieure "
                        "ou égale à la date de semis ou de plantation."
                    )
                )