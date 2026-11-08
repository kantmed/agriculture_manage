from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = "stock.move"

    agriculture_operation_line_id = fields.Many2one(
        "agriculture.farm.operation.line",
        string="Ligne d'opération agricole",
        index=True,
        ondelete="set null",
        copy=True,
    )

    @api.constrains("agriculture_operation_line_id", "product_id", "company_id")
    def _check_agriculture_operation_line(self):
        for move in self:
            line = move.agriculture_operation_line_id
            if not line:
                continue
            if line.product_id and move.product_id != line.product_id:
                raise ValidationError(_("Le produit du mouvement doit correspondre à la ligne de travail agricole."))
            operation_company = line.operation_id.company_id
            if operation_company and move.company_id != operation_company:
                raise ValidationError(_("Le mouvement de stock et le travail agricole doivent appartenir à la même société."))

    def _action_done(self, *args, **kwargs):
        """Synchronize agricultural costs after Odoo has created valuation layers.

        This hook also covers immediate-transfer and backorder wizard flows,
        which may complete moves without calling stock.picking.button_validate
        a second time.
        """
        result = super()._action_done(*args, **kwargs)
        lines = self.filtered(
            lambda move: move.state == "done" and move.agriculture_operation_line_id
        ).mapped("agriculture_operation_line_id")
        lines._agriculture_sync_stock_valuation()
        return result


class StockPicking(models.Model):
    _inherit = "stock.picking"

    farm_id = fields.Many2one(
        "agriculture.farm",
        string="Exploitation",
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    campaign_plot_id = fields.Many2one(
        "agriculture.farm.crop.campaign.plot",
        string="Parcelle de campagne",
        index=True,
        ondelete="restrict",
        tracking=True,
    )
    agriculture_operation_id = fields.Many2one(
        "agriculture.farm.operation",
        string="Travail agricole",
        index=True,
        ondelete="restrict",
        copy=True,
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            operation_id = vals.get("agriculture_operation_id")
            campaign_plot_id = vals.get("campaign_plot_id")
            if operation_id and not vals.get("farm_id"):
                operation = self.env["agriculture.farm.operation"].browse(operation_id)
                vals["farm_id"] = operation.farm_id.id
                if not vals.get("company_id"):
                    vals["company_id"] = operation.company_id.id or self.env.company.id
            elif campaign_plot_id and not vals.get("farm_id"):
                campaign_plot = self.env["agriculture.farm.crop.campaign.plot"].browse(campaign_plot_id)
                vals["farm_id"] = campaign_plot.campaign_id.farm_id.id
                if not vals.get("company_id"):
                    vals["company_id"] = campaign_plot.campaign_id.company_id.id
        return super().create(vals_list)

    @api.constrains("farm_id", "company_id", "campaign_plot_id", "agriculture_operation_id")
    def _check_agriculture_links(self):
        for picking in self:
            if picking.farm_id and picking.farm_id.company_id != picking.company_id:
                raise ValidationError(_("L'exploitation doit appartenir à la société du transfert."))
            if picking.campaign_plot_id:
                if picking.farm_id and picking.campaign_plot_id.campaign_id.farm_id != picking.farm_id:
                    raise ValidationError(_("La parcelle de campagne doit appartenir à l'exploitation sélectionnée."))
            if picking.agriculture_operation_id:
                operation = picking.agriculture_operation_id
                if picking.farm_id and operation.farm_id and picking.farm_id != operation.farm_id:
                    raise ValidationError(_("Le travail et le transfert doivent concerner la même exploitation."))
                if picking.campaign_plot_id and (
                    not operation.campaign_id
                    or picking.campaign_plot_id.campaign_id != operation.campaign_id
                    or picking.campaign_plot_id.plot_id != operation.plot_id
                ):
                    raise ValidationError(_("La parcelle de campagne du transfert doit correspondre à celle du travail."))

    def button_validate(self):
        # The authoritative synchronization is performed by stock.move._action_done
        # after stock_account has created the valuation layers. Keep the standard
        # picking workflow unchanged (including wizard actions).
        return super().button_validate()
