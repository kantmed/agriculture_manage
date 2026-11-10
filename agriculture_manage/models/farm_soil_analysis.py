from odoo import fields, models


class AgricultureFarmSoilAnalysis(models.Model):
    _name = "agriculture.farm.soil.analysis"
    _description = "Analyse de sol"
    _order = "analysis_date desc, id desc"

    plot_id = fields.Many2one(
        "agriculture.farm.plot", string="Parcelle", required=True, ondelete="cascade", index=True,
    )
    analysis_date = fields.Date(string="Date d'analyse", required=True, default=fields.Date.context_today)
    ph = fields.Float(string="pH")
    fertility = fields.Selection([
        ("low", "Faible"),
        ("medium", "Moyenne"),
        ("high", "Élevée"),
    ], string="Fertilité")
    organic_matter = fields.Float(string="Matière organique (%)")
    slope = fields.Float(string="Pente (%)")
    water_source = fields.Char(string="Source d'eau")
    water_availability = fields.Selection([
        ("permanent", "Permanente"),
        ("seasonal", "Saisonnière"),
        ("limited", "Limitée"),
        ("none", "Aucune"),
    ], string="Disponibilité en eau")
    notes = fields.Text(string="Notes / recommandations")
