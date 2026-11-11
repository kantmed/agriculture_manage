# -*- coding: utf-8 -*-
from datetime import date

import psycopg2

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase

DATE_UNIQUE_ERRORS = (ValidationError, psycopg2.errors.UniqueViolation)


class TestCropCycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")
        cls.base_user = cls.env.ref("base.group_user")

        cls.user_a = cls._create_user(
            "crop_user_a", [cls.base_user, cls.group_user]
        )
        cls.user_b = cls._create_user(
            "crop_user_b", [cls.base_user, cls.group_user]
        )
        cls.manager = cls._create_user(
            "crop_manager", [cls.base_user, cls.group_manager]
        )
        cls.admin = cls._create_user(
            "crop_admin", [cls.base_user, cls.group_admin]
        )
        cls.farm_owner = cls.env["res.users"].create(
            {
                "name": "Propriétaire technique cultures",
                "login": "crop_farm_owner",
                "email": "crop_farm_owner@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [cls.base_user.id, cls.group_user.id])],
            }
        )

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine cultures A",
                "code": "CUL-A",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine cultures B",
                "code": "CUL-B",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )

        cls.plot_a = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle cultures A", "code": "PCA", "farm_id": cls.farm_a.id, "area": 10.0}
        )
        cls.plot_a2 = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle cultures A2", "code": "PCA2", "farm_id": cls.farm_a.id, "area": 20.0}
        )
        cls.plot_c = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle cultures C", "code": "PCC", "farm_id": cls.farm_a.id, "area": 8.0}
        )
        cls.plot_b = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle cultures B", "code": "PCB", "farm_id": cls.farm_b.id, "area": 5.0}
        )

        cls.wheat = cls.env["gest_agri.crop.type"].create(
            {"name": "Blé tendre", "code": "BLE", "company_id": cls.company.id}
        )
        cls.barley = cls.env["gest_agri.crop.type"].create(
            {"name": "Orge", "code": "ORG", "company_id": cls.company.id}
        )
        cls.wheat_variety = cls.env["gest_agri.crop.variety"].create(
            {
                "name": "Blé tendre variété A",
                "code": "BLE-A",
                "company_id": cls.company.id,
                "crop_type_id": cls.wheat.id,
            }
        )
        cls.barley_variety = cls.env["gest_agri.crop.variety"].create(
            {
                "name": "Orge variété A",
                "code": "ORG-A",
                "company_id": cls.company.id,
                "crop_type_id": cls.barley.id,
            }
        )

        # Droits d'accès aux exploitations.
        cls.env["gest_agri.farm.access"].create(
            {"farm_id": cls.farm_a.id, "user_id": cls.user_a.id, "role": "user"}
        )
        cls.env["gest_agri.farm.access"].create(
            {"farm_id": cls.farm_b.id, "user_id": cls.user_b.id, "role": "user"}
        )
        cls.env["gest_agri.farm.access"].create(
            {"farm_id": cls.farm_a.id, "user_id": cls.manager.id, "role": "manager"}
        )

        # Cycles de référence pour les tests de sécurité.
        cls.cycle_a = cls.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": cls.plot_c.id,
                "crop_type_id": cls.wheat.id,
                "date_start": date(2025, 1, 1),
                "date_end_planned": date(2025, 3, 31),
            }
        )
        cls.cycle_b = cls.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": cls.plot_b.id,
                "crop_type_id": cls.wheat.id,
                "date_start": date(2025, 1, 1),
                "date_end_planned": date(2025, 3, 31),
            }
        )

    @classmethod
    def _create_user(cls, login, groups):
        group_ids = [
            group.id if hasattr(group, "id") else int(group) for group in groups
        ]
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

    def _create_cycle(self, plot=None, crop_type=None, start=None, **kwargs):
        values = {
            "plot_id": (plot or self.plot_a).id,
            "crop_type_id": (crop_type or self.wheat).id,
            "date_start": start or date(2026, 1, 1),
        }
        values.update(kwargs)
        return self.env["gest_agri.crop.cycle"].create(values)

    # ------------------------------------------------------------------
    # 10.1 Création
    # ------------------------------------------------------------------
    def test_create_minimal_cycle(self):
        cycle = self._create_cycle()
        self.assertTrue(cycle.name)
        self.assertEqual(cycle.state, "planned")
        self.assertEqual(cycle.plot_id, self.plot_a)
        self.assertEqual(cycle.farm_id, self.farm_a)
        self.assertEqual(cycle.company_id, self.company)

    def test_reference_generated_and_unique(self):
        first = self._create_cycle()
        second = self._create_cycle(plot=self.plot_a2)
        self.assertTrue(first.name.startswith("CUL/"))
        self.assertTrue(second.name.startswith("CUL/"))
        self.assertNotEqual(first.name, second.name)

    def test_area_initialized_from_plot(self):
        cycle = self._create_cycle()
        self.assertEqual(cycle.area_ha, self.plot_a.area)

    def test_area_partial_modification(self):
        cycle = self._create_cycle()
        cycle.write({"area_ha": 4.5})
        self.assertEqual(cycle.area_ha, 4.5)

    def test_area_zero_or_negative_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_cycle(area_ha=0.0)
        cycle = self._create_cycle(area_ha=1.0)
        with self.assertRaises(ValidationError):
            cycle.write({"area_ha": -1.0})

    def test_area_exceeding_plot_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_cycle(area_ha=11.0)

    def test_variety_from_other_type_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_cycle(crop_variety_id=self.barley_variety.id)
        cycle = self._create_cycle(crop_variety_id=self.wheat_variety.id)
        with self.assertRaises(ValidationError):
            cycle.write({"crop_variety_id": self.barley_variety.id})

    def test_onchange_clears_incompatible_variety(self):
        cycle = self.env["gest_agri.crop.cycle"].new(
            {
                "plot_id": self.plot_a.id,
                "crop_type_id": self.wheat.id,
                "crop_variety_id": self.wheat_variety.id,
                "date_start": date(2026, 1, 1),
                "area_ha": 5.0,
            }
        )
        cycle.crop_type_id = self.barley
        cycle._onchange_crop_type_id()
        self.assertFalse(cycle.crop_variety_id)

    # ------------------------------------------------------------------
    # 10.2 Dates
    # ------------------------------------------------------------------
    def test_dates_consistent_accepted(self):
        cycle = self._create_cycle(
            date_end_planned=date(2026, 6, 30),
            date_end_actual=date(2026, 6, 20),
        )
        self.assertEqual(cycle.date_end_planned, date(2026, 6, 30))
        self.assertEqual(cycle.date_end_actual, date(2026, 6, 20))

    def test_planned_end_before_start_rejected(self):
        cycle = self._create_cycle()
        with self.assertRaises(ValidationError):
            cycle.write({"date_end_planned": date(2025, 12, 31)})

    def test_actual_end_before_start_rejected(self):
        cycle = self._create_cycle()
        with self.assertRaises(ValidationError):
            cycle.write({"date_end_actual": date(2025, 12, 31)})

    def test_done_without_actual_end_rejected(self):
        cycle = self._create_cycle()
        cycle.action_plant()
        cycle.action_start()
        with self.assertRaises((UserError, ValidationError)):
            cycle.action_done()

    def test_done_with_actual_end_accepted(self):
        cycle = self._create_cycle(date_end_actual=date(2026, 6, 30))
        cycle.action_plant()
        cycle.action_start()
        cycle.action_done()
        self.assertEqual(cycle.state, "done")

    # ------------------------------------------------------------------
    # 10.3 Chevauchements
    # ------------------------------------------------------------------
    def test_partial_overlap_rejected(self):
        self._create_cycle(
            date_end_planned=date(2026, 3, 31),
        )
        with self.assertRaises(ValidationError):
            self._create_cycle(
                start=date(2026, 3, 15),
                date_end_planned=date(2026, 4, 30),
            )

    def test_same_start_day_rejected(self):
        self._create_cycle(date_end_planned=date(2026, 2, 1))
        with self.assertRaises(DATE_UNIQUE_ERRORS):
            self._create_cycle(date_end_planned=date(2026, 3, 1))

    def test_touching_on_same_day_rejected(self):
        self._create_cycle(date_end_planned=date(2026, 3, 31))
        with self.assertRaises(ValidationError):
            self._create_cycle(
                start=date(2026, 3, 31),
                date_end_planned=date(2026, 4, 30),
            )

    def test_successive_without_common_day_accepted(self):
        self._create_cycle(date_end_planned=date(2026, 3, 31))
        second = self._create_cycle(
            start=date(2026, 4, 1),
            date_end_planned=date(2026, 6, 30),
        )
        self.assertTrue(second.id)

    def test_previous_without_end_blocks(self):
        self._create_cycle()
        with self.assertRaises(ValidationError):
            self._create_cycle(start=date(2026, 2, 1))

    def test_succession_after_effective_actual_end(self):
        self._create_cycle(
            date_end_planned=date(2026, 6, 30),
            date_end_actual=date(2026, 6, 20),
        )
        second = self._create_cycle(start=date(2026, 6, 25))
        self.assertTrue(second.id)

    def test_cancelled_cycle_excluded_from_overlap(self):
        first = self._create_cycle(date_end_planned=date(2026, 3, 31))
        first.action_cancel()
        self.assertEqual(first.state, "cancelled")
        second = self._create_cycle(
            start=date(2026, 2, 1),
            date_end_planned=date(2026, 4, 30),
        )
        self.assertTrue(second.id)

    def test_archived_cycle_still_blocks(self):
        first = self._create_cycle(date_end_planned=date(2026, 3, 31))
        first.write({"active": False})
        with self.assertRaises(ValidationError):
            self._create_cycle(
                start=date(2026, 2, 1),
                date_end_planned=date(2026, 4, 30),
            )

    def test_overlap_checked_on_date_change(self):
        self._create_cycle(date_end_planned=date(2026, 3, 31))
        other = self._create_cycle(
            start=date(2026, 5, 1),
            date_end_planned=date(2026, 6, 30),
        )
        with self.assertRaises(ValidationError):
            other.write({"date_start": date(2026, 3, 1)})

    def test_overlap_checked_on_plot_change(self):
        self._create_cycle(date_end_planned=date(2026, 3, 31))
        other = self._create_cycle(
            plot=self.plot_a2,
            start=date(2026, 2, 1),
            date_end_planned=date(2026, 4, 30),
            area_ha=5.0,
        )
        with self.assertRaises(ValidationError):
            other.write({"plot_id": self.plot_a.id})

    def test_reactivation_checks_overlap(self):
        first = self._create_cycle(date_end_planned=date(2026, 3, 31))
        first.write({"active": False})
        self._create_cycle(
            start=date(2026, 5, 1),
            date_end_planned=date(2026, 6, 30),
        )
        first.write({"active": True})
        self.assertTrue(first.active)

    def test_reset_cancelled_cycle_checks_overlap(self):
        first = self._create_cycle(date_end_planned=date(2026, 3, 31))
        first.action_cancel()
        self._create_cycle(
            start=date(2026, 2, 1),
            date_end_planned=date(2026, 4, 30),
        )
        with self.assertRaises(ValidationError):
            first.action_reset()

    # ------------------------------------------------------------------
    # 10.4 États et transitions
    # ------------------------------------------------------------------
    def test_allowed_transitions(self):
        cycle = self._create_cycle(date_end_actual=date(2026, 6, 30))
        self.assertEqual(cycle.state, "planned")
        cycle.action_plant()
        self.assertEqual(cycle.state, "planted")
        cycle.action_start()
        self.assertEqual(cycle.state, "in_progress")
        cycle.action_done()
        self.assertEqual(cycle.state, "done")

    def test_forbidden_transitions(self):
        cycle = self._create_cycle()
        with self.assertRaises(UserError):
            cycle.action_start()
        with self.assertRaises(UserError):
            cycle.action_done()
        cycle.action_plant()
        with self.assertRaises(UserError):
            cycle.action_done()

    def test_direct_state_write_rejected(self):
        cycle = self._create_cycle()
        with self.assertRaises(AccessError):
            cycle.write({"state": "planted"})

    def test_cancelled_reset_by_manager(self):
        cycle = self._create_cycle()
        cycle.action_cancel()
        cycle.with_user(self.manager).action_reset()
        self.assertEqual(cycle.state, "planned")

    def test_cancelled_reset_forbidden_for_user(self):
        cycle = self._create_cycle()
        cycle.action_cancel()
        with self.assertRaises(AccessError):
            cycle.with_user(self.user_a).action_reset()

    # ------------------------------------------------------------------
    # 10.5 Sécurité
    # ------------------------------------------------------------------
    def test_farm_isolation(self):
        visible = self.env["gest_agri.crop.cycle"].with_user(self.user_a).search([])
        self.assertIn(self.cycle_a, visible)
        self.assertNotIn(self.cycle_b, visible)
        with self.assertRaises(AccessError):
            self.cycle_b.with_user(self.user_a).read(["name"])

    def test_multi_company_isolation(self):
        other_company = self.env["res.company"].create({"name": "Société cultures B"})
        other_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Ferme autre société",
                "code": "CUL-OTHER",
                "company_id": other_company.id,
                "total_area": 20.0,
            }
        )
        other_plot = self.env["gest_agri.plot"].create(
            {
                "name": "Parcelle autre société",
                "code": "PCO",
                "farm_id": other_farm.id,
                "area": 5.0,
            }
        )
        other_type = self.env["gest_agri.crop.type"].create(
            {"name": "Culture autre société", "code": "OTH", "company_id": other_company.id}
        )
        other_cycle = self.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": other_plot.id,
                "crop_type_id": other_type.id,
                "date_start": date(2025, 1, 1),
            }
        )
        visible = self.env["gest_agri.crop.cycle"].with_user(self.user_a).search([])
        self.assertNotIn(other_cycle, visible)
        with self.assertRaises(AccessError):
            other_cycle.with_user(self.admin).read(["name"])

    def test_user_can_read_accessible_cycle(self):
        self.assertEqual(
            self.cycle_a.with_user(self.user_a).read(["name"])[0]["name"],
            self.cycle_a.name,
        )

    def test_manager_can_create_and_write_on_managed_farm(self):
        cycle = (
            self.env["gest_agri.crop.cycle"]
            .with_user(self.manager)
            .create(
                {
                    "plot_id": self.plot_a.id,
                    "crop_type_id": self.wheat.id,
                    "date_start": date(2027, 1, 1),
                }
            )
        )
        self.assertTrue(cycle.id)
        cycle.with_user(self.manager).write({"notes": "Suivi responsable"})
        self.assertEqual(cycle.notes, "Suivi responsable")
        with self.assertRaises(AccessError):
            self.env["gest_agri.crop.cycle"].with_user(self.manager).create(
                {
                    "plot_id": self.plot_b.id,
                    "crop_type_id": self.wheat.id,
                    "date_start": date(2027, 1, 1),
                }
            )

    def test_admin_can_manage_cycle(self):
        cycle = self._create_cycle(start=date(2027, 2, 1), date_end_planned=date(2027, 3, 1))
        cycle.with_user(self.admin).write({"notes": "Gestion admin"})
        self.assertEqual(cycle.notes, "Gestion admin")
        cycle.with_user(self.admin).unlink()
        self.assertFalse(cycle.exists())

    def test_user_cannot_create_write_or_unlink(self):
        with self.assertRaises(AccessError):
            self.env["gest_agri.crop.cycle"].with_user(self.user_a).create(
                {
                    "plot_id": self.plot_a.id,
                    "crop_type_id": self.wheat.id,
                    "date_start": date(2027, 3, 1),
                }
            )
        with self.assertRaises(AccessError):
            self.cycle_a.with_user(self.user_a).write({"notes": "Interdit"})
        with self.assertRaises(AccessError):
            self.cycle_a.with_user(self.user_a).unlink()
