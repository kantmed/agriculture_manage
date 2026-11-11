# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestCropCycleCampaign(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")
        cls.base_user = cls.env.ref("base.group_user")

        cls.user_a = cls._create_user(
            "link_user_a", [cls.base_user, cls.group_user]
        )
        cls.user_b = cls._create_user(
            "link_user_b", [cls.base_user, cls.group_user]
        )
        cls.manager = cls._create_user(
            "link_manager", [cls.base_user, cls.group_manager]
        )
        cls.admin = cls._create_user(
            "link_admin", [cls.base_user, cls.group_admin]
        )
        cls.farm_owner = cls.env["res.users"].create(
            {
                "name": "Propriétaire technique liaison",
                "login": "link_farm_owner",
                "email": "link_farm_owner@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [cls.base_user.id, cls.group_user.id])],
            }
        )

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine liaison A",
                "code": "LNK-A",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine liaison B",
                "code": "LNK-B",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {
                "name": "Parcelle liaison A",
                "code": "PLNK-A",
                "farm_id": cls.farm_a.id,
                "area": 10.0,
            }
        )
        cls.plot_b = cls.env["gest_agri.plot"].create(
            {
                "name": "Parcelle liaison B",
                "code": "PLNK-B",
                "farm_id": cls.farm_b.id,
                "area": 5.0,
            }
        )
        cls.crop_type = cls.env["gest_agri.crop.type"].create(
            {"name": "Blé liaison", "code": "BLLNK", "company_id": cls.company.id}
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

        cls.campaign_draft = cls._create_campaign(
            name="Campagne liaison brouillon",
            date_start=date(2026, 1, 1),
            date_end=date(2026, 12, 31),
        )
        cls.campaign_open = cls._create_campaign(
            name="Campagne liaison ouverte",
            date_start=date(2026, 1, 1),
            date_end=False,
        )
        cls.campaign_active = cls._create_campaign(
            name="Campagne liaison active",
            date_start=date(2026, 1, 1),
            date_end=date(2026, 12, 31),
            date_end_actual=date(2026, 11, 30),
        )
        cls.campaign_active.action_activate()
        cls.campaign_closed = cls._create_campaign(
            name="Campagne liaison clôturée",
            date_start=date(2026, 1, 1),
            date_end=date(2026, 12, 31),
            date_end_actual=date(2026, 11, 30),
        )
        cls.campaign_closed.action_activate()
        cls.campaign_closed.action_close()
        cls.campaign_cancelled = cls._create_campaign(
            name="Campagne liaison annulée",
            date_start=date(2026, 1, 1),
            date_end=date(2026, 12, 31),
        )
        cls.campaign_cancelled.action_cancel()
        cls.campaign_archived = cls._create_campaign(
            name="Campagne liaison archivée",
            date_start=date(2026, 1, 1),
            date_end=date(2026, 12, 31),
        )
        cls.campaign_archived.write({"active": False})
        cls.campaign_b = cls._create_campaign(
            name="Campagne liaison autre exploitation",
            farm=cls.farm_b,
            date_start=date(2026, 1, 1),
            date_end=date(2026, 12, 31),
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

    @classmethod
    def _create_campaign(cls, name="Campagne liaison", farm=None, **kwargs):
        values = {
            "name": name,
            "farm_id": (farm or cls.farm_a).id,
            "date_start": date(2026, 1, 1),
        }
        values.update(kwargs)
        return cls.env["gest_agri.crop.campaign"].create(values)

    def _create_cycle(self, campaign=None, plot=None, start=None, planned=None,
                      actual=None, **kwargs):
        values = {
            "plot_id": (plot or self.plot_a).id,
            "crop_type_id": self.crop_type.id,
            "date_start": start or date(2026, 2, 1),
        }
        if campaign:
            values["campaign_id"] = campaign.id
        if planned:
            values["date_end_planned"] = planned
        if actual:
            values["date_end_actual"] = actual
        values.update(kwargs)
        return self.env["gest_agri.crop.cycle"].create(values)

    # ------------------------------------------------------------------
    # Relation
    # ------------------------------------------------------------------
    def test_cycle_without_campaign(self):
        cycle = self._create_cycle()
        self.assertFalse(cycle.campaign_id)

    def test_cycle_with_campaign(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft, planned=date(2026, 6, 30)
        )
        self.assertEqual(cycle.campaign_id, self.campaign_draft)

    def test_inverse_relation_and_count(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft, planned=date(2026, 6, 30)
        )
        self.assertIn(cycle, self.campaign_draft.crop_cycle_ids)
        self.assertEqual(self.campaign_draft.crop_cycle_count, 1)

    # ------------------------------------------------------------------
    # Exploitation et société
    # ------------------------------------------------------------------
    def test_other_farm_campaign_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_cycle(
                campaign=self.campaign_b, planned=date(2026, 6, 30)
            )

    def test_other_company_campaign_rejected(self):
        other_company = self.env["res.company"].create({"name": "Société liaison B"})
        other_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Ferme société liaison",
                "code": "LNK-OTHER",
                "company_id": other_company.id,
                "total_area": 10.0,
            }
        )
        other_campaign = self._create_campaign(
            name="Campagne autre société",
            farm=other_farm,
            date_end=date(2026, 12, 31),
        )
        with self.assertRaises((UserError, ValidationError)):
            self._create_cycle(
                campaign=other_campaign, planned=date(2026, 6, 30)
            )

    # ------------------------------------------------------------------
    # Périodes
    # ------------------------------------------------------------------
    def test_cycle_start_before_campaign_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_cycle(
                campaign=self.campaign_draft,
                start=date(2025, 12, 31),
                planned=date(2026, 3, 31),
            )

    def test_cycle_end_after_campaign_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_cycle(
                campaign=self.campaign_draft,
                start=date(2026, 2, 1),
                planned=date(2027, 1, 15),
            )

    def test_open_end_in_campaign_with_end_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_cycle(campaign=self.campaign_draft)

    def test_open_end_in_campaign_without_end_accepted(self):
        cycle = self._create_cycle(campaign=self.campaign_open)
        self.assertEqual(cycle.campaign_id, self.campaign_open)

    def test_effective_end_uses_actual_date(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft,
            start=date(2026, 2, 1),
            planned=date(2027, 6, 30),
            actual=date(2026, 11, 30),
        )
        self.assertEqual(cycle.campaign_id, self.campaign_draft)

    # ------------------------------------------------------------------
    # États de campagne
    # ------------------------------------------------------------------
    def test_closed_campaign_rejected(self):
        with self.assertRaises(UserError):
            self._create_cycle(
                campaign=self.campaign_closed, planned=date(2026, 6, 30)
            )

    def test_cancelled_campaign_rejected(self):
        with self.assertRaises(UserError):
            self._create_cycle(
                campaign=self.campaign_cancelled, planned=date(2026, 6, 30)
            )

    def test_archived_campaign_rejected(self):
        with self.assertRaises(UserError):
            self._create_cycle(
                campaign=self.campaign_archived, planned=date(2026, 6, 30)
            )

    def test_draft_campaign_accepted(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft, planned=date(2026, 6, 30)
        )
        self.assertEqual(self.campaign_draft.state, "draft")
        self.assertTrue(cycle.id)

    def test_active_campaign_accepted(self):
        cycle = self._create_cycle(
            campaign=self.campaign_active, planned=date(2026, 6, 30)
        )
        self.assertEqual(self.campaign_active.state, "active")
        self.assertTrue(cycle.id)

    def test_detach_allowed(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft, planned=date(2026, 6, 30)
        )
        cycle.write({"campaign_id": False})
        self.assertFalse(cycle.campaign_id)

    def test_detach_from_closed_campaign_rejected(self):
        cycle = self._create_cycle(
            campaign=self.campaign_active, planned=date(2026, 6, 30)
        )
        self.campaign_active.action_close()
        with self.assertRaises(UserError):
            cycle.write({"campaign_id": False})

    # ------------------------------------------------------------------
    # Modification de la campagne
    # ------------------------------------------------------------------
    def test_campaign_start_change_incompatible(self):
        self._create_cycle(
            campaign=self.campaign_draft,
            start=date(2026, 2, 1),
            planned=date(2026, 6, 30),
        )
        with self.assertRaises(ValidationError):
            self.campaign_draft.write({"date_start": date(2026, 3, 1)})

    def test_campaign_end_change_incompatible(self):
        self._create_cycle(
            campaign=self.campaign_draft,
            start=date(2026, 2, 1),
            planned=date(2026, 9, 30),
        )
        with self.assertRaises(ValidationError):
            self.campaign_draft.write({"date_end": date(2026, 8, 31)})

    def test_campaign_farm_change_incompatible(self):
        self._create_cycle(
            campaign=self.campaign_draft, planned=date(2026, 6, 30)
        )
        with self.assertRaises(ValidationError):
            self.campaign_draft.write({"farm_id": self.farm_b.id})

    def test_campaign_compatible_change_allowed(self):
        self._create_cycle(
            campaign=self.campaign_draft,
            start=date(2026, 2, 1),
            planned=date(2026, 6, 30),
        )
        self.campaign_draft.write({"date_end": date(2027, 1, 31)})
        self.assertEqual(self.campaign_draft.date_end, date(2027, 1, 31))

    # ------------------------------------------------------------------
    # Conservation des relations
    # ------------------------------------------------------------------
    def test_archive_preserves_relations(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft, planned=date(2026, 6, 30)
        )
        self.campaign_draft.write({"active": False})
        self.assertEqual(cycle.campaign_id, self.campaign_draft)
        campaign = (
            self.env["gest_agri.crop.campaign"]
            .with_context(active_test=False)
            .browse(self.campaign_draft.id)
        )
        self.assertIn(cycle, campaign.crop_cycle_ids)

    def test_close_preserves_cycles(self):
        cycle = self._create_cycle(
            campaign=self.campaign_active, planned=date(2026, 6, 30)
        )
        self.campaign_active.action_close()
        self.assertTrue(cycle.exists())
        self.assertEqual(cycle.campaign_id, self.campaign_active)
        self.assertEqual(cycle.state, "planned")

    def test_cancel_preserves_cycles(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft, planned=date(2026, 6, 30)
        )
        self.campaign_draft.action_cancel()
        self.assertTrue(cycle.exists())
        self.assertEqual(cycle.campaign_id, self.campaign_draft)

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_user_can_read_but_not_attach(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft, planned=date(2026, 6, 30)
        )
        self.assertEqual(
            cycle.with_user(self.user_a).read(["name"])[0]["name"], cycle.name
        )
        self.assertEqual(
            self.campaign_draft.with_user(self.user_a).read(["name"])[0]["name"],
            self.campaign_draft.name,
        )
        with self.assertRaises(AccessError):
            cycle.with_user(self.user_a).write({"campaign_id": False})

    def test_manager_can_attach(self):
        cycle = self._create_cycle(
            start=date(2026, 8, 1), planned=date(2026, 9, 30)
        )
        cycle.with_user(self.manager).write(
            {"campaign_id": self.campaign_draft.id}
        )
        self.assertEqual(cycle.campaign_id, self.campaign_draft)

    def test_multi_company_isolation(self):
        other_company = self.env["res.company"].create({"name": "Société liaison C"})
        other_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Ferme société C liaison",
                "code": "LNK-C",
                "company_id": other_company.id,
                "total_area": 10.0,
            }
        )
        other_plot = self.env["gest_agri.plot"].create(
            {
                "name": "Parcelle société C liaison",
                "code": "PLNK-C",
                "farm_id": other_farm.id,
                "area": 5.0,
            }
        )
        other_type = self.env["gest_agri.crop.type"].create(
            {"name": "Culture société C", "code": "TYPEC", "company_id": other_company.id}
        )
        other_campaign = self._create_campaign(
            name="Campagne société C liaison",
            farm=other_farm,
            date_end=date(2026, 12, 31),
        )
        other_cycle = self.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": other_plot.id,
                "crop_type_id": other_type.id,
                "campaign_id": other_campaign.id,
                "date_start": date(2026, 2, 1),
                "date_end_planned": date(2026, 6, 30),
            }
        )
        self.assertNotIn(
            other_campaign,
            self.env["gest_agri.crop.campaign"].with_user(self.user_a).search([]),
        )
        with self.assertRaises(AccessError):
            other_cycle.with_user(self.admin).read(["name"])
        with self.assertRaises(AccessError):
            other_campaign.with_user(self.admin).read(["name"])

    # ------------------------------------------------------------------
    # Non-régression des règles du cycle
    # ------------------------------------------------------------------
    def test_cycle_transitions_unchanged(self):
        cycle = self._create_cycle(
            campaign=self.campaign_draft,
            start=date(2026, 2, 1),
            planned=date(2026, 12, 15),
            actual=date(2026, 12, 10),
        )
        cycle.action_plant()
        cycle.action_start()
        cycle.action_done()
        self.assertEqual(cycle.state, "done")
        with self.assertRaises(AccessError):
            cycle.write({"state": "planned"})

    def test_overlap_rules_unchanged(self):
        cancelled = self._create_cycle(
            campaign=self.campaign_draft,
            start=date(2026, 2, 1),
            planned=date(2026, 3, 31),
        )
        with self.assertRaises(ValidationError):
            self._create_cycle(
                start=date(2026, 3, 15),
                planned=date(2026, 4, 30),
            )
        cancelled.action_cancel()
        replacement = self._create_cycle(
            start=date(2026, 3, 15),
            planned=date(2026, 4, 30),
        )
        self.assertTrue(replacement.id)
