# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestProcurement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")

        cls.user_a = cls._create_user("proc_user_a", [cls.base_user, cls.group_user])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme proc A", "code": "PA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme proc B", "code": "PB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create({"name": "Site PA", "code": "SPA", "farm_id": cls.farm_a.id})
        cls.species = cls.env["gest_agri.livestock.species"].create(
            {"name": "Bovin", "code": "BOVP", "company_id": cls.company.id}
        )
        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.product = cls.env["product.product"].create(
            {"name": "Engrais NPK", "type": "consu", "uom_id": cls.uom_kg.id, "company_id": cls.company.id}
        )
        cls.category = cls.env["gest_agri.input.category"].create(
            {"name": "Engrais", "code": "ENG", "company_id": cls.company.id}
        )

    @classmethod
    def _create_user(cls, login, groups):
        group_ids = [g.id if hasattr(g, "id") else int(g) for g in groups]
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create({
                "name": login, "login": login, "email": f"{login}@example.com",
                "company_id": cls.company.id, "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, group_ids)],
            })
        )

    def _new_request(self, **kwargs):
        vals = {"farm_id": self.farm_a.id, "request_date": date(2026, 5, 1)}
        vals.update(kwargs)
        req = self.env["gest_agri.procurement.request"].create(vals)
        if not req.line_ids:
            self.env["gest_agri.procurement.request.line"].create(
                {"request_id": req.id, "product_id": self.product.id, "quantity": 10.0, "product_uom_id": self.uom_kg.id}
            )
        return req

    # ------------------------------------------------------------------
    # Demandes d'approvisionnement
    # ------------------------------------------------------------------
    def test_procurement_request_creation(self):
        r = self._new_request()
        self.assertTrue(r.name.startswith("DAP/"))
        self.assertEqual(r.state, "draft")
        self.assertEqual(r.farm_id, self.farm_a)

    def test_procurement_request_submit(self):
        r = self._new_request()
        r.action_submit()
        self.assertEqual(r.state, "submitted")

    def test_procurement_request_approve(self):
        r = self._new_request()
        r.action_submit()
        r.action_approve()
        self.assertEqual(r.state, "approved")

    def test_procurement_request_order(self):
        r = self._new_request()
        r.action_submit()
        r.action_approve()
        r.action_order()
        self.assertEqual(r.state, "ordered")

    def test_procurement_request_done(self):
        r = self._new_request()
        r.action_submit()
        r.action_approve()
        r.action_order()
        r.action_done()
        self.assertEqual(r.state, "done")

    def test_procurement_request_cancel(self):
        r = self._new_request()
        r.action_cancel()
        self.assertEqual(r.state, "cancelled")

    def test_procurement_request_submit_requires_lines(self):
        r = self.env["gest_agri.procurement.request"].create({"farm_id": self.farm_a.id, "request_date": date(2026, 5, 1)})
        with self.assertRaises(UserError):
            r.action_submit()

    def test_procurement_request_direct_state_write_forbidden(self):
        r = self._new_request()
        with self.assertRaises(AccessError):
            r.write({"state": "submitted"})

    def test_procurement_request_unlink_draft_only(self):
        r = self._new_request()
        r.action_submit()
        with self.assertRaises(UserError):
            r.unlink()

    def test_procurement_request_dates_coherence(self):
        with self.assertRaises(ValidationError):
            self._new_request(needed_date=date(2026, 4, 1))

    def test_procurement_request_site_farm_coherence(self):
        site_b = self.env["gest_agri.site"].create({"name": "Site PB", "code": "SPB", "farm_id": self.farm_b.id})
        with self.assertRaises(ValidationError):
            self._new_request(site_id=site_b.id)

    def test_procurement_request_negative_quantity_refused(self):
        r = self._new_request()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.procurement.request.line"].create(
                {"request_id": r.id, "product_id": self.product.id, "quantity": -1.0, "product_uom_id": self.uom_kg.id}
            )

    # ------------------------------------------------------------------
    # Consommations d'intrants
    # ------------------------------------------------------------------
    def test_input_consumption_creation(self):
        c = self.env["gest_agri.input.consumption"].create(
            {"farm_id": self.farm_a.id, "consumption_date": date(2026, 5, 10)}
        )
        self.assertTrue(c.name.startswith("CON/"))
        self.assertEqual(c.state, "draft")
        self.assertEqual(c.farm_id, self.farm_a)

    def test_input_consumption_validate(self):
        c = self.env["gest_agri.input.consumption"].create(
            {"farm_id": self.farm_a.id, "consumption_date": date(2026, 5, 10)}
        )
        self.env["gest_agri.input.consumption.line"].create(
            {"consumption_id": c.id, "product_id": self.product.id, "quantity": 5.0, "product_uom_id": self.uom_kg.id}
        )
        c.action_validate()
        self.assertEqual(c.state, "validated")

    def test_input_consumption_validate_requires_lines(self):
        c = self.env["gest_agri.input.consumption"].create(
            {"farm_id": self.farm_a.id, "consumption_date": date(2026, 5, 10)}
        )
        with self.assertRaises(UserError):
            c.action_validate()

    def test_input_consumption_cancel(self):
        c = self.env["gest_agri.input.consumption"].create(
            {"farm_id": self.farm_a.id, "consumption_date": date(2026, 5, 10)}
        )
        c.action_cancel()
        self.assertEqual(c.state, "cancelled")

    def test_input_consumption_direct_state_write_forbidden(self):
        c = self.env["gest_agri.input.consumption"].create(
            {"farm_id": self.farm_a.id, "consumption_date": date(2026, 5, 10)}
        )
        with self.assertRaises(AccessError):
            c.write({"state": "validated"})

    def test_input_consumption_unlink_draft_only(self):
        c = self.env["gest_agri.input.consumption"].create(
            {"farm_id": self.farm_a.id, "consumption_date": date(2026, 5, 10)}
        )
        self.env["gest_agri.input.consumption.line"].create(
            {"consumption_id": c.id, "product_id": self.product.id, "quantity": 5.0, "product_uom_id": self.uom_kg.id}
        )
        c.action_validate()
        with self.assertRaises(UserError):
            c.unlink()

    def test_input_consumption_site_farm_coherence(self):
        site_b = self.env["gest_agri.site"].create({"name": "Site PB", "code": "SPB", "farm_id": self.farm_b.id})
        with self.assertRaises(ValidationError):
            self.env["gest_agri.input.consumption"].create(
                {"farm_id": self.farm_a.id, "site_id": site_b.id, "consumption_date": date(2026, 5, 10)}
            )

    def test_input_consumption_plot_farm_coherence(self):
        plot_b = self.env["gest_agri.plot"].create({"name": "Parcelle PB", "code": "PPB", "farm_id": self.farm_b.id})
        with self.assertRaises(ValidationError):
            self.env["gest_agri.input.consumption"].create(
                {"farm_id": self.farm_a.id, "plot_id": plot_b.id, "consumption_date": date(2026, 5, 10)}
            )

    def test_input_consumption_line_negative_quantity_refused(self):
        c = self.env["gest_agri.input.consumption"].create(
            {"farm_id": self.farm_a.id, "consumption_date": date(2026, 5, 10)}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.input.consumption.line"].create(
                {"consumption_id": c.id, "product_id": self.product.id, "quantity": -1.0, "product_uom_id": self.uom_kg.id}
            )

    # ------------------------------------------------------------------
    # Catégories d'intrants
    # ------------------------------------------------------------------
    def test_input_category_creation(self):
        cat = self.env["gest_agri.input.category"].create(
            {"name": "Semences", "code": "SEM", "company_id": self.company.id}
        )
        self.assertTrue(cat.id)
        self.assertEqual(cat.name, "Semences")

    def test_input_category_unique_code(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.input.category"].create(
                {"name": "Autre engrais", "code": "ENG", "company_id": self.company.id}
            )

    # ------------------------------------------------------------------
    # Isolation
    # ------------------------------------------------------------------
    def test_procurement_request_isolation(self):
        r = self._new_request()
        visible = self.env["gest_agri.procurement.request"].with_user(self.user_a).search([])
        self.assertNotIn(r, visible)

    def test_input_consumption_isolation(self):
        c = self.env["gest_agri.input.consumption"].create(
            {"farm_id": self.farm_a.id, "consumption_date": date(2026, 5, 10)}
        )
        visible = self.env["gest_agri.input.consumption"].with_user(self.user_a).search([])
        self.assertNotIn(c, visible)