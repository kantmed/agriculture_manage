from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    agriculture_asset_scope = fields.Selection(
        [("none", "Non affectée"), ("company", "Groupe / société"), ("farm", "Exploitation"), ("site", "Site")],
        string="Affectation agricole de l'immobilisation", default="none",
    )
    agriculture_farm_id = fields.Many2one("agriculture.farm", string="Exploitation de l'immobilisation", check_company=True)
    agriculture_site_id = fields.Many2one("agriculture.farm.site", string="Site de l'immobilisation")
    agriculture_project_id = fields.Many2one("project.project", string="Projet agricole de l'immobilisation", check_company=True)
    agriculture_asset_id = fields.Many2one("account.asset.asset", string="Immobilisation créée", readonly=True, copy=False)

    @api.onchange("agriculture_site_id")
    def _onchange_agriculture_site_id(self):
        if self.agriculture_site_id:
            self.agriculture_farm_id = self.agriculture_site_id.farm_id
            self.agriculture_asset_scope = "site"

    @api.constrains("agriculture_asset_scope", "agriculture_farm_id", "agriculture_site_id", "company_id", "agriculture_project_id")
    def _check_invoice_asset_assignment(self):
        for line in self:
            if line.agriculture_farm_id and line.agriculture_farm_id.company_id != line.company_id:
                raise ValidationError(_("L'exploitation de l'immobilisation doit appartenir à la société de la facture."))
            if line.agriculture_project_id and line.agriculture_project_id.company_id != line.company_id:
                raise ValidationError(_("Le projet doit appartenir à la société de la facture."))
            if line.agriculture_asset_scope == "farm" and (not line.agriculture_farm_id or line.agriculture_site_id):
                raise ValidationError(_("Sélectionnez une exploitation et aucun site pour cette affectation."))
            if line.agriculture_asset_scope == "site" and (not line.agriculture_site_id or line.agriculture_site_id.farm_id != line.agriculture_farm_id):
                raise ValidationError(_("Le site doit appartenir à l'exploitation sélectionnée."))
            if line.agriculture_asset_scope in ("none", "company") and (line.agriculture_farm_id or line.agriculture_site_id):
                raise ValidationError(_("Aucune exploitation ni aucun site ne doit être sélectionné pour cette affectation."))

    def asset_create(self):
        """Create once per invoice line and carry the agricultural assignment over."""
        for line in self:
            # A project-linked invoice line is a project cost, not a separate
            # fixed asset. The single project asset is created at project completion.
            if line.agriculture_project_id:
                continue
            category = line._get_asset_category()
            if not category or line.agriculture_asset_id:
                continue
            existing = self.env["account.asset.asset"].search(
                [("agriculture_invoice_line_id", "=", line.id)], limit=1
            )
            if existing:
                line.agriculture_asset_id = existing
                continue
            move = line.move_id
            company = move.company_id
            invoice_date = move.invoice_date or move.date
            source_currency = line.currency_id or move.currency_id
            value = source_currency._convert(line.price_subtotal, company.currency_id, company, invoice_date)
            vals = {
                "name": line.name,
                "code": move.name or False,
                "category_id": category.id,
                "value": value,
                "partner_id": line.partner_id.id,
                "company_id": company.id,
                "currency_id": company.currency_id.id,
                "date": invoice_date,
                "invoice_id": move.id,
                "agriculture_invoice_line_id": line.id,
                "agriculture_scope": line.agriculture_asset_scope or "none",
                "agriculture_farm_id": line.agriculture_farm_id.id,
                "agriculture_site_id": line.agriculture_site_id.id,
                "agriculture_project_id": line.agriculture_project_id.id,
            }
            category_values = self.env["account.asset.asset"].onchange_category_id_values(category.id)
            vals.update(category_values.get("value", {}))
            # Re-apply explicit agricultural/company-currency values after category defaults.
            vals.update({
                "value": value,
                "company_id": company.id,
                "currency_id": company.currency_id.id,
                "agriculture_invoice_line_id": line.id,
                "agriculture_scope": line.agriculture_asset_scope or "none",
                "agriculture_farm_id": line.agriculture_farm_id.id,
                "agriculture_site_id": line.agriculture_site_id.id,
                "agriculture_project_id": line.agriculture_project_id.id,
            })
            asset = self.env["account.asset.asset"].create(vals)
            line.agriculture_asset_id = asset
            if category.open_asset:
                asset.validate()
        return True
