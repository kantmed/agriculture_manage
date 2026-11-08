from odoo import fields, models


class AgricultureFarmIrrigationType(models.Model):
    _name = "agriculture.farm.irrigation.type"
    _description = "Type d'irrigation"
    _order = "sequence, name"

    name = fields.Char(
        string="Type d'irrigation",
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
        "Le code du type d'irrigation doit être unique.",
    )
