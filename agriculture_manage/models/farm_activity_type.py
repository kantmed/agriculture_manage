from odoo import fields, models


class AgricultureFarmActivityType(models.Model):
    _name = "agriculture.farm.activity.type"
    _description = "Type d'activité agricole"
    _order = "sequence, name"

    name = fields.Char(
        string="Activité",
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

    _farm_activity_code_unique = models.Constraint(
        "UNIQUE(code)",
        "Le code de l'activité doit être unique.",
    )