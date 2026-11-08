from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAgricultureAssetAssignment(TransactionCase):
    def test_asset_module_fields_available(self):
        asset_fields = self.env["account.asset.asset"]._fields
        self.assertIn("agriculture_scope", asset_fields)
        self.assertIn("agriculture_farm_id", asset_fields)
        self.assertIn("agriculture_site_id", asset_fields)
        self.assertIn("agriculture_allocation_ids", asset_fields)
        self.assertIn("analytic_account_id", self.env["agriculture.farm"]._fields)

    def test_allocation_requires_company_scope(self):
        # A minimal assertion that the extension's scope selection is installed.
        selection = dict(self.env["account.asset.asset"]._fields["agriculture_scope"].selection)
        self.assertIn("company", selection)
        self.assertIn("farm", selection)
        self.assertIn("site", selection)
