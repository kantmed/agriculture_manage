# -*- coding: utf-8 -*-
"""Tests for agriculture_manage_analysis."""
import uuid

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAgricultureBudget(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.farm = cls.env["agriculture.farm"].create({
            "name": "Exploitation test budget",
            "total_area": 10,
        })
        crop_type = cls.env.ref("agriculture_manage_crop.crop_type_cereal")
        cls.crop = cls.env["agriculture.farm.crop"].create({
            "name": "Culture budget test",
            "crop_type_id": crop_type.id,
            "abbreviation": f"B{uuid.uuid4().hex[:12]}",
        })
        cls.campaign = cls.env["agriculture.farm.crop.campaign"].create({
            "name": "Campagne budget test",
            "farm_id": cls.farm.id,
            "crop_id": cls.crop.id,
        })

    def test_budget_create(self):
        budget = self.env["agriculture.farm.crop.budget"].create({
            "name": "Budget test",
            "campaign_id": self.campaign.id,
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
        })
        self.assertEqual(budget.state, "draft")
        self.assertTrue(budget.code.startswith("BUD/"))

    def test_budget_dates_invalid(self):
        with self.assertRaises(ValidationError):
            self.env["agriculture.farm.crop.budget"].create({
                "name": "Budget dates invalides",
                "campaign_id": self.campaign.id,
                "date_start": "2026-12-31",
                "date_end": "2026-01-01",
            })

    def test_budget_confirm_and_close(self):
        budget = self.env["agriculture.farm.crop.budget"].create({
            "name": "Budget confirm",
            "campaign_id": self.campaign.id,
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
            "line_ids": [(0, 0, {"name": "Ligne test", "planned_amount": 100.0, "category": "labor"})],
        })
        budget.action_confirm()
        self.assertEqual(budget.state, "confirmed")
        budget.action_close()
        self.assertEqual(budget.state, "closed")