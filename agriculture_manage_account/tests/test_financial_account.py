from odoo.tests.common import TransactionCase


class TestAgricultureFinancialAccounts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.currency = cls.company.currency_id
        cls.cash = cls.env["agriculture.farm.financial.account"].create({
            "name": "Caisse de test", "code": "TEST-CASH",
            "company_id": cls.company.id, "currency_id": cls.currency.id,
            "opening_balance": 1000.0,
        })
        cls.bank = cls.env["agriculture.farm.financial.account"].create({
            "name": "Banque de test", "code": "TEST-BANK", "account_type": "bank",
            "company_id": cls.company.id, "currency_id": cls.currency.id,
            "opening_balance": 500.0,
        })
        cls.partner = cls.env["res.partner"].create({"name": "Partenaire test"})
        cls.product = cls.env["product.product"].create({
            "name": "Service test",
            "type": "service",
            "list_price": 200.0,
            "supplier_taxes_id": [(5, 0, 0)],
            "taxes_id": [(5, 0, 0)],
        })

    def test_expense_payment_reduces_account_balance(self):
        transaction = self.env["agriculture.farm.financial.transaction"].create({
            "name": "Achat carburant", "transaction_type": "expense",
            "category": "fuel", "company_id": self.company.id,
            "currency_id": self.currency.id, "amount": 200.0,
            "account_id": self.cash.id,
            "partner_id": self.partner.id,
            "product_id": self.product.id,
        })
        transaction.action_post()
        # Register payment via native invoice
        move = transaction.account_move_id
        register = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=move.ids
        ).create({"amount": 75.0})
        register.action_create_payments()
        self.assertEqual(transaction.payment_state, "partial")
        self.assertEqual(transaction.residual_amount, 125.0)

    def test_internal_transfer_moves_balance_between_accounts(self):
        transaction = self.env["agriculture.farm.financial.transaction"].create({
            "name": "Virement caisse vers banque", "transaction_type": "transfer",
            "category": "transfer", "company_id": self.company.id,
            "currency_id": self.currency.id, "amount": 100.0,
            "account_id": self.cash.id, "destination_account_id": self.bank.id,
        })
        transaction.action_post()
        self.assertEqual(self.cash.balance, 900.0)
        self.assertEqual(self.bank.balance, 600.0)
