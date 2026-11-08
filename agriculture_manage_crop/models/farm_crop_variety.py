from odoo import fields, models


class AgricultureFarmCropVariety(models.Model):
    _name = "agriculture.farm.crop.variety"
    _description = "Variété de culture"
    _order = "crop_id, name"

    crop_id = fields.Many2one(
        "agriculture.farm.crop",
        string="Culture",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Variété",
        required=True,
    )
    code = fields.Char(string="Code")
    maturity_days = fields.Integer(string="Cycle (jours)")
    yield_potential = fields.Float(string="Rendement potentiel (t/ha)")
    notes = fields.Text(string="Notes")
