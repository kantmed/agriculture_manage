# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestModuleInstall(TransactionCase):
    def test_module_present(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "gestion_agricole")], limit=1
        )
        self.assertTrue(module, "Le module gestion_agricole doit être présent")

