from odoo.tests.common import TransactionCase


class TestWebsiteBasic(TransactionCase):
    def test_portal_access_create(self):
        access = self.env["agriculture.portal.access"].create({
            "name": "Accès test",
            "user_id": self.env.user.id,
        })
        self.assertEqual(access.name, "Accès test")