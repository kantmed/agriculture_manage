from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AgricultureAssetAllocation(models.Model):
    _name = "agriculture.asset.allocation"
    _description = "Répartition d'une immobilisation entre exploitations"
    _order = "asset_id, farm_id"

    asset_id = fields.Many2one(
        "account.asset.asset", string="Immobilisation", required=True,
        ondelete="cascade", index=True,
    )
    farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation utilisatrice", required=True,
        ondelete="restrict", check_company=True,
    )
    company_id = fields.Many2one(related="asset_id.company_id", store=True, readonly=True)
    percentage = fields.Float(string="Part des coûts (%)", required=True, default=100.0)

    _asset_farm_unique = models.Constraint(
        "UNIQUE(asset_id, farm_id)",
        "Une exploitation ne peut apparaître qu'une fois pour une immobilisation.",
    )
    _percentage_positive = models.Constraint(
        "CHECK(percentage > 0 AND percentage <= 100)",
        "Le pourcentage doit être supérieur à 0 et inférieur ou égal à 100.",
    )

    @api.constrains("asset_id", "farm_id", "percentage")
    def _check_allocation(self):
        for line in self:
            if line.asset_id.company_id != line.farm_id.company_id:
                raise ValidationError(_("L'exploitation utilisatrice doit appartenir à la société de l'immobilisation."))
            if line.asset_id.agriculture_scope != "company":
                raise ValidationError(_("Les exploitations utilisatrices ne sont autorisées que pour une immobilisation affectée au groupe / à la société."))
            if line.percentage <= 0 or line.percentage > 100:
                raise ValidationError(_("Le pourcentage doit être compris entre 0 et 100."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("asset_id")._check_agriculture_assignment()
        return records

    def write(self, vals):
        assets = self.mapped("asset_id")
        result = super().write(vals)
        (assets | self.mapped("asset_id"))._check_agriculture_assignment()
        return result

    def unlink(self):
        assets = self.mapped("asset_id")
        result = super().unlink()
        assets.exists()._check_agriculture_assignment()
        return result
