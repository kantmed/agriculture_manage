from odoo import fields, models


class AgricultureFarmHarvestLot(models.Model):
    _name = "agriculture.farm.harvest.lot"
    _description = "Lot de récolte"
    _order = "harvest_id, name"

    harvest_id = fields.Many2one(
        "agriculture.farm.harvest",
        string="Récolte",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Lot",
        required=True,
    )
    code = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default="Nouveau",
    )
    quantity = fields.Float(
        string="Quantité",
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unité",
    )
    storage_location = fields.Char(string="Emplacement de stockage")
    quality = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Bon"),
            ("average", "Moyen"),
            ("poor", "Mauvais"),
        ],
        string="Qualité",
        default="good",
    )
    notes = fields.Text(string="Notes")

    # sequence handled in creation? code default; no auto sequence here to keep simple
