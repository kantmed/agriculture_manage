from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AgricultureFarmHarvest(models.Model):
    _name = "agriculture.farm.harvest"
    _description = "Récolte"
    _order = "harvest_date desc, name"

    name = fields.Char(
        string="Récolte",
        required=True,
    )
    code = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default="Nouveau",
    )
    campaign_id = fields.Many2one(
        "agriculture.farm.crop.campaign",
        string="Campagne",
        ondelete="cascade",
    )
    plot_id = fields.Many2one(
        "agriculture.farm.plot",
        string="Parcelle",
    )
    harvest_date = fields.Date(
        string="Date de récolte",
        default=fields.Date.context_today,
        required=True,
    )
    quantity = fields.Float(
        string="Quantité",
        required=True,
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unité",
    )
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
    product_id = fields.Many2one(
        "product.product",
        string="Produit récolté",
    )
    location_id = fields.Many2one(
        "stock.location",
        string="Emplacement source",
        help="Emplacement virtuel de récolte.",
    )
    location_dest_id = fields.Many2one(
        "stock.location",
        string="Emplacement de destination",
        domain="[('usage', '=', 'internal')]",
    )
    picking_id = fields.Many2one(
        "stock.picking",
        string="Transfert de stock",
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("done", "Validée"),
            ("cancelled", "Annulée"),
        ],
        string="État",
        default="draft",
    )
    company_id = fields.Many2one(
        related="campaign_id.company_id",
        store=True,
        readonly=True,
    )
    lot_ids = fields.One2many(
        "agriculture.farm.harvest.lot",
        "harvest_id",
        string="Lots",
    )
    notes = fields.Html(string="Observations")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("farm.harvest")
                    or "Nouveau"
                )
        return super().create(vals_list)


    def action_validate(self):
        self.ensure_one()
        if self.state != "draft":
            return True
        if not self.product_id or not self.quantity or not self.location_dest_id:
            raise UserError(_("Veuillez renseigner le produit, la quantité et l'emplacement de destination."))
        company = self.company_id or self.env.company
        location_src = self.location_id
        if not location_src:
            location_src = self.env["stock.location"].sudo().with_company(company).search(
                [("usage", "=", "inventory")], limit=1
            )
            if not location_src:
                location_src = self.env["stock.location"].with_company(company).create({
                    "name": "Récolte",
                    "usage": "inventory",
                    "company_id": company.id,
                })
        picking_type = self.env["stock.picking.type"].sudo().with_company(company).search(
            [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company.id)],
            limit=1,
        )
        if not picking_type:
            raise UserError(_("Aucun type de transfert entrant n'est configuré pour la société %s.") % company.name)
        picking = self.env["stock.picking"].with_company(company).create({
            "picking_type_id": picking_type.id,
            "location_id": location_src.id,
            "location_dest_id": self.location_dest_id.id,
            "origin": self.code or self.name,
            "company_id": company.id,
        })
        self.env["stock.move"].with_company(company).create({
            "product_id": self.product_id.id,
            "product_uom_qty": self.quantity,
            "product_uom": self.uom_id.id or self.product_id.uom_id.id,
            "picking_id": picking.id,
            "location_id": location_src.id,
            "location_dest_id": self.location_dest_id.id,
            "company_id": company.id,
        })
        picking.with_company(company).action_confirm()
        picking.with_company(company).button_validate()
        self.picking_id = picking.id
        self.state = "done"
        return True

    def action_cancel(self):
        self.state = "cancelled"
        return True
