# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestLivestock(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")

        cls.user_a = cls._create_user("live_user_a", [cls.base_user, cls.group_user])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme élevage A", "code": "ELEA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme élevage B", "code": "ELEB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create({"name": "Site A", "code": "SA", "farm_id": cls.farm_a.id})
        cls.species = cls.env["gest_agri.livestock.species"].create(
            {"name": "Bovin", "code": "BOV", "company_id": cls.company.id}
        )
        cls.breed = cls.env["gest_agri.livestock.breed"].create(
            {"name": "Holstein", "code": "HOL", "species_id": cls.species.id, "company_id": cls.company.id}
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle A", "code": "PA", "farm_id": cls.farm_a.id, "area": 10.0}
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

    def _create_animal(self, **kwargs):
        vals = {
            "name": "Vache 1",
            "species_id": self.species.id,
            "sex": "female",
            "farm_id": self.farm_a.id,
        }
        vals.update(kwargs)
        return self.env["gest_agri.animal"].create(vals)

    def _create_lot(self, **kwargs):
        vals = {
            "name": "Lot A",
            "species_id": self.species.id,
            "farm_id": self.farm_a.id,
        }
        vals.update(kwargs)
        return self.env["gest_agri.animal.lot"].create(vals)

    # ------------------------------------------------------------------
    # Animaux
    # ------------------------------------------------------------------
    def test_animal_creation(self):
        a = self._create_animal()
        self.assertTrue(a.id)
        self.assertTrue(a.reference.startswith("ANI/"))

    def test_animal_species_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.animal"].create({"name": "Sans espèce", "sex": "male", "farm_id": self.farm_a.id})

    def test_animal_sex_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.animal"].create({"name": "Sans sexe", "species_id": self.species.id, "farm_id": self.farm_a.id})

    def test_animal_farm_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.animal"].create({"name": "Sans ferme", "species_id": self.species.id, "sex": "male"})

    def test_animal_official_id_unique(self):
        self._create_animal(official_id="FR123")
        with self.assertRaises(Exception):
            self._create_animal(official_id="FR123")

    def test_animal_breed_species_coherence(self):
        other_species = self.env["gest_agri.livestock.species"].create(
            {"name": "Ovin", "code": "OVI", "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError):
            self._create_animal(breed_id=self.breed.id, species_id=other_species.id)

    def test_animal_site_farm_coherence(self):
        other_site = self.env["gest_agri.site"].create({"name": "S2", "code": "S2", "farm_id": self.farm_b.id})
        with self.assertRaises(ValidationError):
            self._create_animal(site_id=other_site.id)

    def test_animal_lot_farm_coherence(self):
        other_farm = self.farm_b
        other_lot = self._create_lot(farm_id=other_farm.id)
        with self.assertRaises(ValidationError):
            self._create_animal(lot_id=other_lot.id)

    def test_animal_state_transitions(self):
        a = self._create_animal()
        a.action_activate()
        self.assertEqual(a.state, "active")
        a.action_sell()
        self.assertEqual(a.state, "sold")

    def test_animal_state_transitions2(self):
        a = self._create_animal()
        a.action_activate()
        a.action_die()
        self.assertEqual(a.state, "dead")

    def test_animal_state_transitions3(self):
        a = self._create_animal()
        a.action_activate()
        a.action_retire()
        self.assertEqual(a.state, "retired")

    def test_animal_direct_state_write_forbidden(self):
        a = self._create_animal()
        with self.assertRaises(AccessError):
            a.write({"state": "active"})

    def test_animal_archivable(self):
        a = self._create_animal()
        a.write({"active": False})
        self.assertFalse(a.active)

    # ------------------------------------------------------------------
    # Lots
    # ------------------------------------------------------------------
    def test_lot_creation(self):
        lot = self._create_lot()
        self.assertTrue(lot.id)
        self.assertTrue(lot.reference.startswith("LOT/"))

    def test_lot_species_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.animal.lot"].create({"name": "Sans espèce", "farm_id": self.farm_a.id})

    def test_lot_farm_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.animal.lot"].create({"name": "Sans ferme", "species_id": self.species.id})

    def test_lot_member_count(self):
        lot = self._create_lot()
        a = self._create_animal(lot_id=lot.id)
        lot.invalidate_recordset()
        self.assertEqual(lot.member_count, 1)

    def test_lot_breed_species_coherence(self):
        other_species = self.env["gest_agri.livestock.species"].create(
            {"name": "Ovin", "code": "OVI", "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError):
            self._create_lot(breed_id=self.breed.id, species_id=other_species.id)

    def test_lot_site_farm_coherence(self):
        other_site = self.env["gest_agri.site"].create({"name": "S2", "code": "S2", "farm_id": self.farm_b.id})
        with self.assertRaises(ValidationError):
            self._create_lot(site_id=other_site.id)

    def test_lot_state_transitions(self):
        lot = self._create_lot()
        lot.action_activate()
        self.assertEqual(lot.state, "active")
        lot.action_close()
        self.assertEqual(lot.state, "closed")

    def test_lot_direct_state_write_forbidden(self):
        lot = self._create_lot()
        with self.assertRaises(AccessError):
            lot.write({"state": "active"})

    def test_lot_delete_with_members_forbidden(self):
        lot = self._create_lot()
        self._create_animal(lot_id=lot.id)
        with self.assertRaises(UserError):
            lot.unlink()

    def test_lot_delete_empty_allowed(self):
        lot = self._create_lot()
        lot.unlink()
        self.assertFalse(self.env["gest_agri.animal.lot"].browse(lot.id).exists())

    def test_animal_lot_assignment(self):
        lot = self._create_lot()
        a = self._create_animal(lot_id=lot.id)
        self.assertEqual(a.lot_id, lot)

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_parse_and_install(self):
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "gestion_agricole")]))

    def test_animal_isolation(self):
        other_farm = self.farm_b
        other_animal = self._create_animal(farm_id=other_farm.id, species_id=self.species.id)
        # user_a has access to farm_a only
        visible = self.env["gest_agri.animal"].with_user(self.user_a).search([])
        self.assertNotIn(other_animal, visible)

    # ------------------------------------------------------------------
    # Compléments
    # ------------------------------------------------------------------
    def test_animal_official_id_optional(self):
        a = self._create_animal(official_id=None)
        self.assertTrue(a.id)
        self.assertFalse(a.official_id)

    def test_animal_entry_date(self):
        a = self._create_animal(entry_date=date(2026, 1, 15))
        self.assertEqual(a.entry_date, date(2026, 1, 15))

    def test_animal_origin(self):
        a = self._create_animal(origin="Achat")
        self.assertEqual(a.origin, "Achat")

    def test_animal_notes(self):
        a = self._create_animal(notes="Obs")
        self.assertEqual(a.notes, "Obs")

    def test_lot_constitution_date(self):
        lot = self._create_lot(constitution_date=date(2026, 3, 1))
        self.assertEqual(lot.constitution_date, date(2026, 3, 1))

    def test_lot_notes(self):
        lot = self._create_lot(notes="Obs lot")
        self.assertEqual(lot.notes, "Obs lot")

    def test_animal_lot_assignment_updates_lot(self):
        lot = self._create_lot()
        a = self._create_animal()
        a.write({"lot_id": lot.id})
        self.assertEqual(a.lot_id, lot)
        lot.invalidate_recordset()
        self.assertEqual(lot.member_count, 1)

    def test_animal_multiple_in_lot(self):
        lot = self._create_lot()
        a1 = self._create_animal(lot_id=lot.id)
        a2 = self._create_animal(lot_id=lot.id, name="Vache 2")
        lot.invalidate_recordset()
        self.assertEqual(lot.member_count, 2)

    def test_animal_state_retired_from_active(self):
        a = self._create_animal()
        a.action_activate()
        a.action_retire()
        self.assertEqual(a.state, "retired")

    def test_lot_state_closed_from_active(self):
        lot = self._create_lot()
        lot.action_activate()
        lot.action_close()
        self.assertEqual(lot.state, "closed")
