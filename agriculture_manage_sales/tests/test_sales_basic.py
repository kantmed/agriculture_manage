# -*- coding: utf-8 -*-
"""Tests for agriculture_manage_sales."""
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSalesBasic(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "Client test vente"})
        cls.farm = cls.env["agriculture.farm"].create({
            "name": "Exploitation test vente",
            "total_area": 10,
        })
        crop_type = cls.env.ref("agriculture_manage_crop.crop_type_cereal")
        cls.crop = cls.env["agriculture.farm.crop"].create({
            "name": "Culture vente test",
            "crop_type_id": crop_type.id,
            "abbreviation": "VTE",
        })
        cls.campaign = cls.env["agriculture.farm.crop.campaign"].create({
            "name": "Campagne vente test",
            "farm_id": cls.farm.id,
            "crop_id": cls.crop.id,
        })

    def test_sale_order_create_with_campaign(self):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "agriculture_campaign_id": self.campaign.id,
        })
        self.assertEqual(order.agriculture_farm_id, self.farm)

    def test_sale_order_campaign_company_constraint(self):
        other_company = self.env["res.company"].create({"name": "Autre société"})
        with self.assertRaises(ValidationError):
            self.env["sale.order"].create({
                "partner_id": self.partner.id,
                "company_id": other_company.id,
                "agriculture_campaign_id": self.campaign.id,
            })