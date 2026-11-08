from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAgricultureAnalyticAccounting(TransactionCase):
    def test_analytic_dimensions_are_available(self):
        """The three agricultural dimensions expose native analytic account links."""
        for model_name in ("agriculture.farm", "agriculture.farm.crop.campaign", "agriculture.farm.plot"):
            self.assertIn("analytic_account_id", self.env[model_name]._fields)

    def test_stock_move_has_agriculture_operation_link(self):
        self.assertIn("agriculture_operation_line_id", self.env["stock.move"]._fields)
