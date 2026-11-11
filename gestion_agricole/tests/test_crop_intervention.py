# -*- coding: utf-8 -*-
from datetime import date

import psycopg2

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase

UNIQUE_ERRORS = (ValidationError, psycopg2.errors.UniqueViolation)
REQUIRED_ERRORS = (
    psycopg2.errors.NotNullViolation,
    ValidationError,
    UserError,
)


class TestCropIntervention(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")
        cls.base_user = cls.env.ref("base.group_user")

        cls.user_a = cls._create_user("int_user_a", [cls.base_user, cls.group_user])
        cls.user_b = cls._create_user("int_user_b", [cls.base_user, cls.group_user])
        cls.manager = cls._create_user(
            "int_manager", [cls.base_user, cls.group_manager]
        )
        cls.admin = cls._create_user("int_admin", [cls.base_user, cls.group_admin])
        cls.farm_owner = cls.env["res.users"].create(
            {
                "name": "Propriétaire technique interventions",
                "login": "int_farm_owner",
                "email": "int_farm_owner@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [cls.base_user.id, cls.group_user.id])],
            }
        )

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine interventions A",
                "code": "INT-A",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine interventions B",
                "code": "INT-B",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 50.0,
            }
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle interventions A", "code": "PINT-A", "farm_id": cls.farm_a.id, "area": 10.0}
        )
        cls.plot_a2 = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle interventions A2", "code": "PINT-A2", "farm_id": cls.farm_a.id, "area": 8.0}
        )
        cls.plot_b = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle interventions B", "code": "PINT-B", "farm_id": cls.farm_b.id, "area": 5.0}
        )
        cls.crop_type = cls.env["gest_agri.crop.type"].create(
            {"name": "Blé interventions", "code": "BINT", "company_id": cls.company.id}
        )
        cls.operation_type = cls.env["gest_agri.operation.type"].create(
            {
                "name": "Labour",
                "code": "LAB",
                "company_id": cls.company.id,
            }
        )
        cls.operation_type_2 = cls.env["gest_agri.operation.type"].create(
            {
                "name": "Fertilisation",
                "code": "FERT",
                "company_id": cls.company.id,
            }
        )

        cls.env["gest_agri.farm.access"].create(
            {"farm_id": cls.farm_a.id, "user_id": cls.user_a.id, "role": "user"}
        )
        cls.env["gest_agri.farm.access"].create(
            {"farm_id": cls.farm_b.id, "user_id": cls.user_b.id, "role": "user"}
        )
        cls.env["gest_agri.farm.access"].create(
            {"farm_id": cls.farm_a.id, "user_id": cls.manager.id, "role": "manager"}
        )

        cls.campaign = cls.env["gest_agri.crop.campaign"].create(
            {
                "name": "Campagne interventions",
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
                "date_end_planned": date(2026, 11, 30),
            }
        )
        cls.cycle_open = cls.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": cls.plot_a2.id,
                "crop_type_id": cls.crop_type.id,
                "date_start": date(2026, 2, 1),
            }
        )
        cls.cycle_b = cls.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": cls.plot_b.id,
                "crop_type_id": cls.crop_type.id,
                "date_start": date(2026, 2, 1),
                "date_end_planned": date(2026, 11, 30),
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

    def _create_intervention(self, cycle=None, **kwargs):
        values = {
            "name": "Labour de préparation",
            "crop_cycle_id": (cycle or self.cycle).id,
            "operation_type_id": self.operation_type.id,
            "date_planned": date(2026, 3, 15),
        }
        values.update(kwargs)
        return self.env["gest_agri.crop.intervention"].create(values)

    # ------------------------------------------------------------------
    # Création et identification
    # ------------------------------------------------------------------
    def test_intervention_creation(self):
        intervention = self._create_intervention()
        self.assertTrue(intervention.id)
        self.assertEqual(intervention.state, "draft")
        self.assertEqual(intervention.crop_cycle_id, self.cycle)
        self.assertEqual(intervention.operation_type_id, self.operation_type)

    def test_code_generated(self):
        intervention = self._create_intervention()
        self.assertTrue(intervention.code.startswith("INT/"))
        self.assertRegex(intervention.code, r"^INT/\d{4}/\d{5}$")

    def test_code_uniqueness(self):
        first = self._create_intervention()
        second = self._create_intervention()
        self.assertNotEqual(first.code, second.code)
        with self.assertRaises(UNIQUE_ERRORS):
            second.write({"code": first.code})

    def test_code_kept_on_archive(self):
        intervention = self._create_intervention()
        code = intervention.code
        intervention.write({"active": False})
        archived = (
            self.env["gest_agri.crop.intervention"]
            .with_context(active_test=False)
            .browse(intervention.id)
        )
        self.assertEqual(archived.code, code)

    # ------------------------------------------------------------------
    # Champs obligatoires
    # ------------------------------------------------------------------
    def test_cycle_required(self):
        with self.assertRaises(REQUIRED_ERRORS):
            self.env["gest_agri.crop.intervention"].create(
                {
                    "name": "Intervention sans cycle",
                    "operation_type_id": self.operation_type.id,
                }
            )

    def test_operation_type_required(self):
        with self.assertRaises(REQUIRED_ERRORS):
            self.env["gest_agri.crop.intervention"].create(
                {
                    "name": "Intervention sans type",
                    "crop_cycle_id": self.cycle.id,
                }
            )

    # ------------------------------------------------------------------
    # Cohérence avec le cycle
    # ------------------------------------------------------------------
    def test_plot_derived_from_cycle(self):
        intervention = self._create_intervention()
        self.assertEqual(intervention.plot_id, self.cycle.plot_id)
        self.assertEqual(intervention.plot_id, self.plot_a)

    def test_farm_derived_from_cycle(self):
        intervention = self._create_intervention()
        self.assertEqual(intervention.farm_id, self.cycle.farm_id)
        self.assertEqual(intervention.farm_id, self.farm_a)

    def test_company_derived_from_cycle(self):
        intervention = self._create_intervention()
        self.assertEqual(intervention.company_id, self.cycle.company_id)
        self.assertEqual(intervention.company_id, self.company)

    def test_campaign_derived_from_cycle(self):
        intervention = self._create_intervention()
        self.assertEqual(intervention.campaign_id, self.cycle.campaign_id)
        self.assertEqual(intervention.campaign_id, self.campaign)

    def test_cycle_without_campaign(self):
        intervention = self._create_intervention(cycle=self.cycle_open)
        self.assertFalse(self.cycle_open.campaign_id)
        self.assertFalse(intervention.campaign_id)

    def test_derived_fields_cannot_be_modified(self):
        intervention = self._create_intervention()
        with self.assertRaises(UserError):
            intervention.write({"plot_id": self.plot_b.id})
        with self.assertRaises(UserError):
            intervention.write({"campaign_id": self.campaign.id})

    # ------------------------------------------------------------------
    # Contrôle des dates
    # ------------------------------------------------------------------
    def test_planned_date_within_cycle(self):
        intervention = self._create_intervention(date_planned=date(2026, 5, 1))
        self.assertEqual(intervention.date_planned, date(2026, 5, 1))

    def test_actual_date_within_cycle(self):
        intervention = self._create_intervention(date_actual=date(2026, 5, 2))
        self.assertEqual(intervention.date_actual, date(2026, 5, 2))

    def test_date_before_cycle_start_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_intervention(date_planned=date(2026, 1, 31))
        with self.assertRaises(ValidationError):
            self._create_intervention(date_actual=date(2026, 1, 31))

    def test_date_after_cycle_end_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_intervention(date_planned=date(2026, 12, 1))
        with self.assertRaises(ValidationError):
            self._create_intervention(date_actual=date(2026, 12, 1))

    def test_open_end_cycle_accepts_late_date(self):
        intervention = self._create_intervention(
            cycle=self.cycle_open, date_planned=date(2027, 3, 1)
        )
        self.assertEqual(intervention.date_planned, date(2027, 3, 1))

    def test_cycle_date_change_rejected_when_inconsistent(self):
        self._create_intervention(date_planned=date(2026, 9, 1))
        with self.assertRaises(ValidationError):
            self.cycle.write({"date_end_planned": date(2026, 8, 31)})

    def test_cycle_date_change_allowed_when_consistent(self):
        self._create_intervention(date_planned=date(2026, 3, 15))
        self.cycle.write({"date_end_planned": date(2026, 12, 31)})
        self.assertEqual(self.cycle.date_end_planned, date(2026, 12, 31))

    # ------------------------------------------------------------------
    # États et transitions
    # ------------------------------------------------------------------
    def test_transition_draft_to_planned(self):
        intervention = self._create_intervention()
        intervention.action_plan()
        self.assertEqual(intervention.state, "planned")

    def test_transition_draft_to_cancelled(self):
        intervention = self._create_intervention()
        intervention.action_cancel()
        self.assertEqual(intervention.state, "cancelled")

    def test_transition_planned_to_done(self):
        intervention = self._create_intervention(date_actual=date(2026, 3, 20))
        intervention.action_plan()
        intervention.action_done()
        self.assertEqual(intervention.state, "done")

    def test_done_requires_actual_date(self):
        intervention = self._create_intervention()
        intervention.action_plan()
        with self.assertRaises(UserError):
            intervention.action_done()

    def test_forbidden_transitions(self):
        intervention = self._create_intervention()
        with self.assertRaises(UserError):
            intervention.action_done()
        intervention.action_plan()
        with self.assertRaises(UserError):
            intervention.action_plan()

    def test_direct_state_write_rejected(self):
        intervention = self._create_intervention()
        with self.assertRaises(AccessError):
            intervention.write({"state": "planned"})

    def test_done_intervention_is_protected(self):
        intervention = self._create_intervention(date_actual=date(2026, 3, 20))
        intervention.action_plan()
        intervention.action_done()
        with self.assertRaises(UserError):
            intervention.write({"date_actual": date(2026, 3, 21)})
        with self.assertRaises(UserError):
            intervention.action_cancel()
        with self.assertRaises(UserError):
            intervention.action_plan()

    # ------------------------------------------------------------------
    # Archivage et historique
    # ------------------------------------------------------------------
    def test_archive_and_unarchive(self):
        intervention = self._create_intervention()
        intervention.write({"active": False})
        self.assertFalse(intervention.active)
        intervention.write({"active": True})
        self.assertTrue(intervention.active)

    def test_interventions_kept_when_cycle_archived(self):
        intervention = self._create_intervention()
        self.cycle.write({"active": False})
        self.assertTrue(intervention.exists())
        self.assertEqual(intervention.crop_cycle_id, self.cycle)
        archived_cycle = (
            self.env["gest_agri.crop.cycle"]
            .with_context(active_test=False)
            .browse(self.cycle.id)
        )
        self.assertIn(intervention, archived_cycle.intervention_ids)

    def test_done_intervention_cannot_be_deleted_by_manager(self):
        intervention = self._create_intervention(date_actual=date(2026, 3, 20))
        intervention.action_plan()
        intervention.action_done()
        with self.assertRaises(AccessError):
            intervention.with_user(self.manager).unlink()

    # ------------------------------------------------------------------
    # Relations inverses
    # ------------------------------------------------------------------
    def test_intervention_ids_relation(self):
        intervention = self._create_intervention()
        self.assertIn(intervention, self.cycle.intervention_ids)

    def test_intervention_count_includes_archived(self):
        intervention = self._create_intervention()
        self.assertEqual(self.cycle.intervention_count, 1)
        intervention.write({"active": False})
        self.assertEqual(self.cycle.intervention_count, 1)

    def test_intervention_count_starts_at_zero(self):
        self.assertEqual(self.cycle.intervention_count, 0)

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_user_rights(self):
        intervention = self._create_intervention()
        self.assertTrue(
            intervention.with_user(self.user_a).read(["name"])
        )
        with self.assertRaises(AccessError):
            intervention.with_user(self.user_a).write({"name": "Interdit"})

    def test_manager_rights(self):
        cycle = self.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": self.plot_a2.id,
                "crop_type_id": self.crop_type.id,
                "date_start": date(2026, 3, 1),
                "date_end_planned": date(2026, 10, 31),
            }
        )
        intervention = self.env["gest_agri.crop.intervention"].with_user(
            self.manager
        ).create(
            {
                "name": "Intervention gestionnaire",
                "crop_cycle_id": cycle.id,
                "operation_type_id": self.operation_type.id,
                "date_planned": date(2026, 4, 1),
            }
        )
        self.assertTrue(intervention.id)
        intervention.with_user(self.manager).write({"name": "Intervention modifiée"})
        with self.assertRaises(AccessError):
            intervention.with_user(self.manager).unlink()

    def test_admin_rights(self):
        intervention = self._create_intervention()
        intervention.with_user(self.admin).write({"name": "Intervention admin"})
        self.assertEqual(intervention.name, "Intervention admin")

    def test_multi_company_isolation(self):
        other_company = self.env["res.company"].create({"name": "Société interventions B"})
        other_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Ferme société B interventions",
                "code": "INT-OTHER",
                "company_id": other_company.id,
                "total_area": 10.0,
            }
        )
        other_plot = cls.env["gest_agri.plot"].create(
            {
                "name": "Parcelle société B interventions",
                "code": "PINT-B2",
                "farm_id": other_farm.id,
                "area": 5.0,
            }
        )
        other_type = cls.env["gest_agri.crop.type"].create(
            {"name": "Culture B interventions", "code": "BINT2", "company_id": other_company.id}
        )
        other_intervention = cls.env["gest_agri.crop.intervention"].create(
            {
                "name": "Intervention autre société",
                "crop_cycle_id": cls.env["gest_agri.crop.cycle"].create(
                    {
                        "plot_id": other_plot.id,
                        "crop_type_id": other_type.id,
                        "date_start": date(2026, 3, 1),
                    }
                ).id,
                "operation_type_id": self.operation_type.id,
                "date_planned": date(2026, 4, 1),
            }
        )
        visible = (
            cls.env["gest_agri.crop.intervention"].with_user(self.user_a).search([])
        )
        self.assertNotIn(other_intervention, visible)
        with self.assertRaises(AccessError):
            other_intervention.with_user(self.admin).read(["name"])

    # ------------------------------------------------------------------
    # Navigation et non-régression
    # ------------------------------------------------------------------
    def test_navigation_from_cycle(self):
        action = self.cycle.action_view_interventions()
        self.assertEqual(action["res_model"], "gest_agri.crop.intervention")
        self.assertIn(("crop_cycle_id", "=", self.cycle.id), action["domain"])

    def test_interventions_do_not_alter_cycle_rules(self):
        cycle = self.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": self.plot_a.id,
                "crop_type_id": self.crop_type.id,
                "date_start": date(2026, 3, 1),
                "date_end_planned": date(2026, 10, 31),
            }
        )
        self._create_intervention(cycle=cycle, date_planned=date(2026, 4, 1))
        # Le chevauchement des cultures reste interdit.
        with self.assertRaises(ValidationError):
            self.env["gest_agri.crop.cycle"].create(
                {
                    "plot_id": self.plot_a.id,
                    "crop_type_id": self.crop_type.id,
                    "date_start": date(2026, 5, 1),
                    "date_end_planned": date(2026, 9, 30),
                }
            )
        # Les transitions de cycle restent inchangées.
        cycle.action_plant()
        self.assertEqual(cycle.state, "planted")

    def test_multiple_interventions_same_day_allowed(self):
        self._create_intervention(
            name="Labour du matin", date_planned=date(2026, 3, 15)
        )
        self._create_intervention(
            name="Epandage du soir",
            operation_type_id=self.operation_type_2.id,
            date_planned=date(2026, 3, 15),
        )
        self.assertEqual(self.cycle.intervention_count, 2)
