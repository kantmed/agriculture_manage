# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

import psycopg2

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestEquipment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")

        cls.user_a = cls._create_user("eq_user_a", [cls.base_user, cls.group_user])
        cls.user_b = cls._create_user("eq_user_b", [cls.base_user, cls.group_user])
        cls.manager = cls._create_user("eq_manager", [cls.base_user, cls.group_manager])
        cls.admin = cls._create_user("eq_admin", [cls.base_user, cls.group_admin])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme équipement A", "code": "EQA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme équipement B", "code": "EQB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create(
            {"name": "Site A", "code": "SA", "farm_id": cls.farm_a.id}
        )
        cls.equipment_type = cls.env["gest_agri.equipment.type"].create(
            {"name": "Tracteur", "code": "TRAC", "company_id": cls.company.id}
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle A", "code": "PA", "farm_id": cls.farm_a.id, "area": 10.0}
        )

        cls.equipment = cls.env["gest_agri.equipment"].create(
            {
                "name": "Tracteur 1",
                "equipment_type_id": cls.equipment_type.id,
                "farm_id": cls.farm_a.id,
                "site_id": cls.site_a.id,
                "hour_meter": 100.0,
                "odometer": 5000.0,
            }
        )

    @classmethod
    def _create_user(cls, login, groups):
        group_ids = [g.id if hasattr(g, "id") else int(g) for g in groups]
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "company_id": cls.company.id,
                    "company_ids": [(6, 0, [cls.company.id])],
                    "group_ids": [(6, 0, group_ids)],
                }
            )
        )

    def _create_equipment(self, **kwargs):
        vals = {
            "name": "Équipement test",
            "equipment_type_id": self.equipment_type.id,
            "farm_id": self.farm_a.id,
        }
        vals.update(kwargs)
        return self.env["gest_agri.equipment"].create(vals)

    def _create_usage(self, equipment=None, **kwargs):
        vals = {
            "equipment_id": (equipment or self.equipment).id,
            "start_datetime": datetime(2026, 7, 1, 8, 0),
            "end_datetime": datetime(2026, 7, 1, 12, 0),
        }
        vals.update(kwargs)
        return self.env["gest_agri.equipment.usage"].create(vals)

    def _create_maintenance(self, equipment=None, **kwargs):
        vals = {
            "equipment_id": (equipment or self.equipment).id,
            "maintenance_type": "preventive",
            "planned_date": date(2026, 7, 15),
        }
        vals.update(kwargs)
        return self.env["gest_agri.equipment.maintenance"].create(vals)

    # ------------------------------------------------------------------
    # Équipements
    # ------------------------------------------------------------------
    def test_equipment_creation(self):
        eq = self._create_equipment()
        self.assertTrue(eq.id)
        self.assertTrue(eq.reference.startswith("MAT/"))

    def test_equipment_type_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.equipment"].create(
                {"name": "Sans type", "farm_id": self.farm_a.id}
            )

    def test_equipment_farm_site_coherence(self):
        other_site = self.env["gest_agri.site"].create(
            {"name": "Autre site", "code": "AS", "farm_id": self.farm_b.id}
        )
        with self.assertRaises(ValidationError):
            self._create_equipment(site_id=other_site.id)

    def test_counters_positive(self):
        with self.assertRaises(ValidationError):
            self._create_equipment(hour_meter=-1.0)

    def test_equipment_state_transitions(self):
        eq = self._create_equipment()
        eq.action_available()
        self.assertEqual(eq.state, "available")
        eq.action_in_use()
        self.assertEqual(eq.state, "in_use")
        eq.action_maintenance()
        self.assertEqual(eq.state, "maintenance")
        eq.action_available()
        self.assertEqual(eq.state, "available")
        eq.action_out_of_service()
        self.assertEqual(eq.state, "out_of_service")
        eq.action_retire()
        self.assertEqual(eq.state, "retired")

    def test_equipment_direct_state_write_forbidden(self):
        eq = self._create_equipment()
        with self.assertRaises(AccessError):
            eq.write({"state": "available"})

    def test_equipment_archivable(self):
        eq = self._create_equipment()
        eq.write({"active": False})
        self.assertFalse(eq.active)

    def test_equipment_usage_count(self):
        self._create_usage(equipment=self.equipment)
        self.equipment.invalidate_recordset()
        self.assertEqual(self.equipment.usage_count, 1)

    def test_equipment_maintenance_count(self):
        self._create_maintenance(equipment=self.equipment)
        self.equipment.invalidate_recordset()
        self.assertEqual(self.equipment.maintenance_count, 1)

    def test_equipment_last_usage_date(self):
        usage = self._create_usage(equipment=self.equipment)
        self.equipment.invalidate_recordset()
        self.assertEqual(self.equipment.last_usage_date, usage.start_datetime)

    # ------------------------------------------------------------------
    # Utilisations
    # ------------------------------------------------------------------
    def test_usage_creation(self):
        usage = self._create_usage()
        self.assertTrue(usage.id)
        self.assertTrue(usage.name.startswith("UTI/"))
        self.assertEqual(usage.duration_hours, 4.0)

    def test_usage_counter_delta(self):
        usage = self._create_usage(counter_start=10.0, counter_end=15.0)
        self.assertAlmostEqual(usage.counter_delta, 5.0)

    def test_usage_date_control(self):
        with self.assertRaises(ValidationError):
            self._create_usage(
                start_datetime=datetime(2026, 7, 1, 12, 0),
                end_datetime=datetime(2026, 7, 1, 8, 0),
            )

    def test_usage_counter_control(self):
        with self.assertRaises(ValidationError):
            self._create_usage(counter_start=10.0, counter_end=5.0)

    def test_usage_retired_equipment_rejected(self):
        eq = self._create_equipment()
        eq.action_available()
        eq.action_retire()
        with self.assertRaises(ValidationError):
            self._create_usage(equipment=eq)

    def test_usage_maintenance_equipment_rejected(self):
        eq = self._create_equipment()
        eq.action_available()
        eq.action_maintenance()
        with self.assertRaises(ValidationError):
            self._create_usage(equipment=eq)

    def test_usage_overlap_rejected(self):
        self._create_usage()
        with self.assertRaises(ValidationError):
            self._create_usage(
                start_datetime=datetime(2026, 7, 1, 10, 0),
                end_datetime=datetime(2026, 7, 1, 14, 0),
            )

    def test_usage_farm_coherence(self):
        other_eq = self._create_equipment(farm_id=self.farm_b.id)
        with self.assertRaises(ValidationError):
            self._create_usage(equipment=other_eq, farm_id=self.farm_a.id)

    def test_usage_plot_coherence(self):
        other_plot = self.env["gest_agri.plot"].create(
            {"name": "P2", "code": "P2", "farm_id": self.farm_b.id, "area": 5.0}
        )
        with self.assertRaises(ValidationError):
            self._create_usage(plot_id=other_plot.id)

    def test_usage_state_transition(self):
        usage = self._create_usage()
        usage.action_done()
        self.assertEqual(usage.state, "done")
        usage2 = self._create_usage(
            start_datetime=datetime(2026, 7, 2, 8, 0),
            end_datetime=datetime(2026, 7, 2, 10, 0),
        )
        usage2.action_cancel()
        self.assertEqual(usage2.state, "cancelled")

    def test_usage_direct_state_write_forbidden(self):
        usage = self._create_usage()
        with self.assertRaises(AccessError):
            usage.write({"state": "done"})

    # ------------------------------------------------------------------
    # Maintenances
    # ------------------------------------------------------------------
    def test_maintenance_creation(self):
        m = self._create_maintenance()
        self.assertTrue(m.id)
        self.assertTrue(m.name.startswith("MAI/"))
        self.assertEqual(m.state, "draft")

    def test_maintenance_types(self):
        for t in ("preventive", "corrective", "inspection", "revision", "repair"):
            m = self._create_maintenance(maintenance_type=t)
            self.assertEqual(m.maintenance_type, t)

    def test_maintenance_workflow(self):
        m = self._create_maintenance()
        m.action_plan()
        self.assertEqual(m.state, "planned")
        m.action_start()
        self.assertEqual(m.state, "in_progress")
        m.action_done()
        self.assertEqual(m.state, "done")
        self.assertTrue(m.realized_date)

    def test_maintenance_cancel(self):
        m = self._create_maintenance()
        m.action_plan()
        m.action_cancel()
        self.assertEqual(m.state, "cancelled")

    def test_maintenance_direct_state_write_forbidden(self):
        m = self._create_maintenance()
        with self.assertRaises(AccessError):
            m.write({"state": "planned"})

    def test_maintenance_total_cost(self):
        m = self._create_maintenance(parts_cost=100.0, labor_cost=50.0, external_cost=25.0)
        self.assertAlmostEqual(m.total_cost, 175.0)

    def test_maintenance_counter_positive(self):
        with self.assertRaises(ValidationError):
            self._create_maintenance(counter_at_maintenance=-1.0)

    def test_maintenance_delete_draft_allowed(self):
        m = self._create_maintenance()
        m.unlink()
        self.assertFalse(self.env["gest_agri.equipment.maintenance"].browse(m.id).exists())

    def test_maintenance_delete_validated_forbidden(self):
        m = self._create_maintenance()
        m.action_plan()
        m.action_start()
        m.action_done()
        with self.assertRaises(UserError):
            m.unlink()

    def test_maintenance_makes_equipment_unavailable(self):
        eq = self._create_equipment()
        eq.action_available()
        m = self._create_maintenance(equipment=eq)
        m.action_plan()
        m.action_start()
        self.assertEqual(eq.state, "maintenance")

    def test_maintenance_restore_availability(self):
        eq = self._create_equipment()
        eq.action_available()
        m = self._create_maintenance(equipment=eq)
        m.action_plan()
        m.action_start()
        m.action_done()
        self.assertEqual(eq.state, "available")

    def test_maintenance_preventive_due_dates(self):
        m = self._create_maintenance(
            next_due_date=date(2026, 12, 31),
            next_due_hours=500.0,
            next_due_km=10000.0,
        )
        self.assertEqual(m.next_due_date, date(2026, 12, 31))
        self.assertAlmostEqual(m.next_due_hours, 500.0)

    def test_equipment_total_maintenance_cost(self):
        eq = self._create_equipment()
        self._create_maintenance(equipment=eq, parts_cost=100.0)
        self._create_maintenance(equipment=eq, parts_cost=50.0)
        eq.invalidate_recordset()
        self.assertAlmostEqual(eq.total_maintenance_cost, 150.0)

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_parse_and_install(self):
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "gestion_agricole")]))
