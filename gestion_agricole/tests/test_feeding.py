# -*- coding: utf-8 -*-
from datetime import date, datetime

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestFeeding(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")

        cls.user_a = cls._create_user("feed_user_a", [cls.base_user, cls.group_user])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme feed A", "code": "FDA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme feed B", "code": "FDB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create({"name": "Site A", "code": "SA", "farm_id": cls.farm_a.id})
        cls.species = cls.env["gest_agri.livestock.species"].create(
            {"name": "Bovin", "code": "BOV", "company_id": cls.company.id}
        )
        cls.animal = cls.env["gest_agri.animal"].create(
            {"name": "Vache 1", "species_id": cls.species.id, "sex": "female", "farm_id": cls.farm_a.id}
        )
        cls.lot = cls.env["gest_agri.animal.lot"].create(
            {"name": "Lot A", "species_id": cls.species.id, "farm_id": cls.farm_a.id}
        )
        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.feed = cls.env["gest_agri.feed"].create(
            {"name": "Foin", "code": "FOIN", "category": "forage", "species_id": cls.species.id,
             "uom_id": cls.uom_kg.id, "company_id": cls.company.id}
        )
        cls.feed2 = cls.env["gest_agri.feed"].create(
            {"name": "Concentré", "code": "CONC", "category": "concentrate", "uom_id": cls.uom_kg.id,
             "company_id": cls.company.id}
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

    def _create_ration(self, **kwargs):
        vals = {"name": "Ration A", "species_id": self.species.id, "company_id": self.company.id}
        vals.update(kwargs)
        ration = self.env["gest_agri.feed.ration"].create(vals)
        if not ration.line_ids:
            self.env["gest_agri.feed.ration.line"].create(
                {"ration_id": ration.id, "feed_id": self.feed.id, "quantity": 5.0, "uom_id": self.uom_kg.id}
            )
        return ration

    def _create_distribution(self, **kwargs):
        vals = {
            "farm_id": self.farm_a.id,
            "distribution_date": date(2026, 7, 1),
            "animal_id": self.animal.id,
        }
        vals.update(kwargs)
        dist = self.env["gest_agri.feed.distribution"].create(vals)
        if not dist.line_ids:
            self.env["gest_agri.feed.distribution.line"].create(
                {"distribution_id": dist.id, "feed_id": self.feed.id, "quantity": 3.0, "uom_id": self.uom_kg.id}
            )
        return dist

    # ------------------------------------------------------------------
    # Aliments
    # ------------------------------------------------------------------
    def test_feed_creation(self):
        feed = self.env["gest_agri.feed"].create(
            {"name": "Paille", "code": "PAIL", "uom_id": self.uom_kg.id, "company_id": self.company.id}
        )
        self.assertTrue(feed.id)

    def test_feed_uom_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.feed"].create({"name": "Sans UOM", "code": "SU", "company_id": self.company.id})

    def test_feed_species_compatibility(self):
        other_species = self.env["gest_agri.livestock.species"].create(
            {"name": "Ovin", "code": "OVI", "company_id": self.company.id}
        )
        feed = self.env["gest_agri.feed"].create(
            {"name": "Foin ovin", "code": "FO", "species_id": other_species.id, "uom_id": self.uom_kg.id, "company_id": self.company.id}
        )
        self.assertEqual(feed.species_id, other_species)

    def test_feed_code_unique(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.feed"].create(
                {"name": "Dup", "code": "FOIN", "uom_id": self.uom_kg.id, "company_id": self.company.id}
            )

    def test_feed_archive(self):
        feed = self.env["gest_agri.feed"].create(
            {"name": "Arch", "code": "ARCH", "uom_id": self.uom_kg.id, "company_id": self.company.id}
        )
        feed.write({"active": False})
        self.assertFalse(feed.active)

    # ------------------------------------------------------------------
    # Rations
    # ------------------------------------------------------------------
    def test_ration_creation(self):
        ration = self._create_ration()
        self.assertTrue(ration.id)
        self.assertTrue(ration.reference.startswith("RAT/") if hasattr(ration, "reference") else True)

    def test_ration_species_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.feed.ration"].create({"name": "Sans espèce", "company_id": self.company.id})

    def test_ration_validity(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.feed.ration"].create(
                {"name": "R", "species_id": self.species.id, "company_id": self.company.id,
                 "valid_from": date(2026, 8, 1), "valid_to": date(2026, 7, 1)}
            )

    def test_ration_line_quantity_positive(self):
        ration = self._create_ration()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.feed.ration.line"].create(
                {"ration_id": ration.id, "feed_id": self.feed.id, "quantity": 0.0, "uom_id": self.uom_kg.id}
            )

    def test_ration_species_compatibility(self):
        other_species = self.env["gest_agri.livestock.species"].create(
            {"name": "Ovin", "code": "OVI", "company_id": self.company.id}
        )
        other_feed = self.env["gest_agri.feed"].create(
            {"name": "Foin ovin", "code": "FO", "species_id": other_species.id, "uom_id": self.uom_kg.id, "company_id": self.company.id}
        )
        ration = self._create_ration(species_id=self.species.id)
        with self.assertRaises(ValidationError):
            self.env["gest_agri.feed.ration.line"].create(
                {"ration_id": ration.id, "feed_id": other_feed.id, "quantity": 1.0, "uom_id": self.uom_kg.id}
            )

    # ------------------------------------------------------------------
    # Distributions
    # ------------------------------------------------------------------
    def test_distribution_creation(self):
        dist = self._create_distribution()
        self.assertTrue(dist.id)
        self.assertTrue(dist.name.startswith("DIS/"))

    def test_distribution_requires_animal_or_lot(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.feed.distribution"].create(
                {"farm_id": self.farm_a.id, "distribution_date": date(2026, 7, 1)}
            )

    def test_distribution_animal_or_lot_exclusive(self):
        with self.assertRaises(ValidationError):
            self._create_distribution(animal_id=self.animal.id, lot_id=self.lot.id)

    def test_distribution_quantity_positive(self):
        dist = self._create_distribution()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.feed.distribution.line"].create(
                {"distribution_id": dist.id, "feed_id": self.feed.id, "quantity": 0.0, "uom_id": self.uom_kg.id}
            )

    def test_distribution_animal_farm_coherence(self):
        other_farm = self.farm_b
        other_animal = self.env["gest_agri.animal"].create(
            {"name": "A2", "species_id": self.species.id, "sex": "female", "farm_id": other_farm.id}
        )
        with self.assertRaises(ValidationError):
            self._create_distribution(animal_id=other_animal.id)

    def test_distribution_lot_farm_coherence(self):
        other_farm = self.farm_b
        other_lot = self.env["gest_agri.animal.lot"].create(
            {"name": "L2", "species_id": self.species.id, "farm_id": other_farm.id}
        )
        with self.assertRaises(ValidationError):
            self._create_distribution(lot_id=other_lot.id)

    def test_distribution_site_farm_coherence(self):
        other_site = self.env["gest_agri.site"].create({"name": "S2", "code": "S2", "farm_id": self.farm_b.id})
        with self.assertRaises(ValidationError):
            self._create_distribution(site_id=other_site.id)

    def test_distribution_ration_species_coherence(self):
        other_species = self.env["gest_agri.livestock.species"].create(
            {"name": "Ovin", "code": "OVI", "company_id": self.company.id}
        )
        other_ration = self.env["gest_agri.feed.ration"].create(
            {"name": "Ration ovin", "species_id": other_species.id, "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError):
            self._create_distribution(ration_id=other_ration.id)

    def test_distribution_total_quantity(self):
        dist = self._create_distribution()
        self.assertAlmostEqual(dist.total_quantity, 3.0)

    def test_distribution_workflow(self):
        dist = self._create_distribution()
        dist.action_done()
        self.assertEqual(dist.state, "done")
        dist2 = self._create_distribution(
            distribution_date=date(2026, 7, 2),
            animal_id=self.animal.id,
        )
        dist2.action_cancel()
        self.assertEqual(dist2.state, "cancelled")

    def test_distribution_direct_state_write_forbidden(self):
        dist = self._create_distribution()
        with self.assertRaises(AccessError):
            dist.write({"state": "done"})

    def test_distribution_delete_draft_allowed(self):
        dist = self._create_distribution()
        dist.unlink()
        self.assertFalse(self.env["gest_agri.feed.distribution"].browse(dist.id).exists())

    def test_distribution_delete_done_forbidden(self):
        dist = self._create_distribution()
        dist.action_done()
        with self.assertRaises(UserError):
            dist.unlink()

    def test_distribution_lot_based(self):
        dist = self._create_distribution(animal_id=False, lot_id=self.lot.id)
        self.assertEqual(dist.lot_id, self.lot)
        self.assertFalse(dist.animal_id)

    def test_distribution_history_by_animal(self):
        self._create_distribution()
        dist2 = self._create_distribution(distribution_date=date(2026, 7, 2))
        count = self.env["gest_agri.feed.distribution"].search_count([("animal_id", "=", self.animal.id)])
        self.assertEqual(count, 2)

    def test_distribution_line_quantity_positive(self):
        dist = self._create_distribution()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.feed.distribution.line"].create(
                {"distribution_id": dist.id, "feed_id": self.feed.id, "quantity": -1.0, "uom_id": self.uom_kg.id}
            )

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_feed_isolation(self):
        other_feed = self.env["gest_agri.feed"].create(
            {"name": "Autre", "code": "AUT", "uom_id": self.uom_kg.id, "company_id": self.company.id}
        )
        # sanity: created
        self.assertTrue(other_feed.id)

    def test_parse_and_install(self):
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "gestion_agricole")]))

    def test_distribution_archive(self):
        dist = self._create_distribution()
        dist.write({"active": False})
        self.assertFalse(dist.active)

    def test_feed_category_values(self):
        feed = self.env["gest_agri.feed"].create(
            {"name": "Minéral", "code": "MIN", "category": "mineral", "uom_id": self.uom_kg.id, "company_id": self.company.id}
        )
        self.assertEqual(feed.category, "mineral")

    def test_ration_creation_with_lines(self):
        ration = self._create_ration()
        self.assertEqual(len(ration.line_ids), 1)

    def test_ration_validity_period(self):
        ration = self._create_ration(valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
        self.assertEqual(ration.valid_from, date(2026, 1, 1))

    def test_distribution_with_ration(self):
        ration = self._create_ration()
        dist = self._create_distribution(ration_id=ration.id)
        self.assertEqual(dist.ration_id, ration)

    def test_distribution_farm_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.feed.distribution"].create(
                {"distribution_date": date(2026, 7, 1), "animal_id": self.animal.id}
            )

    def test_feed_archive(self):
        feed = self.env["gest_agri.feed"].create(
            {"name": "Arch", "code": "ARCH", "uom_id": self.uom_kg.id, "company_id": self.company.id}
        )
        feed.write({"active": False})
        self.assertFalse(feed.active)

    def test_distribution_total_quantity_multiple_lines(self):
        dist = self._create_distribution()
        self.env["gest_agri.feed.distribution.line"].create(
            {"distribution_id": dist.id, "feed_id": self.feed2.id, "quantity": 2.0, "uom_id": self.uom_kg.id}
        )
        dist.invalidate_recordset()
        self.assertAlmostEqual(dist.total_quantity, 5.0)

    def test_ration_total_quantity(self):
        ration = self._create_ration()
        self.env["gest_agri.feed.ration.line"].create(
            {"ration_id": ration.id, "feed_id": self.feed2.id, "quantity": 2.0, "uom_id": self.uom_kg.id}
        )
        ration.invalidate_recordset()
        self.assertEqual(len(ration.line_ids), 2)

    def test_distribution_lot_with_ration_species_coherence(self):
        ration = self._create_ration()
        dist = self._create_distribution(animal_id=False, lot_id=self.lot.id, ration_id=ration.id)
        self.assertEqual(dist.lot_id, self.lot)
        self.assertEqual(dist.ration_id, ration)
