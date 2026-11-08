from odoo import fields, models


class AgricultureFarmCropType(models.Model):
    _name = "agriculture.farm.crop.type"
    _description = "Type de culture"
    _order = "sequence, name"

    name = fields.Char(
        string="Type de culture",
        required=True,
        translate=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
    )
    sequence = fields.Integer(
        string="Ordre",
        default=10,
    )
    active = fields.Boolean(default=True)
    description = fields.Text(
        string="Description",
        translate=True,
    )

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "Le code du type de culture doit être unique.",
    )
