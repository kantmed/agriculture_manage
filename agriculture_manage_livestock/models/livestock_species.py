from odoo import fields, models

class AgricultureLivestockSpecies(models.Model):
    _name = "agriculture.livestock.species"
    _description = "Espèce animale"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    category = fields.Selection([
        ("ovine", "Ovins"), ("bovine", "Bovins"), ("caprine", "Caprins"),
        ("camelid", "Camelins"), ("poultry", "Volailles"),
        ("apiculture", "Apiculture"), ("other", "Autres")
    ], required=True)
    sequence = fields.Integer(default=10)
    individual_tracking = fields.Boolean(default=True)
    batch_tracking = fields.Boolean(default=True)
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint("UNIQUE(code)", "Le code de l'espèce doit être unique.")
