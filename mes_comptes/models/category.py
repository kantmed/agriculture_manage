from odoo import fields, models


class MesComptesCategory(models.Model):
    _name = "mes.comptes.category"
    _description = "Catégorie financière"
    _order = "transaction_type, name"

    name = fields.Char(required=True)
    transaction_type = fields.Selection([
        ("income", "Recette"), ("expense", "Dépense")
    ], required=True, default="expense")
    color = fields.Integer(string="Couleur")
    active = fields.Boolean(default=True)
