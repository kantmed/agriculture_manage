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
