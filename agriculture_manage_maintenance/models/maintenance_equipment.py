from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    agriculture_farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation agricole", index=True,
        ondelete="restrict", tracking=True,
    )
    agriculture_site_id = fields.Many2one(
        "agriculture.farm.site", string="Site agricole", index=True,
        ondelete="restrict", tracking=True,
        domain="[('farm_id', '=', agriculture_farm_id)]",
    )
    agriculture_infrastructure_id = fields.Many2one(
        "agriculture.farm.infrastructure", string="Infrastructure associée",
        index=True, ondelete="restrict", tracking=True,
        domain="[('farm_id', '=', agriculture_farm_id), '|', ('site_id', '=', False), ('site_id', '=', agriculture_site_id)]",
    )
    @api.onchange("agriculture_farm_id")
    def _onchange_agriculture_farm_id(self):
        for equipment in self:
            if equipment.agriculture_farm_id:
                equipment.company_id = equipment.agriculture_farm_id.company_id
            if equipment.agriculture_site_id and equipment.agriculture_site_id.farm_id != equipment.agriculture_farm_id:
                equipment.agriculture_site_id = False
            if equipment.agriculture_infrastructure_id and equipment.agriculture_infrastructure_id.farm_id != equipment.agriculture_farm_id:
                equipment.agriculture_infrastructure_id = False

    @api.onchange("agriculture_infrastructure_id")
    def _onchange_agriculture_infrastructure_id(self):
        for equipment in self:
            infrastructure = equipment.agriculture_infrastructure_id
            if infrastructure:
                equipment.agriculture_farm_id = infrastructure.farm_id
                equipment.agriculture_site_id = infrastructure.site_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            farm_id = vals.get("agriculture_farm_id")
            if farm_id and not vals.get("company_id"):
                vals["company_id"] = self.env["agriculture.farm"].browse(farm_id).company_id.id
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if vals.get("agriculture_farm_id") and "company_id" not in vals:
            vals["company_id"] = self.env["agriculture.farm"].browse(vals["agriculture_farm_id"]).company_id.id
        return super().write(vals)

    @api.constrains("agriculture_farm_id", "agriculture_site_id", "agriculture_infrastructure_id", "company_id")
    def _check_agriculture_assignment(self):
        for equipment in self:
            farm = equipment.agriculture_farm_id
            site = equipment.agriculture_site_id
            infrastructure = equipment.agriculture_infrastructure_id
            if farm and equipment.company_id and farm.company_id != equipment.company_id:
                raise ValidationError(_("La société de l'équipement doit correspondre à celle de l'exploitation."))
            if site and (not farm or site.farm_id != farm):
                raise ValidationError(_("Le site doit appartenir à l'exploitation sélectionnée."))
            if infrastructure:
                if not farm or infrastructure.farm_id != farm:
                    raise ValidationError(_("L'infrastructure doit appartenir à l'exploitation sélectionnée."))
                if site and infrastructure.site_id and infrastructure.site_id != site:
                    raise ValidationError(_("L'infrastructure doit appartenir au site sélectionné."))
