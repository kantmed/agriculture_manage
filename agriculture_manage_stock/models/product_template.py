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

    @api.depends("agriculture_category")
    def _compute_agriculture_is_input(self):
        for product in self:
            product.agriculture_is_input = bool(product.agriculture_category)
