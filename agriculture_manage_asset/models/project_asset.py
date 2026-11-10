from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ProjectProject(models.Model):
    _inherit = "project.project"

    agriculture_asset_ids = fields.One2many(
        "account.asset.asset", "agriculture_project_id", string="Immobilisations issues du projet"
    )
    agriculture_asset_id = fields.Many2one(
        "account.asset.asset", compute="_compute_agriculture_asset_id",
        string="Immobilisation issue du projet (unitaire)",
    )
    agriculture_investment_state = fields.Selection(
        [("in_progress", "En cours"), ("completed", "Achevé")],
        string="État de l'investissement", default="in_progress", tracking=True,
        copy=False,
    )
    agriculture_asset_category_id = fields.Many2one(
        "account.asset.category", string="Modèle d'immobilisation",
        check_company=True,
        domain="[('company_id', '=', company_id), ('type', '=', 'purchase')]",
    )
    agriculture_asset_origin = fields.Selection(
        [("direct", "Acquisition directe"), ("subcontracted", "Réalisation sous-traitée"), ("internal", "Réalisation par la société")],
        string="Mode de réalisation", default="internal",
    )
    agriculture_investment_actual_cost = fields.Monetary(
        string="Coût final immobilisable", currency_field="agriculture_currency_id",
        help="Montant final validé à immobiliser, après rapprochement des achats, prestations et coûts de réalisation. Ne pas saisir ici les dépenses non immobilisables.",
    )
    agriculture_project_invoice_line_ids = fields.One2many(
        "account.move.line", "agriculture_project_id", string="Lignes de factures du projet",
    )
    agriculture_project_invoice_total = fields.Monetary(
        string="Factures fournisseurs comptabilisées", currency_field="agriculture_currency_id",
        compute="_compute_agriculture_project_cost_indicators",
    )
    agriculture_project_operation_total = fields.Monetary(
        string="Coûts saisis sur les opérations", currency_field="agriculture_currency_id",
        compute="_compute_agriculture_project_cost_indicators",
    )

    @api.depends("agriculture_asset_ids")
    def _compute_agriculture_asset_id(self):
        for project in self:
            project.agriculture_asset_id = project.agriculture_asset_ids[:1]

    @api.depends(
        "agriculture_project_invoice_line_ids.price_subtotal",
        "agriculture_project_invoice_line_ids.move_id.state",
        "agriculture_project_invoice_line_ids.move_id.move_type",
        "agriculture_project_invoice_line_ids.move_id.invoice_date",
        "agriculture_project_invoice_line_ids.move_id.date",
        "agriculture_project_invoice_line_ids.currency_id",
        "agriculture_operation_ids.line_ids.cost",
        "agriculture_operation_ids.line_ids.consume_stock",
        "agriculture_operation_ids.line_ids.stock_valuation_value",
        "agriculture_operation_ids.line_ids.stock_cost_updated",
    )
    def _compute_agriculture_project_cost_indicators(self):
        for project in self:
            invoice_total = 0.0
            company = project.company_id
            if not company:
                project.agriculture_project_invoice_total = 0.0
                project.agriculture_project_operation_total = 0.0
                continue
            for line in project.agriculture_project_invoice_line_ids.filtered(
                lambda item: item.move_id.state == "posted"
                and item.move_id.move_type in ("in_invoice", "in_refund")
            ):
                move = line.move_id
                currency = line.currency_id or move.currency_id
                amount = currency._convert(
                    line.price_subtotal,
                    company.currency_id,
                    company,
                    move.invoice_date or move.date,
                )
                if move.move_type == "in_refund":
                    amount = -amount
                invoice_total += amount

            operation_total = 0.0
            for operation_line in project.agriculture_operation_ids.mapped("line_ids"):
                if (
                    "consume_stock" in operation_line._fields
                    and operation_line.consume_stock
                    and operation_line.stock_cost_updated
                ):
                    operation_total += operation_line.stock_valuation_value
                else:
                    operation_total += operation_line.cost

            project.agriculture_project_invoice_total = company.currency_id.round(invoice_total) if company else invoice_total
            project.agriculture_project_operation_total = company.currency_id.round(operation_total) if company else operation_total

    @api.constrains("agriculture_asset_category_id", "company_id")
    def _check_agriculture_asset_category_company(self):
        for project in self:
            category = project.agriculture_asset_category_id
            if category and project.company_id and category.company_id != project.company_id:
                raise ValidationError(_("Le modèle d'immobilisation doit appartenir à la société du projet."))

    def action_create_agriculture_asset(self):
        self.ensure_one()
        existing_asset = self.agriculture_asset_id
        if existing_asset:
            return {
                "type": "ir.actions.act_window",
                "name": _("Immobilisation du projet"),
                "res_model": "account.asset.asset",
                "view_mode": "form",
                "res_id": existing_asset.id,
                "target": "current",
            }
        if self.agriculture_investment_state == "completed":
            raise UserError(_("Ce projet est déjà achevé, mais aucune immobilisation n'est liée. Contactez votre administrateur."))
        if not self.company_id:
            raise UserError(_("Définissez une société sur le projet avant de créer l'immobilisation."))
        if not self.agriculture_asset_category_id:
            raise UserError(_("Sélectionnez un modèle d'immobilisation."))
        if self.agriculture_investment_actual_cost <= 0:
            raise UserError(_("Saisissez un coût final immobilisable strictement positif."))

        category = self.agriculture_asset_category_id
        if category.company_id != self.company_id:
            raise UserError(_("Le modèle d'immobilisation appartient à une autre société."))
        category_values = self.env["account.asset.asset"].onchange_category_id_values(category.id)
        vals = dict(category_values.get("value", {}))
        vals.update({
            "name": self.name,
            "code": self.name,
            "category_id": category.id,
            "value": self.agriculture_investment_actual_cost,
            "company_id": self.company_id.id,
            "currency_id": self.company_id.currency_id.id,
            "date": fields.Date.context_today(self),
            "type": "purchase",
            "agriculture_project_id": self.id,
            "agriculture_origin": self.agriculture_asset_origin,
            "agriculture_scope": "farm" if self.agriculture_farm_id else "none",
            "agriculture_farm_id": self.agriculture_farm_id.id or False,
            "agriculture_site_id": False,
            "agriculture_invoice_line_id": False,
        })
        required_category_fields = (
            "account_asset_id", "account_depreciation_id",
            "account_depreciation_expense_id", "journal_id",
        )
        missing = [name for name in required_category_fields if not vals.get(name)]
        if missing:
            raise UserError(_(
                "Le modèle d'immobilisation doit définir les comptes et le journal requis avant la création. Champs manquants : %s",
                ", ".join(missing),
            ))

        asset = self.env["account.asset.asset"].create(vals)
        self.write({"agriculture_investment_state": "completed"})
        self.message_post(body=_("Projet achevé. L'immobilisation « %s » a été créée en brouillon.", asset.display_name))
        asset.message_post(body=_("Immobilisation créée à partir du projet « %s ». Vérifiez la fiche puis validez-la pour démarrer les amortissements.", self.display_name))
        return {
            "type": "ir.actions.act_window",
            "name": _("Immobilisation créée"),
            "res_model": "account.asset.asset",
            "view_mode": "form",
            "res_id": asset.id,
            "target": "current",
        }
