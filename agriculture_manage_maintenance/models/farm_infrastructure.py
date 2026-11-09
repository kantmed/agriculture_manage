from odoo import fields, models, _


class AgricultureFarmInfrastructure(models.Model):
    _inherit = "agriculture.farm.infrastructure"

    maintenance_equipment_ids = fields.One2many(
        "maintenance.equipment", "agriculture_infrastructure_id",
        string="Équipements de l'infrastructure",
    )
    maintenance_equipment_count = fields.Integer(
        string="Nombre d'équipements", compute="_compute_maintenance_counts",
    )
    maintenance_request_count = fields.Integer(
        string="Demandes de maintenance", compute="_compute_maintenance_counts",
    )

    def _compute_maintenance_counts(self):
        Equipment = self.env["maintenance.equipment"]
        Request = self.env["maintenance.request"]
        for infrastructure in self:
            infrastructure.maintenance_equipment_count = Equipment.search_count([
                ("agriculture_infrastructure_id", "=", infrastructure.id)
            ])
            infrastructure.maintenance_request_count = Request.search_count([
                ("agriculture_infrastructure_id", "=", infrastructure.id)
            ])

    def action_view_maintenance_equipment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Équipements"),
            "res_model": "maintenance.equipment",
            "view_mode": "list,form",
            "domain": [("agriculture_infrastructure_id", "=", self.id)],
            "context": {
                "default_agriculture_farm_id": self.farm_id.id,
                "default_agriculture_site_id": self.site_id.id,
                "default_agriculture_infrastructure_id": self.id,
            },
        }

    def action_view_maintenance_requests(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Interventions de maintenance"),
            "res_model": "maintenance.request",
            "view_mode": "list,form",
            "domain": [("agriculture_infrastructure_id", "=", self.id)],
        }
