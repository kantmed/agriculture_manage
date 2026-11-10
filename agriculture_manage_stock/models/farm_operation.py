from collections import defaultdict

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class FarmOperationLine(models.Model):
    _inherit = "agriculture.farm.operation.line"

    consume_stock = fields.Boolean(
        string="Consommer du stock",
        help="Cette ligne doit être consommée depuis un magasin Odoo avant la clôture du travail.",
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="Magasin source",
        domain="['|', ('farm_id', '=', False), ('farm_id', '=', operation_id.farm_id)]",
        ondelete="restrict",
    )
    # Legacy pointer retained for compatibility with existing views/data.
    stock_move_id = fields.Many2one(
        "stock.move", string="Mouvement principal", readonly=True,
        copy=False, ondelete="set null",
    )
    # One agricultural line may be split over several stock moves/backorders.
    stock_move_ids = fields.One2many(
        "stock.move", "agriculture_operation_line_id",
        string="Mouvements de stock", readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Devise", compute="_compute_currency_id",
    )
    stock_valuation_value = fields.Monetary(
        string="Valeur valorisée consommée", currency_field="currency_id",
        readonly=True, copy=False,
        help="Valeur nette des mouvements terminés, issue de la valorisation native Odoo.",
    )
    stock_valuation_quantity = fields.Float(
        string="Quantité valorisée", readonly=True, copy=False,
    )
    stock_cost_updated = fields.Boolean(
        string="Coût actualisé depuis le stock", readonly=True, copy=False,
    )
    stock_valuation_layer_count = fields.Integer(
        string="Couches de valorisation", compute="_compute_stock_valuation_layer_count",
    )

    @api.depends("stock_move_ids")
    def _compute_stock_valuation_layer_count(self):
        for line in self:
            line.stock_valuation_layer_count = sum(
                len(move.stock_valuation_layer_ids)
                for move in line.stock_move_ids
                if "stock_valuation_layer_ids" in move._fields
            )

    def _agriculture_sync_stock_valuation(self):
        """Rebuild the line cost from Odoo stock valuation layers.

        A stock issue from an internal location to the production location
        creates negative valuation layers. Negating their value/quantity gives
        a positive consumed cost/quantity. A return creates positive layers
        and therefore reduces the net agricultural cost automatically.
        """
        for line in self:
            done_moves = line.stock_move_ids.filtered(lambda move: move.state == "done")
            total_value = 0.0
            total_quantity = 0.0
            has_valuation = False

            for move in done_moves:
                layers = (
                    move.stock_valuation_layer_ids
                    if "stock_valuation_layer_ids" in move._fields
                    else self.env["stock.valuation.layer"]
                )
                if layers:
                    has_valuation = True
                    for layer in layers:
                        # SVL quantity is expressed in the product's default UoM.
                        layer_quantity = layer.quantity
                        product_uom = layer.product_id.uom_id
                        if product_uom and line.uom_id and product_uom._has_common_reference(line.uom_id):
                            layer_quantity = product_uom._compute_quantity(
                                layer_quantity, line.uom_id, round=False,
                            )
                        total_quantity -= layer_quantity
                        total_value -= layer.value
                elif "value" in move._fields and getattr(move, "is_valued", True):
                    # Compatibility fallback for installations where a valued
                    # move exposes its value but no SVL relation is available.
                    has_valuation = True
                    move_quantity = abs(move.quantity)
                    quantity_in_line_uom = move.uom_id._compute_quantity(
                        move_quantity, line.uom_id, round=False,
                    ) if line.uom_id else move_quantity
                    direction = -1.0 if (
                        move.location_id.usage == "production"
                        and move.location_dest_id.usage == "internal"
                    ) else 1.0
                    total_quantity += direction * quantity_in_line_uom
                    total_value += direction * abs(move.value)

            currency = line.currency_id or line.operation_id.company_id.currency_id
            if currency:
                total_value = currency.round(total_value)
            line.write({
                "stock_valuation_value": total_value,
                "stock_valuation_quantity": total_quantity,
                "stock_cost_updated": has_valuation,
            })

    @api.depends("operation_id.company_id")
    def _compute_currency_id(self):
        for line in self:
            line.currency_id = line.operation_id.company_id.currency_id or line.env.company.currency_id

    @api.constrains("consume_stock", "product_id", "warehouse_id", "quantity", "uom_id", "operation_id")
    def _check_stock_consumption_line(self):
        for line in self:
            if not line.consume_stock:
                continue
            if not line.product_id:
                raise ValidationError(_("Sélectionnez un produit pour chaque ligne consommant du stock."))
            if not line.product_id.is_storable:
                raise ValidationError(_("Le produit %s doit être suivi en stock.", line.product_id.display_name))
            if not line.warehouse_id:
                raise ValidationError(_("Sélectionnez le magasin source pour chaque ligne consommant du stock."))
            if line.quantity <= 0:
                raise ValidationError(_("La quantité à consommer doit être strictement positive."))
            company = line.operation_id.company_id or line.env.company
            if line.warehouse_id.company_id != company:
                raise ValidationError(_("Le magasin source doit appartenir à la société du travail."))
            farm = line.operation_id.farm_id
            if farm and line.warehouse_id.farm_id and line.warehouse_id.farm_id != farm:
                raise ValidationError(_("Le magasin source doit appartenir à l'exploitation du travail."))
            if not line.uom_id:
                raise ValidationError(_("Sélectionnez une unité pour chaque ligne consommant du stock."))
            if not line.product_id.uom_id._has_common_reference(line.uom_id):
                raise ValidationError(_("L'unité de la ligne doit être compatible avec l'unité du produit."))


class FarmOperation(models.Model):
    _inherit = "agriculture.farm.operation"

    farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation", compute="_compute_farm_id", store=True, readonly=True,
    )

    @api.depends("campaign_id")
    def _compute_farm_id(self):
        for operation in self:
            if operation.campaign_id:
                operation.farm_id = operation.campaign_id.farm_id
            elif "project_id" in operation._fields and operation.project_id:
                operation.farm_id = operation.project_id.agriculture_farm_id
            else:
                operation.farm_id = False
    stock_picking_ids = fields.One2many(
        "stock.picking", "agriculture_operation_id", string="Sorties de stock",
    )
    stock_picking_count = fields.Integer(compute="_compute_stock_picking_count")

    @api.depends("stock_picking_ids")
    def _compute_stock_picking_count(self):
        for operation in self:
            operation.stock_picking_count = len(operation.stock_picking_ids)

    def action_prepare_stock_issue(self):
        """Prepare native internal transfers, grouped by source warehouse.

        This method is idempotent: it refuses to create another active issue
        for the same operation. Reservations and validation remain in Odoo Stock.
        """
        created_pickings = self.env["stock.picking"]
        for operation in self:
            if operation.state != "draft":
                raise UserError(_("La sortie de stock doit être préparée avant la clôture du travail."))
            lines = operation.line_ids.filtered("consume_stock")
            if not lines:
                raise UserError(_("Aucune ligne n'est marquée pour consommer du stock."))
            if operation.stock_picking_ids.filtered(lambda picking: picking.state != "cancel"):
                raise UserError(_("Une sortie de stock active existe déjà pour ce travail."))

            grouped = defaultdict(lambda: self.env["agriculture.farm.operation.line"])
            for line in lines:
                # Re-run the business checks before creating any stock document.
                line._check_stock_consumption_line()
                grouped[line.warehouse_id.id] |= line

            for warehouse_id, warehouse_lines in grouped.items():
                warehouse = self.env["stock.warehouse"].browse(warehouse_id)
                company = warehouse.company_id
                picking_type = warehouse.int_type_id
                if not picking_type:
                    raise UserError(_("Aucun type de transfert interne n'est configuré pour le magasin %s.", warehouse.display_name))

                production_location = self.env["stock.location"].with_company(company).search([
                    ("usage", "=", "production"),
                    ("company_id", "in", [company.id, False]),
                ], order="company_id desc, id", limit=1)
                if not production_location:
                    raise UserError(_("L'emplacement virtuel de production est introuvable pour la société %s.", company.display_name))

                campaign_plot = False
                if operation.campaign_id and operation.plot_id:
                    campaign_plot = operation.campaign_id.campaign_plot_ids.filtered(
                        lambda item: item.plot_id == operation.plot_id
                    )[:1]

                move_commands = []
                for line in warehouse_lines:
                    move_commands.append(Command.create({
                        "product_id": line.product_id.id,
                        "uom_id": line.uom_id.id,
                        "product_uom_qty": line.quantity,
                        "location_id": warehouse.lot_stock_id.id,
                        "location_dest_id": production_location.id,
                        "company_id": company.id,
                        "agriculture_operation_line_id": line.id,
                    }))

                picking_vals = {
                    "picking_type_id": picking_type.id,
                    "location_id": warehouse.lot_stock_id.id,
                    "location_dest_id": production_location.id,
                    "company_id": company.id,
                    "origin": operation.code or operation.name,
                    "agriculture_operation_id": operation.id,
                    "move_ids": move_commands,
                }
                if operation.farm_id:
                    picking_vals["farm_id"] = operation.farm_id.id
                if campaign_plot:
                    picking_vals["campaign_plot_id"] = campaign_plot.id

                picking = self.env["stock.picking"].with_company(company).create(picking_vals)
                picking.action_confirm()
                for move in picking.move_ids:
                    if move.agriculture_operation_line_id:
                        move.agriculture_operation_line_id.stock_move_id = move
                created_pickings |= picking

        if len(created_pickings) == 1:
            return {
                "type": "ir.actions.act_window", "name": _("Sortie de stock"),
                "res_model": "stock.picking", "view_mode": "form",
                "res_id": created_pickings.id, "target": "current",
            }
        return {
            "type": "ir.actions.act_window", "name": _("Sorties de stock"),
            "res_model": "stock.picking", "view_mode": "list,form",
            "domain": [("id", "in", created_pickings.ids)], "target": "current",
        }

    def action_validate(self):
        for operation in self:
            if operation.state != "draft":
                continue
            stock_lines = operation.line_ids.filtered("consume_stock")
            if not stock_lines:
                continue
            active_pickings = operation.stock_picking_ids.filtered(lambda picking: picking.state != "cancel")
            if not active_pickings:
                raise UserError(_("Préparez d'abord les sorties de stock avant de terminer ce travail."))
            pending = active_pickings.filtered(lambda picking: picking.state != "done")
            if pending:
                raise UserError(_("Validez toutes les sorties de stock liées au travail avant de le terminer."))
            for line in stock_lines:
                done_moves = line.stock_move_ids.filtered(lambda move: move.state == "done")
                done_quantity = sum(
                    move.uom_id._compute_quantity(move.quantity, line.uom_id, round=False)
                    for move in done_moves
                )
                if float_compare(done_quantity, line.quantity, precision_rounding=line.uom_id.rounding) < 0:
                    raise UserError(_(
                        "La quantité réellement sortie pour '%(line)s' est inférieure à la quantité prévue. "
                        "Complétez le transfert ou ajustez la quantité de la ligne.",
                        line=line.display_name,
                    ))
        # The crop base method now only changes the agricultural state. It no
        # longer creates an outgoing picking, so no duplicate stock issue occurs.
        return super().action_validate()

    def action_recalculate_stock_valuation(self):
        done_operations = self.filtered(lambda op: op.state == "done")
        for operation in done_operations:
            for line in operation.line_ids.filtered("consume_stock"):
                line._agriculture_sync_stock_valuation()
        return True

    def action_cancel(self):
        for operation in self:
            if operation.stock_picking_ids.filtered(lambda picking: picking.state == "done"):
                raise UserError(_("Impossible d'annuler un travail dont une sortie de stock est déjà validée."))
            open_pickings = operation.stock_picking_ids.filtered(lambda picking: picking.state != "cancel")
            if open_pickings:
                open_pickings.action_cancel()
        return super().action_cancel()

    def action_view_stock_pickings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Sorties de stock"),
            "res_model": "stock.picking", "view_mode": "list,form",
            "domain": [("agriculture_operation_id", "=", self.id)],
            "context": {"default_agriculture_operation_id": self.id},
        }
