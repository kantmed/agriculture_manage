# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplateAgriExtension(models.Model):
    _inherit = "product.template"

    gest_agri_input_category_id = fields.Many2one(
        "gest_agri.input.category", string="Catégorie d'intrant agricole",
        ondelete="set null", index=True,
    )
    gest_agri_input_type = fields.Selection(
        selection=[
            ("seed", "Semence / Plant"),
            ("fertilizer", "Engrais"),
            ("amendment", "Amendement"),
            ("phytosanitary", "Produit phytosanitaire"),
            ("treatment", "Produit de traitement"),
            ("cleaning", "Produit de nettoyage"),
            ("material", "Matériel et fourniture"),
            ("spare_part", "Pièce / Consommable"),
            ("other", "Autre intrant"),
        ],
        string="Type d'intrant agricole",
        index=True,
    )
    gest_agri_manufacturer = fields.Char(string="Fabricant")
    gest_agri_composition = fields.Text(string="Composition / Concentration")
    gest_agri_dosage = fields.Char(string="Dosage recommandé")
    gest_agri_storage_conditions = fields.Text(string="Conditions de stockage")
    gest_agri_shelf_life_days = fields.Integer(string="Durée de conservation (jours)")
    gest_agri_requires_lot = fields.Boolean(string="Traçabilité par lot requise", default=False)
    gest_agri_requires_expiry = fields.Boolean(string="Date de péremption requise", default=False)
    gest_agri_safety_notes = fields.Text(string="Précautions de manipulation")