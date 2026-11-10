from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    agriculture_farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation agricole",
        related="equipment_id.agriculture_farm_id", store=True, readonly=True, index=True,
    )
    agriculture_site_id = fields.Many2one(
        "agriculture.farm.site", string="Site agricole",
        related="equipment_id.agriculture_site_id", store=True, readonly=True, index=True,
    )
    agriculture_infrastructure_id = fields.Many2one(
        "agriculture.farm.infrastructure", string="Infrastructure",
        related="equipment_id.agriculture_infrastructure_id", store=True, readonly=True, index=True,
    )
    agriculture_intervention_cost = fields.Monetary(
        string="Coût de l'intervention", currency_field="agriculture_currency_id",
        tracking=True, help="Coût direct de l'intervention, dans la devise de la société de l'exploitation.",
    )
    agriculture_account_move_id = fields.Many2one(
        "account.move", string="Facture fournisseur", readonly=True, copy=False,
    )
    agriculture_currency_id = fields.Many2one(
        "res.currency", string="Devise",
        related="agriculture_farm_id.company_id.currency_id", store=True, readonly=True,
    )

    @api.onchange("equipment_id")
    def _onchange_agriculture_equipment(self):
        for request in self:
            if request.equipment_id and request.equipment_id.company_id:
                request.company_id = request.equipment_id.company_id

    @api.constrains("equipment_id", "company_id", "agriculture_intervention_cost")
    def _check_agriculture_request(self):
        for request in self:
            if request.equipment_id and request.equipment_id.company_id != request.company_id:
                raise ValidationError(_("La société de l'intervention doit correspondre à celle de l'équipement."))
            if request.agriculture_intervention_cost < 0:
                raise ValidationError(_("Le coût de l'intervention ne peut pas être négatif."))

    def action_view_invoice(self):
        self.ensure_one()
        if not self.agriculture_account_move_id:
            return
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.agriculture_account_move_id.id,
            "target": "current",
        }

    def action_create_invoice(self):
        self.ensure_one()
        if self.agriculture_intervention_cost <= 0:
            raise UserError(_("Le coût de l'intervention doit être strictement positif."))
        if self.agriculture_account_move_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "view_mode": "form",
                "res_id": self.agriculture_account_move_id.id,
                "target": "current",
            }
        partner = (self.agriculture_farm_id.partner_id if self.agriculture_farm_id else False) or self.company_id.partner_id
        expense_account = self.env["account.account"].search([
            ("account_type", "=", "expense"),
            ("company_id", "=", self.company_id.id),
        ], limit=1)
        if not expense_account:
            raise UserError(_("Aucun compte de charge n'est configuré pour cette société."))
        move = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": partner.id,
            "company_id": self.company_id.id,
            "currency_id": self.agriculture_currency_id.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_line_ids": [(0, 0, {
                "name": self.name,
                "quantity": 1.0,
                "price_unit": self.agriculture_intervention_cost,
                "account_id": expense_account.id,
            })],
        })
        self.agriculture_account_move_id = move
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
            "target": "current",
        }
