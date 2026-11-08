from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAssetAsset(models.Model):
    _inherit = "account.asset.asset"

    agriculture_invoice_line_id = fields.Many2one(
        "account.move.line", string="Ligne de facture source", ondelete="set null", copy=False, index=True,
    )
    agriculture_scope = fields.Selection(
        [
            ("none", "Non affectée"),
            ("company", "Groupe / société"),
            ("farm", "Exploitation"),
            ("site", "Site"),
        ],
        string="Niveau d'affectation agricole",
        default="none",
        required=True,
        tracking=True,
        help="Laisser Non affectée pour une immobilisation qui ne nécessite pas de suivi agricole.",
    )
    agriculture_farm_id = fields.Many2one(
        "agriculture.farm", string="Exploitation", ondelete="restrict",
        check_company=True, tracking=True,
    )
    agriculture_site_id = fields.Many2one(
        "agriculture.farm.site", string="Site", ondelete="restrict", tracking=True,
        domain="[('farm_id', '=', agriculture_farm_id)]",
    )
    agriculture_project_id = fields.Many2one(
        "project.project", string="Projet agricole", ondelete="restrict",
        check_company=True, index=True,
    )

    _agriculture_project_asset_unique = models.Constraint(
        "UNIQUE(agriculture_project_id)",
        "Un projet d'investissement ne peut générer qu'une seule immobilisation.",
    )
    agriculture_origin = fields.Selection(
        [
            ("direct", "Acquisition directe"),
            ("subcontracted", "Réalisation sous-traitée"),
            ("internal", "Réalisation par la société"),
        ],
        string="Mode d'obtention",
        required=True,
        default="direct",
        tracking=True,
        help="Indique comment l'immobilisation a été obtenue. Les réalisations sous-traitées ou internes doivent être rattachées à un projet.",
    )
    agriculture_allocation_ids = fields.One2many(
        "agriculture.asset.allocation", "asset_id", string="Exploitations utilisatrices",
        copy=True,
    )
    agriculture_allocation_total = fields.Float(
        string="Total de répartition (%)", compute="_compute_agriculture_allocation_total",
    )

    @api.depends("agriculture_allocation_ids.percentage")
    def _compute_agriculture_allocation_total(self):
        for asset in self:
            asset.agriculture_allocation_total = sum(asset.agriculture_allocation_ids.mapped("percentage"))

    @api.onchange("agriculture_site_id")
    def _onchange_agriculture_site_id(self):
        if self.agriculture_site_id:
            self.agriculture_farm_id = self.agriculture_site_id.farm_id
            self.agriculture_scope = "site"

    @api.onchange("agriculture_scope")
    def _onchange_agriculture_scope(self):
        if self.agriculture_scope == "company":
            self.agriculture_farm_id = False
            self.agriculture_site_id = False
        elif self.agriculture_scope == "farm":
            self.agriculture_site_id = False

    @api.constrains("agriculture_scope", "agriculture_farm_id", "agriculture_site_id", "company_id", "agriculture_allocation_ids", "agriculture_project_id", "agriculture_origin")
    def _check_agriculture_assignment(self):
        for asset in self:
            farm = asset.agriculture_farm_id
            site = asset.agriculture_site_id
            if farm and farm.company_id != asset.company_id:
                raise ValidationError(_("L'exploitation doit appartenir à la même société que l'immobilisation."))
            if asset.agriculture_project_id and asset.agriculture_project_id.company_id != asset.company_id:
                raise ValidationError(_("Le projet et l'immobilisation doivent appartenir à la même société."))
            if asset.agriculture_origin in ("subcontracted", "internal") and not asset.agriculture_project_id:
                raise ValidationError(_("Une immobilisation réalisée en sous-traitance ou par la société doit être rattachée à un projet."))
            if asset.agriculture_scope == "none":
                if farm or site or asset.agriculture_allocation_ids:
                    raise ValidationError(_("Une immobilisation non affectée ne doit pas avoir de rattachement agricole."))
            elif asset.agriculture_scope == "company":
                if farm or site:
                    raise ValidationError(_("Une immobilisation de groupe ne doit pas être rattachée directement à une exploitation ou à un site."))
                if asset.agriculture_allocation_ids:
                    total = sum(asset.agriculture_allocation_ids.mapped("percentage"))
                    if total > 100.0001:
                        raise ValidationError(_("La répartition entre exploitations ne peut pas dépasser 100 % (actuellement : %.2f %%).") % total)
                    if asset.state != "draft" and abs(total - 100.0) > 0.0001:
                        raise ValidationError(_("Avant confirmation, la répartition entre exploitations doit totaliser 100 % (actuellement : %.2f %%).") % total)
            elif asset.agriculture_scope == "farm":
                if not farm or site:
                    raise ValidationError(_("Une immobilisation affectée à une exploitation doit avoir une exploitation et aucun site."))
                if asset.agriculture_allocation_ids:
                    raise ValidationError(_("Les répartitions multi-exploitations sont réservées aux immobilisations de groupe."))
            elif asset.agriculture_scope == "site":
                if not farm or not site or site.farm_id != farm:
                    raise ValidationError(_("Une immobilisation affectée à un site doit avoir le site et son exploitation correspondante."))
                if asset.agriculture_allocation_ids:
                    raise ValidationError(_("Une immobilisation affectée à un site ne peut pas avoir de répartition multi-exploitations."))

    def _agriculture_check_allocation_complete(self):
        for asset in self.filtered(lambda item: item.agriculture_scope == "company" and item.agriculture_allocation_ids):
            total = sum(asset.agriculture_allocation_ids.mapped("percentage"))
            if abs(total - 100.0) > 0.0001:
                raise ValidationError(_("La répartition entre exploitations doit totaliser 100 % avant confirmation (actuellement : %.2f %%).") % total)
            missing_analytic = asset.agriculture_allocation_ids.filtered(lambda allocation: not allocation.farm_id.analytic_account_id)
            if missing_analytic:
                names = ", ".join(missing_analytic.mapped("farm_id.name"))
                raise ValidationError(_("Un compte analytique doit être configuré sur chaque exploitation utilisatrice avant confirmation : %s") % names)

    def validate(self):
        self._agriculture_check_allocation_complete()
        return super().validate()

    def _agriculture_get_analytic_distribution(self):
        """Build native Odoo analytic_distribution for depreciation expense."""
        self.ensure_one()
        if self.agriculture_scope == "company" and self.agriculture_allocation_ids:
            distribution = {}
            for allocation in self.agriculture_allocation_ids:
                account = allocation.farm_id.analytic_account_id
                if account:
                    key = str(account.id)
                    distribution[key] = distribution.get(key, 0.0) + allocation.percentage
            return distribution
        if self.agriculture_scope in ("farm", "site") and self.agriculture_farm_id.analytic_account_id:
            return {str(self.agriculture_farm_id.analytic_account_id.id): 100.0}
        return {}

    def _compute_entries(self, date, group_entries=False):
        """Keep agricultural depreciation entries separate to preserve each farm split."""
        if group_entries and self.filtered(lambda asset: asset.agriculture_scope != "none"):
            depreciation_lines = self.env["account.asset.depreciation.line"].search([
                ("asset_id", "in", self.ids),
                ("depreciation_date", "<=", date),
                ("move_check", "=", False),
            ])
            return depreciation_lines.create_move()
        return super()._compute_entries(date, group_entries=group_entries)

