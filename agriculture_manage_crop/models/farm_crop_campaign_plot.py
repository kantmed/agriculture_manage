from odoo import fields, models


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
