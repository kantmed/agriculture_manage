from odoo import fields, models

class AgricultureLivestockBreed(models.Model):
    _name = "agriculture.livestock.breed"
    _description = "Race animale"
    _order = "species_id, name"

    name = fields.Char(string="Race", required=True, translate=True)
    code = fields.Char(string="Code")
    species_id = fields.Many2one("agriculture.livestock.species", required=True, ondelete="restrict")
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)
