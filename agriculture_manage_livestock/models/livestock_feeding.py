from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class AgricultureLivestockRation(models.Model):
    _name = "agriculture.livestock.ration"
    _description = "Ration alimentaire"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "farm_id, species_id, name"

    name = fields.Char(string="Nom de la ration", required=True, tracking=True)
    active = fields.Boolean(default=True)
    farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation", required=True,
        ondelete="restrict", tracking=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", store=True, readonly=True,
    )
    species_id = fields.Many2one(
        "agriculture.livestock.species", string="Espèce", required=True,
        ondelete="restrict",
    )
    purpose = fields.Selection([
        ("meat", "Viande"), ("milk", "Lait"), ("breeding", "Reproduction"),
        ("fattening", "Engraissement"), ("eggs", "Œufs"),
        ("wool", "Laine"), ("other", "Autres productions"),
    ], string="Objectif", default="other")
    line_ids = fields.One2many(
        "agriculture.livestock.ration.line", "ration_id",
        string="Composition de la ration", copy=True,
    )
    total_energy_per_head = fields.Float(
        string="Énergie totale par tête (kcal)", compute="_compute_totals", store=True,
    )
    total_protein_per_head = fields.Float(
        string="Protéines totales par tête (g)", compute="_compute_totals", store=True,
    )

    @api.depends("line_ids.energy_per_head", "line_ids.protein_per_head")
    def _compute_totals(self):
        for ration in self:
            ration.total_energy_per_head = sum(ration.line_ids.mapped("energy_per_head"))
            ration.total_protein_per_head = sum(ration.line_ids.mapped("protein_per_head"))
    notes = fields.Text(string="Observations")

    @api.constrains("farm_id", "species_id", "line_ids")
    def _check_ration(self):
        for ration in self:
            products = ration.line_ids.mapped("product_id")
            if len(products) != len(ration.line_ids):
                raise ValidationError(_("Un même aliment ne peut apparaître qu'une seule fois dans une ration."))


class AgricultureLivestockRationLine(models.Model):
    _name = "agriculture.livestock.ration.line"
    _description = "Ligne de ration alimentaire"
    _order = "ration_id, sequence, id"

    ration_id = fields.Many2one(
        "agriculture.livestock.ration", required=True,
        ondelete="cascade", index=True,
    )
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        "product.product", string="Aliment", required=True,
        ondelete="restrict",
        domain="[('product_tmpl_id.agriculture_category', '=', 'feed')]",
    )
    quantity_per_head = fields.Float(
        string="Quantité par tête et par jour", required=True,
        digits="Product Unit of Measure",
    )
    uom_id = fields.Many2one(
        "uom.uom", string="Unité",
        related="product_id.uom_id", readonly=True,
    )
    note = fields.Char(string="Remarque")

    energy_per_head = fields.Float(
        string="Énergie par tête (kcal)", compute="_compute_nutrition", store=True,
    )
    protein_per_head = fields.Float(
        string="Protéines par tête (g)", compute="_compute_nutrition", store=True,
    )

    @api.depends("quantity_per_head", "product_id.nutrition_energy_kcal", "product_id.nutrition_protein", "uom_id")
    def _compute_nutrition(self):
        for line in self:
            qty = line.quantity_per_head or 0.0
            line.energy_per_head = qty * (line.product_id.nutrition_energy_kcal or 0.0)
            line.protein_per_head = qty * (line.product_id.nutrition_protein or 0.0)
    def _check_ration_line(self):
        for line in self:
            if line.quantity_per_head <= 0:
                raise ValidationError(_("La quantité par tête et par jour doit être strictement positive."))
            if line.product_id and line.product_id.product_tmpl_id.agriculture_category != "feed":
                raise ValidationError(_("Le produit sélectionné doit être classé dans les aliments pour animaux."))
            if line.product_id and not line.product_id.is_storable:
                raise ValidationError(_("L'aliment doit être un produit suivi en stock."))


class AgricultureLivestockFeeding(models.Model):
    _name = "agriculture.livestock.feeding"
    _description = "Distribution d'aliments"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(
        string="Référence", readonly=True, copy=False,
        default="Nouveau", tracking=True,
    )
    date = fields.Date(
        string="Date de distribution", required=True,
        default=fields.Date.context_today, tracking=True,
    )
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("prepared", "Sortie de stock préparée"),
        ("done", "Consommation enregistrée"),
        ("cancel", "Annulé"),
    ], string="État", default="draft", required=True, tracking=True)

    animal_id = fields.Many2one(
        "agriculture.livestock.animal", string="Animal",
        ondelete="restrict", index=True,
        domain="[('state', '=', 'active')]",
    )
    herd_id = fields.Many2one(
        "agriculture.livestock.herd", string="Lot",
        ondelete="restrict", index=True,
        domain="[('active', '=', True)]",
    )
    farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation",
        compute="_compute_target", store=True, readonly=True, index=True,
    )
    company_id = fields.Many2one(
        "res.company", compute="_compute_target", store=True, readonly=True,
    )
    species_id = fields.Many2one(
        "agriculture.livestock.species", compute="_compute_target",
        store=True, readonly=True,
    )
    headcount = fields.Float(
        string="Effectif concerné", default=1.0, required=True,
        readonly=True, tracking=True,
        help="Effectif mémorisé au moment de la distribution.",
    )
    feeding_days = fields.Integer(
        string="Nombre de jours couverts", default=1, required=True,
    )
    ration_id = fields.Many2one(
        "agriculture.livestock.ration", string="Ration",
        ondelete="restrict",
        domain="[('farm_id', '=', farm_id), ('species_id', '=', species_id), ('active', '=', True)]",
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="Magasin source",
        required=True, ondelete="restrict",
        domain="['|', ('farm_id', '=', False), ('farm_id', '=', farm_id)]",
    )
    line_ids = fields.One2many(
        "agriculture.livestock.feeding.line", "feeding_id",
        string="Aliments distribués", copy=True,
    )
    stock_picking_ids = fields.Many2many(
        "stock.picking",
        "agriculture_livestock_feeding_stock_picking_rel",
        "feeding_id", "picking_id",
        string="Sorties de stock", readonly=True, copy=False,
    )
    stock_picking_count = fields.Integer(
        string="Nombre de transferts", compute="_compute_stock_picking_count",
    )
    notes = fields.Text(string="Observations")

    @api.depends(
        "animal_id.farm_id", "animal_id.company_id", "animal_id.species_id",
        "herd_id.farm_id", "herd_id.company_id", "herd_id.species_id",
    )
    def _compute_target(self):
        for rec in self:
            farm = rec.animal_id.farm_id or rec.herd_id.farm_id
            rec.farm_id = farm
            rec.company_id = farm.company_id
            rec.species_id = rec.animal_id.species_id or rec.herd_id.species_id

    @api.depends("stock_picking_ids")
    def _compute_stock_picking_count(self):
        for rec in self:
            rec.stock_picking_count = len(rec.stock_picking_ids)

    @api.onchange("animal_id", "herd_id")
    def _onchange_target(self):
        for rec in self:
            if rec.animal_id:
                rec.headcount = 1.0
                rec.herd_id = False
            elif rec.herd_id:
                rec.headcount = rec.herd_id.headcount
                rec.animal_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "agriculture.livestock.feeding"
                ) or "Nouveau"
            if vals.get("animal_id"):
                vals["headcount"] = 1.0
            elif vals.get("herd_id") and "headcount" not in vals:
                herd = self.env["agriculture.livestock.herd"].browse(vals["herd_id"])
                vals["headcount"] = herd.headcount
        return super().create(vals_list)

    @api.constrains(
        "animal_id", "herd_id", "farm_id", "species_id", "headcount",
        "feeding_days", "ration_id", "warehouse_id", "state",
    )
    def _check_feeding(self):
        for rec in self:
            if bool(rec.animal_id) == bool(rec.herd_id):
                raise ValidationError(_("Une distribution doit concerner exactement un animal ou un lot."))
            if rec.animal_id and rec.animal_id.state != "active":
                raise ValidationError(_("La distribution ne peut concerner qu'un animal actif."))
            if rec.herd_id and not rec.herd_id.active:
                raise ValidationError(_("Le lot sélectionné doit être actif."))
            if rec.headcount <= 0 or rec.feeding_days <= 0:
                raise ValidationError(_("L'effectif et le nombre de jours doivent être strictement positifs."))
            if rec.ration_id and (
                rec.ration_id.farm_id != rec.farm_id
                or rec.ration_id.species_id != rec.species_id
            ):
                raise ValidationError(_("La ration doit correspondre à l'exploitation et à l'espèce concernées."))
            if rec.warehouse_id and rec.company_id and rec.warehouse_id.company_id != rec.company_id:
                raise ValidationError(_("Le magasin source doit appartenir à la société de l'exploitation."))
            if rec.warehouse_id and rec.farm_id and rec.warehouse_id.farm_id and rec.warehouse_id.farm_id != rec.farm_id:
                raise ValidationError(_("Le magasin source doit appartenir à l'exploitation concernée."))
            if rec.state in ("prepared", "done") and not rec.stock_picking_ids:
                raise ValidationError(_("Une distribution préparée ou terminée doit être liée à une sortie de stock."))

    def action_apply_ration(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("La ration ne peut être appliquée qu'à une distribution en brouillon."))
            if not rec.ration_id:
                raise UserError(_("Sélectionnez d'abord une ration."))
            if not rec.ration_id.line_ids:
                raise UserError(_("La ration ne contient aucun aliment."))
            if rec.line_ids:
                raise UserError(_("Supprimez les lignes existantes avant d'appliquer la ration."))
            commands = []
            for ration_line in rec.ration_id.line_ids:
                commands.append(Command.create({
                    "product_id": ration_line.product_id.id,
                    "quantity": ration_line.quantity_per_head * rec.headcount * rec.feeding_days,
                    "uom_id": ration_line.product_id.uom_id.id,
                    "note": ration_line.note,
                }))
            rec.write({"line_ids": commands})
        return True

    def action_prepare_stock_issue(self):
        self.ensure_one()
        if self.state not in ("draft", "prepared"):
            raise UserError(_("Seule une distribution en brouillon ou sans sortie active peut être préparée."))
        if not self.line_ids:
            raise UserError(_("Ajoutez des aliments ou appliquez une ration avant de préparer la sortie."))
        if self.stock_picking_ids.filtered(lambda p: p.state != "cancel"):
            raise UserError(_("Une sortie de stock active existe déjà pour cette distribution."))
        company = self.company_id
        warehouse = self.warehouse_id
        if not company or warehouse.company_id != company:
            raise UserError(_("Le magasin doit appartenir à la société de l'exploitation."))
        if warehouse.farm_id and warehouse.farm_id != self.farm_id:
            raise UserError(_("Le magasin doit appartenir à l'exploitation concernée."))
        picking_type = warehouse.int_type_id
        if not picking_type:
            raise UserError(_("Aucun type de transfert interne n'est configuré pour le magasin %s.", warehouse.display_name))
        production_location = self.env["stock.location"].with_company(company).search([
            ("usage", "=", "production"),
            ("company_id", "in", [company.id, False]),
        ], order="company_id desc, id", limit=1)
        if not production_location:
            raise UserError(_("L'emplacement virtuel de production est introuvable pour la société %s.", company.display_name))

        move_commands = []
        for line in self.line_ids:
            line._check_feeding_line()
            move_commands.append(Command.create({
                "name": line.product_id.display_name,
                "product_id": line.product_id.id,
                "product_uom": line.uom_id.id,
                "product_uom_qty": line.quantity,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": production_location.id,
                "company_id": company.id,
            }))
        picking_vals = {
            "picking_type_id": picking_type.id,
            "location_id": warehouse.lot_stock_id.id,
            "location_dest_id": production_location.id,
            "company_id": company.id,
            "origin": self.name,
            "farm_id": self.farm_id.id,
            "move_ids": move_commands,
        }
        picking = self.env["stock.picking"].with_company(company).create(picking_vals)
        picking.action_confirm()
        self.write({
            "stock_picking_ids": [Command.link(picking.id)],
            "state": "prepared",
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Sortie de stock des aliments"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": picking.id,
            "target": "current",
        }

    def action_mark_done(self):
        for rec in self:
            if rec.state != "prepared":
                raise UserError(_("Seule une distribution préparée peut être clôturée."))
            pickings = rec.stock_picking_ids
            if not pickings or any(p.state != "done" for p in pickings):
                raise UserError(_("Validez d'abord la sortie de stock dans l'application Inventaire."))
            for line in rec.line_ids:
                done_moves = pickings.mapped("move_ids").filtered(
                    lambda move: move.state == "done" and move.product_id == line.product_id
                )
                done_qty = sum(
                    move.product_uom._compute_quantity(move.quantity, line.uom_id, round=False)
                    for move in done_moves
                )
                if float_compare(done_qty, line.quantity, precision_rounding=line.uom_id.rounding) < 0:
                    raise UserError(_(
                        "La quantité réellement sortie pour '%(product)s' est inférieure à la quantité prévue.",
                        product=line.product_id.display_name,
                    ))
            rec.state = "done"
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(_("Une distribution consommée ne peut pas être annulée. Corrigez-la par un mouvement de stock inverse."))
            done_pickings = rec.stock_picking_ids.filtered(lambda p: p.state == "done")
            if done_pickings:
                raise UserError(_("Une sortie de stock est déjà terminée. Annulez ou retournez le transfert depuis Inventaire."))
            for picking in rec.stock_picking_ids.filtered(lambda p: p.state not in ("cancel", "done")):
                picking.action_cancel()
            rec.state = "cancel"
        return True

    def action_open_stock_pickings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sorties de stock"),
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", self.stock_picking_ids.ids)],
            "target": "current",
        }


class AgricultureLivestockFeedingLine(models.Model):
    _name = "agriculture.livestock.feeding.line"
    _description = "Ligne de distribution alimentaire"
    _order = "feeding_id, id"

    feeding_id = fields.Many2one(
        "agriculture.livestock.feeding", required=True,
        ondelete="cascade", index=True,
    )
    product_id = fields.Many2one(
        "product.product", string="Aliment", required=True,
        ondelete="restrict",
        domain="[('product_tmpl_id.agriculture_category', '=', 'feed')]",
    )
    quantity = fields.Float(
        string="Quantité", required=True, digits="Product Unit of Measure",
    )
    uom_id = fields.Many2one(
        "uom.uom", string="Unité", required=True,
    )
    note = fields.Char(string="Remarque")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.uom_id = line.product_id.uom_id

    @api.constrains("feeding_id", "product_id", "quantity", "uom_id")
    def _check_feeding_line(self):
        for line in self:
            if line.feeding_id and line.feeding_id.state != "draft":
                raise ValidationError(_("Les lignes d'une distribution ne peuvent plus être modifiées après la préparation du stock."))
            if line.quantity <= 0:
                raise ValidationError(_("La quantité distribuée doit être strictement positive."))
            if line.product_id and line.product_id.product_tmpl_id.agriculture_category != "feed":
                raise ValidationError(_("Le produit sélectionné doit être classé dans les aliments pour animaux."))
            if line.product_id and not line.product_id.is_storable:
                raise ValidationError(_("L'aliment doit être un produit suivi en stock."))
            if line.product_id and line.uom_id and not line.product_id.uom_id._has_common_reference(line.uom_id):
                raise ValidationError(_("L'unité de distribution doit être compatible avec l'unité du produit."))

    def unlink(self):
        if any(line.feeding_id.state != "draft" for line in self):
            raise UserError(_("Les lignes d'une distribution ne peuvent plus être supprimées après la préparation du stock."))
        return super().unlink()
