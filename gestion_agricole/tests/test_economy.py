# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestEconomy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme éco A", "code": "ECA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme éco B", "code": "ECB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle A", "code": "PA", "farm_id": cls.farm_a.id, "area": 10.0}
        )
        cls.cat_expense = cls.env["gest_agri.economic.category"].create(
            {"name": "Semences", "code": "SEM", "nature": "expense", "company_id": cls.company.id}
        )
        cls.cat_revenue = cls.env["gest_agri.economic.category"].create(
            {"name": "Vente blé", "code": "VBL", "nature": "revenue", "company_id": cls.company.id}
        )

    def _create_expense(self, **kwargs):
        vals = {
            "farm_id": self.farm_a.id,
            "category_id": self.cat_expense.id,
            "expense_date": date(2026, 7, 1),
            "amount": 100.0,
        }
        vals.update(kwargs)
        return self.env["gest_agri.economic.expense"].create(vals)

    def _create_revenue(self, **kwargs):
        vals = {
            "farm_id": self.farm_a.id,
            "category_id": self.cat_revenue.id,
            "revenue_date": date(2026, 7, 1),
            "amount": 200.0,
        }
        vals.update(kwargs)
        return self.env["gest_agri.economic.revenue"].create(vals)

    # ------------------------------------------------------------------
    # Catégories
    # ------------------------------------------------------------------
    def test_category_creation(self):
        cat = self.env["gest_agri.economic.category"].create(
            {"name": "Engrais", "code": "ENG", "nature": "expense", "company_id": self.company.id}
        )
        self.assertTrue(cat.id)

    def test_category_nature_coherence(self):
        with self.assertRaises((ValidationError, ValueError)):
            self.env["gest_agri.economic.category"].create(
                {"name": "Bad", "code": "BAD", "nature": "invalid", "company_id": self.company.id}
            )

    # ------------------------------------------------------------------
    # Dépenses
    # ------------------------------------------------------------------
    def test_expense_creation(self):
        exp = self._create_expense()
        self.assertTrue(exp.id)
        self.assertTrue(exp.name.startswith("DEP/"))

    def test_expense_category_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.economic.expense"].create(
                {"farm_id": self.farm_a.id, "expense_date": date(2026, 7, 1), "amount": 50.0}
            )

    def test_expense_amount_positive(self):
        with self.assertRaises(ValidationError):
            self._create_expense(amount=-10.0)

    def test_expense_category_nature(self):
        with self.assertRaises(ValidationError):
            self._create_expense(category_id=self.cat_revenue.id)

    def test_expense_plot_coherence(self):
        other_plot = self.env["gest_agri.plot"].create(
            {"name": "P2", "code": "P2", "farm_id": self.farm_b.id, "area": 5.0}
        )
        with self.assertRaises(ValidationError):
            self._create_expense(plot_id=other_plot.id)

    def test_expense_site_coherence(self):
        other_site = self.env["gest_agri.site"].create(
            {"name": "S2", "code": "S2", "farm_id": self.farm_b.id}
        )
        with self.assertRaises(ValidationError):
            self._create_expense(site_id=other_site.id)

    def test_expense_unit_price(self):
        exp = self._create_expense(amount=100.0, quantity=5.0)
        self.assertAlmostEqual(exp.unit_price, 20.0)

    def test_expense_farm_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.economic.expense"].create(
                {"category_id": self.cat_expense.id, "expense_date": date(2026, 7, 1), "amount": 50.0}
            )

    # ------------------------------------------------------------------
    # Recettes
    # ------------------------------------------------------------------
    def test_revenue_creation(self):
        rev = self._create_revenue()
        self.assertTrue(rev.id)
        self.assertTrue(rev.name.startswith("REC/"))

    def test_revenue_category_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.economic.revenue"].create(
                {"farm_id": self.farm_a.id, "revenue_date": date(2026, 7, 1), "amount": 50.0}
            )

    def test_revenue_amount_positive(self):
        with self.assertRaises(ValidationError):
            self._create_revenue(amount=-10.0)

    def test_revenue_category_nature(self):
        with self.assertRaises(ValidationError):
            self._create_revenue(category_id=self.cat_expense.id)

    def test_revenue_plot_coherence(self):
        other_plot = self.env["gest_agri.plot"].create(
            {"name": "P3", "code": "P3", "farm_id": self.farm_b.id, "area": 5.0}
        )
        with self.assertRaises(ValidationError):
            self._create_revenue(plot_id=other_plot.id)

    def test_revenue_unit_price(self):
        rev = self._create_revenue(amount=200.0, quantity=4.0)
        self.assertAlmostEqual(rev.unit_price, 50.0)

    def test_revenue_harvest_coherence(self):
        plot = self.plot_a
        cycle = self.env["gest_agri.crop.cycle"].create(
            {"plot_id": plot.id, "crop_type_id": self.env["gest_agri.crop.type"].create({"name": "Blé", "code": "BLE", "company_id": self.company.id}).id, "date_start": date(2026, 2, 1)}
        )
        harvest = self.env["gest_agri.crop.harvest"].create(
            {"cycle_id": cycle.id, "harvest_date": date(2026, 7, 15), "quantity": 1000.0, "uom_id": self.env.ref("uom.product_uom_kgm").id, "harvested_area": 2.0}
        )
        rev = self._create_revenue(harvest_id=harvest.id, farm_id=self.farm_a.id)
        self.assertEqual(rev.harvest_id, harvest)

    # ------------------------------------------------------------------
    # Isolation
    # ------------------------------------------------------------------
    def test_expense_farm_isolation(self):
        exp = self._create_expense()
        self.assertEqual(exp.farm_id, self.farm_a)

    def test_parse_and_install(self):
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "gestion_agricole")]))

    # ------------------------------------------------------------------
    # Security (basic)
    # ------------------------------------------------------------------
    def test_category_unique_code(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.economic.category"].create(
                {"name": "Dup", "code": "SEM", "nature": "expense", "company_id": self.company.id}
            )

    # ------------------------------------------------------------------
    # Coûts de production (agrégats sur le cycle)
    # ------------------------------------------------------------------
    def test_expense_linked_to_cycle(self):
        plot = self.plot_a
        cycle = self.env["gest_agri.crop.cycle"].create(
            {"plot_id": plot.id, "crop_type_id": self.env["gest_agri.crop.type"].create({"name": "Blé", "code": "BLE", "company_id": self.company.id}).id, "date_start": date(2026, 2, 1)}
        )
        exp = self._create_expense(cycle_id=cycle.id, amount=50.0)
        cycle.invalidate_recordset()
        self.assertEqual(cycle.expense_count, 1)
        self.assertAlmostEqual(cycle.total_expense, 50.0)

    def test_revenue_linked_to_cycle(self):
        plot = self.plot_a
        cycle = self.env["gest_agri.crop.cycle"].create(
            {"plot_id": plot.id, "crop_type_id": self.env["gest_agri.crop.type"].create({"name": "Blé", "code": "BLE", "company_id": self.company.id}).id, "date_start": date(2026, 2, 1)}
        )
        rev = self._create_revenue(cycle_id=cycle.id, amount=120.0)
        cycle.invalidate_recordset()
        self.assertEqual(cycle.revenue_count, 1)
        self.assertAlmostEqual(cycle.total_revenue, 120.0)

    def test_economic_balance_on_cycle(self):
        plot = self.plot_a
        cycle = self.env["gest_agri.crop.cycle"].create(
            {"plot_id": plot.id, "crop_type_id": self.env["gest_agri.crop.type"].create({"name": "Blé", "code": "BLE", "company_id": self.company.id}).id, "date_start": date(2026, 2, 1)}
        )
        self._create_expense(cycle_id=cycle.id, amount=80.0)
        self._create_revenue(cycle_id=cycle.id, amount=200.0)
        cycle.invalidate_recordset()
        self.assertAlmostEqual(cycle.economic_balance, 120.0)

    def test_expense_linked_to_campaign(self):
        campaign = self.env["gest_agri.crop.campaign"].create(
            {"name": "Campagne éco", "farm_id": self.farm_a.id, "date_start": date(2026, 1, 1), "date_end": date(2026, 12, 31)}
        )
        exp = self._create_expense(campaign_id=campaign.id, amount=60.0)
        self.assertEqual(exp.campaign_id, campaign)

    def test_revenue_linked_to_harvest(self):
        plot = self.plot_a
        cycle = self.env["gest_agri.crop.cycle"].create(
            {"plot_id": plot.id, "crop_type_id": self.env["gest_agri.crop.type"].create({"name": "Blé", "code": "BLE", "company_id": self.company.id}).id, "date_start": date(2026, 2, 1)}
        )
        harvest = self.env["gest_agri.crop.harvest"].create(
            {"cycle_id": cycle.id, "harvest_date": date(2026, 7, 15), "quantity": 1000.0, "uom_id": self.env.ref("uom.product_uom_kgm").id, "harvested_area": 2.0}
        )
        rev = self._create_revenue(harvest_id=harvest.id, farm_id=self.farm_a.id, amount=500.0)
        self.assertEqual(rev.harvest_id, harvest)

    def test_expense_site_coherence_ok(self):
        site = self.env["gest_agri.site"].create({"name": "Site A", "code": "SA", "farm_id": self.farm_a.id})
        exp = self._create_expense(site_id=site.id)
        self.assertEqual(exp.site_id, site)

    def test_revenue_site_coherence_ok(self):
        site = self.env["gest_agri.site"].create({"name": "Site A", "code": "SA", "farm_id": self.farm_a.id})
        rev = self._create_revenue(site_id=site.id)
        self.assertEqual(rev.site_id, site)

    def test_expense_intervention_coherence_ok(self):
        cycle = self.env["gest_agri.crop.cycle"].create(
            {"plot_id": self.plot_a.id, "crop_type_id": self.env["gest_agri.crop.type"].create({"name": "Blé", "code": "BLE", "company_id": self.company.id}).id, "date_start": date(2026, 2, 1)}
        )
        intervention = self.env["gest_agri.crop.intervention"].create(
            {"name": "Labour", "crop_cycle_id": cycle.id, "operation_type_id": self.env["gest_agri.operation.type"].create({"name": "Labour", "code": "LAB", "company_id": self.company.id}).id, "date_planned": date(2026, 3, 15)}
        )
        exp = self._create_expense(intervention_id=intervention.id, farm_id=self.farm_a.id)
        self.assertEqual(exp.intervention_id, intervention)

    def test_expense_multiple_on_same_farm(self):
        e1 = self._create_expense(amount=10.0)
        e2 = self._create_expense(amount=20.0)
        self.assertNotEqual(e1.id, e2.id)

    def test_revenue_multiple_on_same_farm(self):
        r1 = self._create_revenue(amount=10.0)
        r2 = self._create_revenue(amount=20.0)
        self.assertNotEqual(r1.id, r2.id)

    def test_expense_zero_amount_allowed(self):
        # montant 0 ne déclenche pas la contrainte (seuls les négatifs sont refusés)
        exp = self._create_expense(amount=0.0)
        self.assertEqual(exp.amount, 0.0)

    def test_revenue_zero_amount_allowed(self):
        rev = self._create_revenue(amount=0.0)
        self.assertEqual(rev.amount, 0.0)

    def test_expense_archive(self):
        exp = self._create_expense()
        exp.write({"active": False})
        self.assertFalse(exp.active)

    def test_revenue_archive(self):
        rev = self._create_revenue()
        rev.write({"active": False})
        self.assertFalse(rev.active)

    def test_category_code_unique(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.economic.category"].create(
                {"name": "Dup", "code": "SEM", "nature": "expense", "company_id": self.company.id}
            )

    def test_expense_currency_default(self):
        exp = self._create_expense()
        self.assertEqual(exp.currency_id, self.company.currency_id)

    def test_revenue_currency_default(self):
        rev = self._create_revenue()
        self.assertEqual(rev.currency_id, self.company.currency_id)
