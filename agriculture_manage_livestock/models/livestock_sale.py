from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    livestock_sale = fields.Boolean(
        string="Vente d'élevage",
        copy=False,
        tracking=True,
        help="Active le suivi de la vente d'un animal ou d'un lot d'élevage.",
    )
    livestock_animal_id = fields.Many2one(
        "agriculture.livestock.animal",
        string="Animal vendu",
        copy=False,
        ondelete="restrict",
        domain="[('state', '=', 'active'), ('company_id', '=', company_id)]",
    )
    livestock_herd_id = fields.Many2one(
        "agriculture.livestock.herd",
        string="Lot vendu",
        copy=False,
        ondelete="restrict",
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )
    livestock_quantity = fields.Float(
        string="Effectif vendu",
        default=1.0,
        copy=False,
        digits=(16, 2),
        help="Nombre de têtes vendues. Pour un animal individuel, la quantité est obligatoirement égale à 1.",
    )
    livestock_farm_id = fields.Many2one(
        "agriculture.farm",
        string="Exploitation d'élevage",
        compute="_compute_livestock_target",
        store=True,
        readonly=True,
    )
    livestock_species_id = fields.Many2one(
        "agriculture.livestock.species",
        string="Espèce",
        compute="_compute_livestock_target",
        store=True,
        readonly=True,
    )
    livestock_movement_id = fields.Many2one(
        "agriculture.livestock.movement",
        string="Mouvement de cheptel généré",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )

    @api.depends(
        "livestock_animal_id.farm_id",
        "livestock_animal_id.species_id",
        "livestock_herd_id.farm_id",
        "livestock_herd_id.species_id",
    )
    def _compute_livestock_target(self):
        for order in self:
            target = order.livestock_animal_id or order.livestock_herd_id
            order.livestock_farm_id = target.farm_id if target else False
            order.livestock_species_id = target.species_id if target else False

    @api.onchange("livestock_animal_id")
    def _onchange_livestock_animal_id(self):
        for order in self:
            if order.livestock_animal_id:
                order.livestock_herd_id = False
                order.livestock_quantity = 1.0
                order.livestock_sale = True
                order.company_id = order.livestock_animal_id.company_id

    @api.onchange("livestock_herd_id")
    def _onchange_livestock_herd_id(self):
        for order in self:
            if order.livestock_herd_id:
                order.livestock_animal_id = False
                order.livestock_sale = True
                order.company_id = order.livestock_herd_id.company_id
                order.livestock_quantity = order.livestock_herd_id.headcount

    @api.constrains(
        "livestock_sale", "livestock_animal_id", "livestock_herd_id",
        "livestock_quantity", "company_id",
    )
    def _check_livestock_sale_target(self):
        for order in self:
            if not order.livestock_sale:
                if order.livestock_animal_id or order.livestock_herd_id:
                    raise ValidationError(_("Un animal ou un lot ne peut être renseigné que pour une vente d'élevage."))
                continue
            if bool(order.livestock_animal_id) == bool(order.livestock_herd_id):
                raise ValidationError(_("Une vente d'élevage doit concerner exactement un animal ou un lot."))
            target = order.livestock_animal_id or order.livestock_herd_id
            if target.company_id != order.company_id:
                raise ValidationError(_("L'animal ou le lot doit appartenir à la société de la commande."))
            if order.livestock_animal_id:
                if order.livestock_animal_id.state != "active":
                    raise ValidationError(_("Seuls les animaux actifs peuvent être vendus."))
                if float_compare(order.livestock_quantity, 1.0, precision_digits=2) != 0:
                    raise ValidationError(_("La vente d'un animal individuel doit porter sur une seule tête."))
            if order.livestock_herd_id:
                if not order.livestock_herd_id.active:
                    raise ValidationError(_("Seuls les lots actifs peuvent être vendus."))
                if order.livestock_herd_id.tracking_mode != "batch":
                    raise ValidationError(_("La vente collective exige un lot suivi par effectif."))
                if order.livestock_quantity <= 0:
                    raise ValidationError(_("L'effectif vendu doit être strictement positif."))
                if order.livestock_quantity > order.livestock_herd_id.headcount:
                    raise ValidationError(_("L'effectif vendu dépasse l'effectif disponible dans le lot."))

    def _check_livestock_sale_before_confirmation(self):
        for order in self.filtered("livestock_sale"):
            order._check_livestock_sale_target()
            stockable_lines = order.order_line.filtered(
                lambda line: not line.display_type
                and line.product_id
                and line.product_id.is_storable
                and line.product_uom_qty > 0
            )
            if not stockable_lines:
                raise UserError(_("Une vente d'élevage doit comporter au moins une ligne de produit stockable livrable."))
            if order.livestock_movement_id:
                raise UserError(_("Un mouvement de vente de cheptel existe déjà pour cette commande."))

    def action_confirm(self):
        self._check_livestock_sale_before_confirmation()
        return super().action_confirm()

    def action_view_livestock_movement(self):
        self.ensure_one()
        if not self.livestock_movement_id:
            raise UserError(_("Aucun mouvement de cheptel n'a encore été généré."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Mouvement de cheptel"),
            "res_model": "agriculture.livestock.movement",
            "view_mode": "form",
            "res_id": self.livestock_movement_id.id,
            "target": "current",
        }


class AgricultureLivestockMovement(models.Model):
    _inherit = "agriculture.livestock.movement"

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Commande client",
        readonly=True,
        copy=False,
        ondelete="restrict",
        index=True,
    )

    _sale_order_unique = models.Constraint(
        "UNIQUE(sale_order_id)",
        "Une commande ne peut générer qu'un seul mouvement de vente de cheptel.",
    )

    @api.constrains("sale_order_id", "movement_type", "tracking_mode", "animal_id", "source_herd_id", "quantity", "farm_id", "species_id")
    def _check_sale_order_consistency(self):
        for movement in self:
            order = movement.sale_order_id
            if not order:
                continue
            if movement.movement_type != "sale" or not order.livestock_sale:
                raise ValidationError(_("La commande liée doit être une vente d'élevage."))
            if movement.farm_id != order.livestock_farm_id or movement.species_id != order.livestock_species_id:
                raise ValidationError(_("L'exploitation et l'espèce du mouvement doivent correspondre à la commande."))
            if order.livestock_animal_id:
                if movement.tracking_mode != "individual" or movement.animal_id != order.livestock_animal_id:
                    raise ValidationError(_("Le mouvement doit concerner l'animal indiqué sur la commande."))
            elif order.livestock_herd_id:
                if movement.tracking_mode != "batch" or movement.source_herd_id != order.livestock_herd_id:
                    raise ValidationError(_("Le mouvement doit concerner le lot indiqué sur la commande."))
                if movement.quantity != order.livestock_quantity:
                    raise ValidationError(_("La quantité du mouvement doit correspondre à l'effectif vendu."))


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        result = super()._action_done()
        orders = self.move_ids.mapped("sale_line_id.order_id").filtered(
            lambda order: order and order.livestock_sale and not order.livestock_movement_id
        )
        for order in orders:
            stockable_lines = order.order_line.filtered(
                lambda line: not line.display_type
                and line.product_id
                and line.product_id.is_storable
                and line.product_uom_qty > 0
            )
            if not stockable_lines:
                continue
            # The herd/animal is marked sold only after the complete sale order
            # quantity has been delivered through the standard Odoo Stock flow.
            not_fully_delivered = any(
                float_compare(
                    line.qty_delivered,
                    line.product_uom_qty,
                    precision_rounding=line.product_uom.rounding,
                ) < 0
                for line in stockable_lines
            )
            if not_fully_delivered:
                continue
            open_pickings = order.picking_ids.filtered(
                lambda picking: picking.state not in ("done", "cancel")
            )
            if open_pickings:
                continue

            if order.livestock_animal_id:
                movement_vals = {
                    "movement_type": "sale",
                    "tracking_mode": "individual",
                    "farm_id": order.livestock_farm_id.id,
                    "species_id": order.livestock_species_id.id,
                    "animal_id": order.livestock_animal_id.id,
                    "quantity": 1.0,
                    "sale_order_id": order.id,
                    "date": fields.Date.context_today(order),
                    "notes": _("Vente réalisée via la commande %s.", order.name),
                }
            else:
                movement_vals = {
                    "movement_type": "sale",
                    "tracking_mode": "batch",
                    "farm_id": order.livestock_farm_id.id,
                    "species_id": order.livestock_species_id.id,
                    "source_herd_id": order.livestock_herd_id.id,
                    "quantity": order.livestock_quantity,
                    "sale_order_id": order.id,
                    "date": fields.Date.context_today(order),
                    "notes": _("Vente réalisée via la commande %s.", order.name),
                }
            movement = self.env["agriculture.livestock.movement"].create(movement_vals)
            movement.action_apply()
            order.livestock_movement_id = movement
        return result
