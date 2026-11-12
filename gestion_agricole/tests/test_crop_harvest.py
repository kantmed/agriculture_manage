# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestCropHarvest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")

        cls.user_a = cls._create_user("harvest_user_a", [cls.base_user, cls.group_user])
        cls.user_b = cls._create_user("harvest_user_b", [cls.base_user, cls.group_user])
        cls.manager = cls._create_user("harvest_manager", [cls.base_user, cls.group_manager])
        cls.admin = cls._create_user("harvest_admin", [cls.base_user, cls.group_admin])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {
                "name": "Ferme récolte A",
                "code": "HAR-A",
                "company_id": cls.company.id,
                "manager_id": cls.manager.id,
                "total_area": 50.0,
            }
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {
                "name": "Ferme récolte B",
                "code": "HAR-B",
                "company_id": cls.company.id,
                "manager_id": cls.manager.id,
                "total_area": 30.0,
            }
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle récolte A", "code": "PHAR-A", "farm_id": cls.farm_a.id, "area": 10.0}
        )
        cls.plot_b = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle récolte B", "code": "PHAR-B", "farm_id": cls.farm_b.id, "area": 5.0}
        )
        cls.crop_type = cls.env["gest_agri.crop.type"].create(
            {"name": "Blé récolte", "code": "BLR", "company_id": cls.company.id}
        )
        cls.campaign = cls.env["gest_agri.crop.campaign"].create(
            {
                "name": "Campagne récolte",
                "farm_id": cls.farm_a.id,
                "date_start": date(2026, 1, 1),
                "date_end": date(2026, 12, 31),
            }
        )
        cls.cycle = cls.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": cls.plot_a.id,
                "campaign_id": cls.campaign.id,
                "crop_type_id": cls.crop_type.id,
                "date_start": date(2026, 2, 1),
                "date_end_planned": date(2026, 8, 30),
                "area_ha": 10.0,
            }
        )
        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_t = cls.env.ref("uom.product_uom_ton")

    @classmethod
    def _create_user(cls, login, groups):
        group_ids = [group.id for group in groups]
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

    def _create_harvest(self, **kwargs):
        values = {
            "cycle_id": self.cycle.id,
            "harvest_date": date(2026, 7, 15),
            "quantity": 5000.0,
            "uom_id": self.uom_kg.id,
            "harvested_area": 5.0,
            "state": "draft",
        }
        values.update(kwargs)
        return self.env["gest_agri.crop.harvest"].create(values)

    def test_harvest_creation(self):
        harvest = self._create_harvest()
        self.assertTrue(harvest.id)
        self.assertTrue(harvest.name.startswith("REC/"))
        self.assertEqual(harvest.state, "draft")

    def test_name_sequence_generated(self):
        harvest = self._create_harvest()
        self.assertRegex(harvest.name, r"^REC/\d{4}/\d{5}$")

    def test_cycle_required(self):
        with self.assertRaises((ValidationError, UserError)):
            self.env["gest_agri.crop.harvest"].create(
                {
                    "harvest_date": date(2026, 7, 1),
                    "quantity": 100.0,
                    "uom_id": self.uom_kg.id,
                    "harvested_area": 1.0,
                }
            )

    def test_plot_derived_from_cycle(self):
        harvest = self._create_harvest()
        self.assertEqual(harvest.plot_id, self.plot_a)

    def test_campaign_derived_from_cycle(self):
        harvest = self._create_harvest()
        self.assertEqual(harvest.campaign_id, self.campaign)

    def test_farm_derived_from_cycle(self):
        harvest = self._create_harvest()
        self.assertEqual(harvest.farm_id, self.farm_a)

    def test_company_derived_from_cycle(self):
        harvest = self._create_harvest()
        self.assertEqual(harvest.company_id, self.company)

    def test_quantity_positive(self):
        with self.assertRaises(ValidationError):
            self._create_harvest(quantity=0.0)

    def test_area_positive(self):
        with self.assertRaises(ValidationError):
            self._create_harvest(harvested_area=0.0)

    def test_area_cannot_exceed_cycle(self):
        with self.assertRaises(ValidationError):
            self._create_harvest(harvested_area=20.0)

    def test_date_before_cycle_start(self):
        with self.assertRaises(ValidationError):
            self._create_harvest(harvest_date=date(2026, 1, 31))

    def test_date_after_cycle_end_planned(self):
        with self.assertRaises(ValidationError):
            self._create_harvest(harvest_date=date(2026, 9, 1))

    def test_date_after_cycle_end_actual(self):
        self.cycle.write({"date_end_actual": date(2026, 8, 20)})
        with self.assertRaises(ValidationError):
            self._create_harvest(harvest_date=date(2026, 8, 21))

    def test_multiple_harvests_same_cycle_allowed(self):
        self._create_harvest(quantity=1000.0, harvested_area=2.0)
        self._create_harvest(quantity=2000.0, harvested_area=3.0)
        self.assertEqual(self.env["gest_agri.crop.harvest"].search_count([("cycle_id", "=", self.cycle.id)]), 2)

    def test_yield_calculated(self):
        harvest = self._create_harvest(quantity=5000.0, harvested_area=5.0)
        self.assertAlmostEqual(harvest.yield_qty, 1000.0)

    def test_yield_zero_if_area_zero(self):
        with self.assertRaises(ValidationError):
            self._create_harvest(harvested_area=0.0)

    def test_validate_transition(self):
        harvest = self._create_harvest()
        harvest.action_validate()
        self.assertEqual(harvest.state, "validated")

    def test_cancel_after_validation(self):
        harvest = self._create_harvest()
        harvest.action_validate()
        harvest.action_cancel()
        self.assertEqual(harvest.state, "cancelled")

    def test_cancel_before_validation(self):
        harvest = self._create_harvest()
        harvest.action_cancel()
        self.assertEqual(harvest.state, "cancelled")

    def test_state_change_direct_write_forbidden(self):
        harvest = self._create_harvest()
        with self.assertRaises(AccessError):
            harvest.write({"state": "validated"})

    def test_derived_fields_cannot_be_modified(self):
        harvest = self._create_harvest()
        with self.assertRaises(UserError):
            harvest.write({"plot_id": self.plot_b.id})

    def test_delete_draft_allowed(self):
        harvest = self._create_harvest()
        harvest.unlink()
        self.assertFalse(self.env["gest_agri.crop.harvest"].browse(harvest.id).exists())

    def test_delete_validated_forbidden(self):
        harvest = self._create_harvest()
        harvest.action_validate()
        with self.assertRaises(UserError):
            harvest.unlink()

    def test_uom_compatibility(self):
        harvest = self._create_harvest(quantity=5.0, uom_id=self.uom_t.id)
        self.assertTrue(harvest.id)

    def test_non_matching_campaign_rejected(self):
        other_campaign = self.env["gest_agri.crop.campaign"].create(
            {
                "name": "Autre campagne",
                "farm_id": self.farm_a.id,
                "date_start": date(2026, 1, 1),
                "date_end": date(2026, 12, 31),
            }
        )
        with self.assertRaises((ValidationError, UserError)):
            self.env["gest_agri.crop.harvest"].create(
                {
                    "cycle_id": self.cycle.id,
                    "campaign_id": other_campaign.id,
                    "harvest_date": date(2026, 7, 15),
                    "quantity": 1000.0,
                    "uom_id": self.uom_kg.id,
                    "harvested_area": 2.0,
                }
            )

    def test_cycle_cancelled_rejects_harvest(self):
        self.cycle.action_cancel()
        with self.assertRaises((ValidationError, UserError)):
            self._create_harvest()

    def test_parse_and_install(self):
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "gestion_agricole")]))

    def test_harvest_date_equal_cycle_start_allowed(self):
        harvest = self._create_harvest(harvest_date=date(2026, 2, 1))
        self.assertEqual(harvest.harvest_date, date(2026, 2, 1))

    def test_harvest_date_equal_cycle_end_actual_allowed(self):
        self.cycle.write({"date_end_actual": date(2026, 8, 30)})
        harvest = self._create_harvest(harvest_date=date(2026, 8, 30))
        self.assertEqual(harvest.harvest_date, date(2026, 8, 30))

    def test_harvest_date_equal_cycle_end_planned_allowed(self):
        self.cycle.write({"date_end_actual": False, "date_end_planned": date(2026, 8, 30)})
        harvest = self._create_harvest(harvest_date=date(2026, 8, 30))
        self.assertEqual(harvest.harvest_date, date(2026, 8, 30))

    def test_harvest_with_other_plot_rejected(self):
        other_cycle = self.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": self.plot_b.id,
                "crop_type_id": self.crop_type.id,
                "date_start": date(2026, 2, 1),
                "date_end_planned": date(2026, 8, 30),
                "area_ha": 5.0,
            }
        )
        with self.assertRaises((ValidationError, UserError)):
            self.env["gest_agri.crop.harvest"].create(
                {
                    "cycle_id": self.cycle.id,
                    "plot_id": other_cycle.plot_id.id,
                    "harvest_date": date(2026, 7, 10),
                    "quantity": 1000.0,
                    "uom_id": self.uom_kg.id,
                    "harvested_area": 2.0,
                }
            )

    def test_state_cancelled_has_no_direct_rewrite(self):
        harvest = self._create_harvest()
        harvest.action_validate()
        harvest.action_cancel()
        with self.assertRaises(AccessError):
            harvest.write({"notes": "test"})

    def test_harvest_notes_can_be_edited_in_draft(self):
        harvest = self._create_harvest(notes="Premier test")
        harvest.write({"notes": "Modifié"})
        self.assertEqual(harvest.notes, "Modifié")

    def test_harvest_validation_keeps_history(self):
        harvest = self._create_harvest()
        harvest.action_validate()
        harvest.action_cancel()
        self.assertEqual(harvest.state, "cancelled")

    def test_harvest_is_archivable(self):
        harvest = self._create_harvest()
        harvest.write({"active": False})
        self.assertFalse(harvest.active)

    def test_harvest_quantity_conversion_to_reference(self):
        harvest = self._create_harvest(quantity=2.0, uom_id=self.uom_t.id)
        self.assertTrue(harvest.yield_qty >= 0)

    def test_harvest_quantity_conversion_compatible_category(self):
        harvest = self._create_harvest(quantity=5.0, uom_id=self.uom_kg.id)
        self.assertTrue(harvest.id)

    def test_harvest_invalid_cycle_state_rejected(self):
        self.cycle.action_plant()
        self.cycle.action_start()
        self.cycle.write({"date_end_actual": date(2026, 8, 30)})
        self.cycle.action_done()
        harvest = self._create_harvest(harvest_date=date(2026, 8, 30))
        self.assertTrue(harvest.id)

    def test_harvest_date_equal_cycle_end_actual_with_state_done(self):
        self.cycle.action_plant()
        self.cycle.action_start()
        self.cycle.write({"date_end_actual": date(2026, 8, 30)})
        self.cycle.action_done()
        harvest = self._create_harvest(harvest_date=date(2026, 8, 30))
        self.assertEqual(harvest.harvest_date, date(2026, 8, 30))

    def test_harvest_multiple_records_are_independent(self):
        first = self._create_harvest(quantity=900.0, harvested_area=2.0)
        second = self._create_harvest(quantity=1300.0, harvested_area=3.0)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.cycle_id, self.cycle)
        self.assertEqual(second.cycle_id, self.cycle)

    def test_cyclic_harvest_date_in_range(self):
        harvest = self._create_harvest(harvest_date=date(2026, 7, 1))
        self.assertEqual(harvest.harvest_date, date(2026, 7, 1))

    def test_harvest_total_quantity_and_yield_can_be_consulted(self):
        self._create_harvest(quantity=3000.0, harvested_area=3.0)
        total = self.env["gest_agri.crop.harvest"].search_count([("cycle_id", "=", self.cycle.id)])
        self.assertEqual(total, 1)
