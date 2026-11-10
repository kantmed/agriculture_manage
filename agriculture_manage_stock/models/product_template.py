from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    agriculture_category = fields.Selection(
        [
            ("seed", "Semences et plants"),
            ("fertilizer", "Engrais et amendements"),
            ("phytosanitary", "Produits phytosanitaires"),
            ("fuel", "Carburants et lubrifiants"),
            ("irrigation", "Matériel d'irrigation"),
            ("spare_part", "Pièces de rechange"),
            ("feed", "Aliments pour animaux"),
            ("packaging", "Emballages"),
            ("other", "Autre intrant agricole"),
        ],
        string="Catégorie agricole",
        help="Classe le produit dans le catalogue des intrants agricoles.",
        index=True,
    )
    agriculture_is_input = fields.Boolean(
        string="Intrant agricole",
        compute="_compute_agriculture_is_input",
        store=True,
    )

    # Nutrition (pour les aliments)
    nutrition_energy_kcal = fields.Float(
        string="Énergie (kcal/kg)",
        help="Apport énergétique par kg d'aliment.",
    )
    nutrition_protein = fields.Float(
        string="Protéines (%)",
        help="Teneur en protéines.",
    )
    nutrition_fat = fields.Float(
        string="Matières grasses (%)",
        help="Teneur en matières grasses.",
    )
    nutrition_fiber = fields.Float(
        string="Fibres (%)",
        help="Teneur en fibres.",
    )

    @api.depends("agriculture_category")
    def _compute_agriculture_is_input(self):
        for product in self:
            product.agriculture_is_input = bool(product.agriculture_category)
