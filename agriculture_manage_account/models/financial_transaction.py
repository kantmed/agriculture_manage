from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AgricultureFinancialTransaction(models.Model):
    _name = "agriculture.farm.financial.transaction"
    _description = "Mouvement financier agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Libellé", required=True, tracking=True)
    reference = fields.Char(string="Référence", readonly=True, copy=False, default="Nouveau")
    transaction_type = fields.Selection([
        ("income", "Recette"), ("expense", "Dépense"), ("transfer", "Virement interne"),
    ], string="Type de mouvement", required=True, default="expense", tracking=True, index=True)
    category = fields.Selection([
        ("crop_sales", "Vente de récolte"), ("livestock_sales", "Vente de bétail"),
        ("subsidy", "Subvention"), ("other_income", "Autre recette"),
        ("seeds", "Semences"), ("fertilizer", "Engrais"), ("phytosanitary", "Produits phytosanitaires"),
        ("fuel", "Carburant"), ("water_energy", "Eau et énergie"),
        ("labor", "Main-d'œuvre"), ("equipment", "Matériel et entretien"),
        ("rent", "Location"), ("tax", "Taxes et impôts"), ("other_expense", "Autre dépense"),
        ("transfer", "Virement"),
    ], string="Catégorie", required=True, default="other_expense", tracking=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Devise", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    amount = fields.Monetary(string="Montant", currency_field="currency_id", required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Client / Fournisseur", tracking=True)
    product_id = fields.Many2one(
        "product.product", string="Article / Service comptable",
        check_company=True,
        help="Article ou service utilisé pour générer la ligne de facture ou de facture fournisseur dans Odoo Comptabilité.",
    )
    account_move_id = fields.Many2one(
        "account.move", string="Pièce comptable", readonly=True, copy=False,
        ondelete="restrict", check_company=True, index=True,
    )
    farm_id = fields.Many2one("agriculture.farm", string="Exploitation", index=True)
    campaign_id = fields.Many2one(
        "agriculture.farm.crop.campaign", string="Campagne", ondelete="restrict", index=True,
    )
    plot_id = fields.Many2one("agriculture.farm.plot", string="Parcelle", ondelete="restrict")
    operation_id = fields.Many2one("agriculture.farm.operation", string="Opération agricole", ondelete="restrict")
    harvest_id = fields.Many2one("agriculture.farm.harvest", string="Récolte", ondelete="restrict")
    budget_id = fields.Many2one("agriculture.farm.crop.budget", string="Budget agricole", ondelete="restrict")
    account_id = fields.Many2one(
        "agriculture.farm.financial.account", string="Compte financier",
        ondelete="restrict", tracking=True,
    )
    destination_account_id = fields.Many2one(
        "agriculture.farm.financial.account", string="Compte destinataire",
        ondelete="restrict",
    )
    payment_ids = fields.One2many(
        "agriculture.farm.financial.payment", "transaction_id", string="Règlements",
    )
    paid_amount = fields.Monetary(
        string="Montant réglé", currency_field="currency_id", compute="_compute_payment_status", store=True,
    )
    residual_amount = fields.Monetary(
        string="Reste à payer", currency_field="currency_id", compute="_compute_payment_status", store=True,
    )
    payment_state = fields.Selection([
        ("not_paid", "Non réglé"), ("in_payment", "Paiement en cours"),
        ("partial", "Partiellement réglé"), ("paid", "Réglé"), ("reversed", "Extourné"),
    ], string="État du règlement", compute="_compute_payment_status", store=True,
    )
    state = fields.Selection([
        ("draft", "Brouillon"), ("posted", "Validé"), ("cancelled", "Annulé"),
    ], string="État", default="draft", required=True, tracking=True, index=True)
    description = fields.Text(string="Description")

    @api.onchange("campaign_id")
    def _onchange_campaign_id(self):
        if self.campaign_id:
            self.farm_id = self.campaign_id.farm_id
            self.company_id = self.campaign_id.company_id
            self.currency_id = self.company_id.currency_id

    @api.onchange("budget_id")
    def _onchange_budget_id(self):
        if self.budget_id:
            self.campaign_id = self.budget_id.campaign_id
            self.farm_id = self.budget_id.farm_id
            self.company_id = self.budget_id.company_id
            self.currency_id = self.budget_id.currency_id

    @api.onchange("transaction_type")
    def _onchange_transaction_type(self):
        defaults = {
            "income": "other_income",
            "expense": "other_expense",
            "transfer": "transfer",
        }
        if self.transaction_type in defaults:
            self.category = defaults[self.transaction_type]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("budget_id") and not vals.get("campaign_id"):
                budget = self.env["agriculture.farm.crop.budget"].browse(vals["budget_id"])
                vals.setdefault("campaign_id", budget.campaign_id.id)
                vals.setdefault("farm_id", budget.farm_id.id)
                vals.setdefault("company_id", budget.company_id.id)
                vals.setdefault("currency_id", budget.currency_id.id)
            if vals.get("campaign_id"):
                campaign = self.env["agriculture.farm.crop.campaign"].browse(vals["campaign_id"])
                vals.setdefault("farm_id", campaign.farm_id.id)
                vals.setdefault("company_id", campaign.company_id.id)
                vals.setdefault("currency_id", campaign.company_id.currency_id.id)
            if vals.get("reference", "Nouveau") == "Nouveau":
                vals["reference"] = self.env["ir.sequence"].next_by_code("agriculture.farm.financial.transaction") or "Nouveau"
        return super().create(vals_list)

    @api.depends(
        "amount", "payment_ids.amount", "payment_ids.state", "currency_id",
        "account_move_id.amount_residual", "account_move_id.amount_total", "account_move_id.payment_state",
    )
    def _compute_payment_status(self):
        for record in self:
            currency = record.currency_id
            if record.account_move_id:
                move = record.account_move_id
                residual = move.amount_residual
                paid = max(move.amount_total - residual, 0.0)
                record.paid_amount = currency.round(paid) if currency else paid
                record.residual_amount = currency.round(residual) if currency else residual
                record.payment_state = move.payment_state if move.payment_state in ("not_paid", "in_payment", "partial", "paid", "reversed") else "not_paid"
                continue
            paid = sum(record.payment_ids.filtered(lambda p: p.state == "posted").mapped("amount"))
            if currency:
                paid = currency.round(paid)
            residual = max((record.amount or 0.0) - paid, 0.0)
            record.paid_amount = paid
            record.residual_amount = currency.round(residual) if currency else residual
            if not paid:
                record.payment_state = "not_paid"
            elif currency and currency.is_zero(residual):
                record.payment_state = "paid"
            elif not currency and residual <= 0:
                record.payment_state = "paid"
            else:
                record.payment_state = "partial"

    @api.constrains("amount", "transaction_type", "account_id", "destination_account_id", "company_id", "currency_id", "farm_id", "campaign_id", "plot_id", "operation_id", "harvest_id", "budget_id")
    def _check_consistency(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Le montant doit être strictement positif."))
            if rec.transaction_type == "transfer":
                if not rec.account_id or not rec.destination_account_id:
                    raise ValidationError(_("Un virement nécessite un compte source et un compte destinataire."))
                if rec.account_id == rec.destination_account_id:
                    raise ValidationError(_("Les comptes source et destinataire doivent être différents."))
                if rec.account_id.company_id != rec.company_id or rec.destination_account_id.company_id != rec.company_id:
                    raise ValidationError(_("Les deux comptes du virement doivent appartenir à la société du mouvement."))
            elif rec.account_id:
                if rec.account_id.company_id != rec.company_id:
                    raise ValidationError(_("Le compte financier doit appartenir à la société du mouvement."))
                if rec.account_id.currency_id != rec.currency_id:
                    raise ValidationError(_("La devise du mouvement doit correspondre à celle du compte financier."))
            if rec.transaction_type == "transfer" and rec.account_id and rec.destination_account_id:
                if rec.account_id.currency_id != rec.destination_account_id.currency_id or rec.currency_id != rec.account_id.currency_id:
                    raise ValidationError(_("Les comptes source et destinataire ainsi que le mouvement doivent utiliser la même devise."))
            if rec.farm_id and rec.farm_id.company_id != rec.company_id:
                raise ValidationError(_("L'exploitation doit appartenir à la société du mouvement."))
            if rec.campaign_id and rec.farm_id and rec.campaign_id.farm_id != rec.farm_id:
                raise ValidationError(_("La campagne ne correspond pas à l'exploitation sélectionnée."))
            if rec.plot_id and rec.farm_id and rec.plot_id.farm_id != rec.farm_id:
                raise ValidationError(_("La parcelle ne correspond pas à l'exploitation sélectionnée."))
            if rec.operation_id and rec.campaign_id and rec.operation_id.campaign_id != rec.campaign_id:
                raise ValidationError(_("L'opération ne correspond pas à la campagne sélectionnée."))
            if rec.harvest_id and rec.campaign_id and rec.harvest_id.campaign_id != rec.campaign_id:
                raise ValidationError(_("La récolte ne correspond pas à la campagne sélectionnée."))
            if rec.budget_id and rec.campaign_id and rec.budget_id.campaign_id != rec.campaign_id:
                raise ValidationError(_("Le budget ne correspond pas à la campagne sélectionnée."))
            if rec.budget_id and rec.transaction_type != "expense":
                raise ValidationError(_("Un budget de dépenses ne peut être associé qu'à un mouvement de type dépense."))
            if rec.budget_id and rec.budget_id.company_id != rec.company_id:
                raise ValidationError(_("Le budget doit appartenir à la société du mouvement."))

    def _prepare_account_move_vals(self):
        self.ensure_one()
        if self.transaction_type not in ("income", "expense"):
            raise UserError(_("Seules les recettes et dépenses peuvent générer une facture ou une facture fournisseur."))
        if not self.partner_id:
            raise UserError(_("Sélectionnez un client ou un fournisseur avant de créer la pièce comptable."))
        if not self.product_id:
            raise UserError(_("Sélectionnez un article ou un service comptable."))
        if self.product_id.company_id and self.product_id.company_id != self.company_id:
            raise UserError(_("L'article doit appartenir à la société du mouvement."))
        account_type = "income" if self.transaction_type == "income" else "expense"
        product_accounts = self.product_id.with_company(self.company_id)._get_product_accounts()
        product_account = product_accounts.get(account_type)
        if not product_account:
            raise UserError(_("Aucun compte de produit/dépense n'est configuré sur l'article ou sa catégorie."))
        analytic_accounts = self.env["account.analytic.account"]
        if self.farm_id and self.farm_id.analytic_account_id:
            analytic_accounts |= self.farm_id.analytic_account_id
        if self.campaign_id and self.campaign_id.analytic_account_id:
            analytic_accounts |= self.campaign_id.analytic_account_id
        if self.plot_id and self.plot_id.analytic_account_id:
            analytic_accounts |= self.plot_id.analytic_account_id
        distribution = {}
        if analytic_accounts:
            distribution[",".join(map(str, sorted(analytic_accounts.ids)))] = 100.0
        product_taxes = self.product_id.taxes_id if self.transaction_type == "income" else self.product_id.supplier_taxes_id
        taxes = product_taxes.filtered(lambda tax: tax.company_id == self.company_id)
        return {
            "move_type": "out_invoice" if self.transaction_type == "income" else "in_invoice",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "invoice_date": self.date,
            "ref": self.reference,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product_id.id,
                "name": self.name,
                "quantity": 1.0,
                "price_unit": self.amount,
                "account_id": product_account.id,
                "tax_ids": [(6, 0, taxes.ids)],
                "analytic_distribution": distribution,
            })],
            "agriculture_farm_id": self.farm_id.id,
            "agriculture_campaign_id": self.campaign_id.id,
            "agriculture_plot_id": self.plot_id.id,
            "agriculture_operation_id": self.operation_id.id,
            "agriculture_harvest_id": self.harvest_id.id,
            "agriculture_budget_id": self.budget_id.id,
            "agriculture_financial_transaction_id": self.id,
        }

    def action_post(self):
        for rec in self:
            if rec.state != "draft":
                continue
            if rec.transaction_type == "transfer":
                if rec.payment_ids.filtered(lambda p: p.state == "posted"):
                    raise UserError(_("Un virement interne ne doit pas comporter de règlement séparé."))
                if not rec.account_id or not rec.destination_account_id:
                    raise UserError(_("Sélectionnez les comptes source et destinataire du virement."))
                rec.state = "posted"
                continue
            if not rec.account_move_id:
                move = self.env["account.move"].create(rec._prepare_account_move_vals())
                move.action_post()
                rec.account_move_id = move
            elif rec.account_move_id.state == "draft":
                rec.account_move_id.action_post()
            elif rec.account_move_id.state != "posted":
                raise UserError(_("La pièce comptable liée doit être en brouillon ou validée."))
            rec.state = "posted"
        return True

    def action_cancel(self):
        for rec in self:
            if rec.account_move_id and rec.account_move_id.state == "posted":
                raise UserError(_("Annulez ou extournez d'abord la pièce dans Odoo Comptabilité."))
            if rec.payment_ids.filtered(lambda p: p.state == "posted"):
                raise UserError(_("Annulez d'abord les règlements validés avant d'annuler ce mouvement."))
            rec.state = "cancelled"
        return True

    def action_set_draft(self):
        if self.filtered(lambda rec: rec.payment_ids.filtered(lambda p: p.state == "posted")):
            raise UserError(_("Impossible de remettre en brouillon un mouvement ayant des règlements validés. Annulez d'abord les règlements."))
        self.write({"state": "draft"})
        return True

    def action_register_payment(self):
        self.ensure_one()
        if self.state != "posted" or self.transaction_type == "transfer":
            raise UserError(_("Le règlement est disponible uniquement pour une recette ou une dépense validée."))
        if self.currency_id.is_zero(self.residual_amount):
            raise UserError(_("Ce mouvement est déjà entièrement réglé."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Enregistrer un règlement"),
            "res_model": "agriculture.farm.financial.payment",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_transaction_id": self.id,
                "default_account_id": self.account_id.id,
                "default_amount": self.residual_amount,
                "default_payment_date": fields.Date.context_today(self),
            },
        }


    def action_view_account_move(self):
        self.ensure_one()
        if not self.account_move_id:
            raise UserError(_("Aucune pièce comptable n'est encore liée à ce mouvement."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Pièce comptable"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.account_move_id.id,
            "target": "current",
        }


class AgricultureFinancialPayment(models.Model):
    _name = "agriculture.farm.financial.payment"
    _description = "Règlement financier agricole"
    _order = "payment_date desc, id desc"

    name = fields.Char(string="Référence", readonly=True, copy=False, default="Nouveau")
    transaction_id = fields.Many2one(
        "agriculture.farm.financial.transaction", string="Mouvement", required=True,
        ondelete="cascade", index=True,
    )
    payment_date = fields.Date(string="Date de règlement", required=True, default=fields.Date.context_today)
    account_id = fields.Many2one(
        "agriculture.farm.financial.account", string="Compte financier", required=True,
        ondelete="restrict",
    )
    currency_id = fields.Many2one("res.currency", related="transaction_id.currency_id", readonly=True)
    amount = fields.Monetary(string="Montant réglé", currency_field="currency_id", required=True)
    payment_method = fields.Selection([
        ("cash", "Espèces"), ("bank", "Virement bancaire"), ("check", "Chèque"), ("other", "Autre"),
    ], string="Mode de règlement", required=True, default="cash")
    state = fields.Selection([
        ("draft", "Brouillon"), ("posted", "Validé"), ("cancelled", "Annulé"),
    ], string="État", default="draft", required=True)
    note = fields.Char(string="Note")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code("agriculture.farm.financial.payment") or "Nouveau"
        return super().create(vals_list)

    @api.constrains("amount", "transaction_id", "account_id")
    def _check_payment(self):
        for payment in self:
            if payment.amount <= 0:
                raise ValidationError(_("Le montant du règlement doit être strictement positif."))
            transaction = payment.transaction_id
            if transaction.transaction_type == "transfer":
                raise ValidationError(_("Les virements internes ne nécessitent pas de règlement séparé."))
            if transaction.account_move_id:
                raise ValidationError(_("Les règlements de ce mouvement doivent être enregistrés depuis la pièce native Odoo Comptabilité."))
            if payment.account_id.company_id != transaction.company_id:
                raise ValidationError(_("Le compte de règlement doit appartenir à la société du mouvement."))
            if payment.account_id.currency_id != transaction.currency_id:
                raise ValidationError(_("La devise du compte doit correspondre à celle du mouvement."))
            other_paid = sum(transaction.payment_ids.filtered(
                lambda p: p.state == "posted" and p.id != payment.id
            ).mapped("amount"))
            if transaction.currency_id.compare_amounts(other_paid + payment.amount, transaction.amount) > 0:
                raise ValidationError(_("Le total des règlements ne peut pas dépasser le montant du mouvement."))

    def action_post(self):
        for payment in self:
            if payment.transaction_id.state != "posted":
                raise UserError(_("Validez d'abord le mouvement financier."))
            if payment.state != "draft":
                continue
            payment._check_payment()
            payment.state = "posted"
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True
