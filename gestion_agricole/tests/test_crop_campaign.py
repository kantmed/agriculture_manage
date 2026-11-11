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


class TestCropCampaign(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")
        cls.base_user = cls.env.ref("base.group_user")

        cls.user_a = cls._create_user(
            "campaign_user_a", [cls.base_user, cls.group_user]
        )
        cls.user_b = cls._create_user(
            "campaign_user_b", [cls.base_user, cls.group_user]
        )
        cls.manager = cls._create_user(
            "campaign_manager", [cls.base_user, cls.group_manager]
        )
        cls.admin = cls._create_user(
            "campaign_admin", [cls.base_user, cls.group_admin]
        )
        cls.farm_owner = cls.env["res.users"].create(
            {
                "name": "Propriétaire technique campagnes",
                "login": "campaign_farm_owner",
                "email": "campaign_farm_owner@example.com",
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, [cls.base_user.id, cls.group_user.id])],
            }
        )

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine campagnes A",
                "code": "CAM-A",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {
                "name": "Domaine campagnes B",
                "code": "CAM-B",
                "company_id": cls.company.id,
                "manager_id": cls.farm_owner.id,
                "total_area": 100.0,
            }
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {
                "name": "Parcelle campagnes A",
                "code": "PCMA",
                "farm_id": cls.farm_a.id,
                "area": 10.0,
            }
        )
        cls.crop_type = cls.env["gest_agri.crop.type"].create(
            {"name": "Blé campagnes", "code": "BLEC", "company_id": cls.company.id}
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

        cls.campaign_a = cls._create_campaign(farm=cls.farm_a, name="Campagne A")
        cls.campaign_b = cls._create_campaign(farm=cls.farm_b, name="Campagne B")

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
    def _create_campaign(cls, farm=None, name="Campagne", **kwargs):
        values = {
            "name": name,
            "farm_id": (farm or cls.farm_a).id,
            "date_start": date(2026, 1, 1),
            "date_end": date(2026, 12, 31),
        }
        values.update(kwargs)
        return cls.env["gest_agri.crop.campaign"].create(values)

    # ------------------------------------------------------------------
    # Création, identification, société
    # ------------------------------------------------------------------
    def test_create_campaign(self):
        campaign = self._create_campaign(name="Campagne céréalière")
        self.assertEqual(campaign.name, "Campagne céréalière")
        self.assertEqual(campaign.state, "draft")
        self.assertTrue(campaign.active)
        self.assertTrue(campaign.id)

    def test_code_generated_and_unique(self):
        first = self._create_campaign(name="Campagne code 1")
        second = self._create_campaign(name="Campagne code 2")
        self.assertTrue(first.code.startswith("CAM/"))
        self.assertTrue(second.code.startswith("CAM/"))
        self.assertNotEqual(first.code, second.code)

    def test_code_uniqueness_on_write_rejected(self):
        first = self._create_campaign(name="Campagne unique 1")
        second = self._create_campaign(name="Campagne unique 2")
        with self.assertRaises(UNIQUE_ERRORS):
            second.write({"code": first.code})

    def test_code_uniqueness_on_create_rejected(self):
        first = self._create_campaign(name="Campagne unique 3")
        with self.assertRaises(UNIQUE_ERRORS):
            self._create_campaign(name="Campagne unique 4", code=first.code)

    def test_farm_required(self):
        with self.assertRaises(REQUIRED_ERRORS):
            self.env["gest_agri.crop.campaign"].create(
                {"name": "Campagne sans exploitation", "date_start": date(2026, 1, 1)}
            )

    def test_company_derived_from_farm(self):
        self.assertEqual(self.campaign_a.company_id, self.farm_a.company_id)
        self.assertEqual(self.campaign_a.company_id, self.company)

        other_company = self.env["res.company"].create({"name": "Société campagnes B"})
        other_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Ferme autre société campagnes",
                "code": "CAM-OTHER",
                "company_id": other_company.id,
                "total_area": 10.0,
            }
        )
        other_campaign = self._create_campaign(farm=other_farm, name="Campagne autre société")
        self.assertEqual(other_campaign.company_id, other_company)

    def test_farm_inverse_relation(self):
        self.assertIn(self.campaign_a, self.farm_a.crop_campaign_ids)

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    def test_planned_end_before_start_rejected(self):
        campaign = self._create_campaign(name="Campagne dates 1")
        with self.assertRaises(ValidationError):
            campaign.write({"date_end": date(2025, 12, 31)})

    def test_actual_end_before_start_rejected(self):
        campaign = self._create_campaign(name="Campagne dates 2")
        with self.assertRaises(ValidationError):
            campaign.write({"date_end_actual": date(2025, 12, 31)})

    # ------------------------------------------------------------------
    # États et transitions
    # ------------------------------------------------------------------
    def test_draft_to_active(self):
        campaign = self._create_campaign(name="Campagne activation")
        campaign.action_activate()
        self.assertEqual(campaign.state, "active")

    def test_draft_to_cancelled(self):
        campaign = self._create_campaign(name="Campagne annulation brouillon")
        campaign.action_cancel()
        self.assertEqual(campaign.state, "cancelled")

    def test_active_to_closed_with_actual_date(self):
        campaign = self._create_campaign(name="Campagne clôture")
        campaign.action_activate()
        campaign.write({"date_end_actual": date(2026, 11, 30)})
        campaign.action_close()
        self.assertEqual(campaign.state, "closed")

    def test_close_without_actual_date_rejected(self):
        campaign = self._create_campaign(name="Campagne clôture sans date")
        campaign.action_activate()
        with self.assertRaises(UserError):
            campaign.action_close()

    def test_active_to_cancelled(self):
        campaign = self._create_campaign(name="Campagne annulation en cours")
        campaign.action_activate()
        campaign.action_cancel()
        self.assertEqual(campaign.state, "cancelled")

    def test_forbidden_transitions(self):
        draft = self._create_campaign(name="Campagne transitions brouillon")
        with self.assertRaises(UserError):
            draft.action_close()

        closed = self._create_campaign(
            name="Campagne transitions clôturée",
            date_end_actual=date(2026, 6, 30),
        )
        closed.action_activate()
        closed.action_close()
        with self.assertRaises(UserError):
            closed.action_activate()
        with self.assertRaises(UserError):
            closed.action_cancel()

        cancelled = self._create_campaign(name="Campagne transitions annulée")
        cancelled.action_cancel()
        with self.assertRaises(UserError):
            cancelled.action_activate()

    def test_direct_state_write_rejected(self):
        campaign = self._create_campaign(name="Campagne état direct")
        with self.assertRaises(AccessError):
            campaign.write({"state": "active"})

    def test_multiple_active_campaigns_allowed(self):
        first = self._create_campaign(name="Campagne multiple 1")
        second = self._create_campaign(name="Campagne multiple 2")
        first.action_activate()
        second.action_activate()
        self.assertEqual(first.state, "active")
        self.assertEqual(second.state, "active")

    # ------------------------------------------------------------------
    # Protection des données métier
    # ------------------------------------------------------------------
    def test_closed_campaign_protected(self):
        campaign = self._create_campaign(
            name="Campagne protégée clôturée", date_end_actual=date(2026, 6, 30)
        )
        campaign.action_activate()
        campaign.action_close()
        with self.assertRaises(UserError):
            campaign.write({"name": "Nom interdit"})
        with self.assertRaises(UserError):
            campaign.write({"date_start": date(2025, 1, 1)})
        with self.assertRaises(UserError):
            campaign.write({"notes": "Note interdite"})
        self.assertEqual(campaign.name, "Campagne protégée clôturée")

    def test_cancelled_campaign_protected(self):
        campaign = self._create_campaign(name="Campagne protégée annulée")
        campaign.action_cancel()
        with self.assertRaises(UserError):
            campaign.write({"name": "Nom interdit"})
        with self.assertRaises(UserError):
            campaign.write({"description": "Description interdite"})

    def test_archive_and_unarchive(self):
        campaign = self._create_campaign(name="Campagne archivage")
        campaign.write({"active": False})
        self.assertNotIn(
            campaign,
            self.env["gest_agri.crop.campaign"].search([("id", "=", campaign.id)]),
        )
        self.assertIn(
            campaign,
            self.env["gest_agri.crop.campaign"]
            .with_context(active_test=False)
            .search([("id", "=", campaign.id)]),
        )
        campaign.write({"active": True})
        self.assertIn(
            campaign,
            self.env["gest_agri.crop.campaign"].search([("id", "=", campaign.id)]),
        )

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_acl_user_read_only(self):
        self.assertEqual(
            self.campaign_a.with_user(self.user_a).read(["name"])[0]["name"],
            self.campaign_a.name,
        )
        with self.assertRaises(AccessError):
            self.env["gest_agri.crop.campaign"].with_user(self.user_a).create(
                {
                    "name": "Campagne interdite",
                    "farm_id": self.farm_a.id,
                    "date_start": date(2026, 1, 1),
                }
            )
        with self.assertRaises(AccessError):
            self.campaign_a.with_user(self.user_a).write({"notes": "Interdit"})
        with self.assertRaises(AccessError):
            self.campaign_a.with_user(self.user_a).unlink()

    def test_acl_manager_create_write_no_delete(self):
        campaign = (
            self.env["gest_agri.crop.campaign"]
            .with_user(self.manager)
            .create(
                {
                    "name": "Campagne gérée",
                    "farm_id": self.farm_a.id,
                    "date_start": date(2027, 1, 1),
                }
            )
        )
        self.assertTrue(campaign.id)
        campaign.with_user(self.manager).write({"notes": "Suivi responsable"})
        with self.assertRaises(AccessError):
            campaign.with_user(self.manager).unlink()
        with self.assertRaises(AccessError):
            self.env["gest_agri.crop.campaign"].with_user(self.manager).create(
                {
                    "name": "Campagne non gérée",
                    "farm_id": self.farm_b.id,
                    "date_start": date(2027, 1, 1),
                }
            )

    def test_acl_admin_full(self):
        campaign = self._create_campaign(
            name="Campagne admin",
            date_start=date(2027, 1, 1),
            date_end=date(2027, 12, 31),
        )
        campaign.with_user(self.admin).write({"notes": "Gestion admin"})
        self.assertEqual(campaign.notes, "Gestion admin")
        campaign.with_user(self.admin).unlink()
        self.assertFalse(campaign.exists())

    def test_multi_company_isolation(self):
        other_company = self.env["res.company"].create({"name": "Société campagnes C"})
        other_farm = self.env["gest_agri.farm"].create(
            {
                "name": "Ferme société C",
                "code": "CAM-C",
                "company_id": other_company.id,
                "total_area": 10.0,
            }
        )
        other_campaign = self._create_campaign(farm=other_farm, name="Campagne société C")
        visible = self.env["gest_agri.crop.campaign"].with_user(self.user_a).search([])
        self.assertNotIn(other_campaign, visible)
        with self.assertRaises(AccessError):
            other_campaign.with_user(self.admin).read(["name"])

    # ------------------------------------------------------------------
    # Non-régression : cycles de culture
    # ------------------------------------------------------------------
    def test_crop_cycle_untouched(self):
        # Prompt 52 ajoute volontairement la relation « campaign_id » au cycle.
        self.assertIn("campaign_id", self.env["gest_agri.crop.cycle"]._fields)
        self.assertNotIn("campaign_ids", self.env["gest_agri.crop.cycle"]._fields)

        cycle = self.env["gest_agri.crop.cycle"].create(
            {
                "plot_id": self.plot_a.id,
                "crop_type_id": self.crop_type.id,
                "date_start": date(2025, 1, 1),
            }
        )
        cycle_name = cycle.name
        self._create_campaign(name="Campagne sans effet sur les cycles")
        self.assertEqual(cycle.name, cycle_name)
        self.assertEqual(cycle.state, "planned")
        self.assertFalse(cycle.campaign_id)
