# -*- coding: utf-8 -*-
"""Tests for agriculture_manage_livestock."""
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestLivestockBasic(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.farm = cls.env["agriculture.farm"].create({
            "name": "Exploitation test élevage",
            "total_area": 10,
        })
        cls.species = cls.env["agriculture.livestock.species"].create({
            "name": "Ovins test",
            "code": "OVIN-TEST",
            "category": "ovine",
        })

    def test_species_create(self):
        self.assertEqual(self.species.code, "OVIN-TEST")

    def test_animal_create(self):
        animal = self.env["agriculture.livestock.animal"].create({
            "name": "Brebis test",
            "farm_id": self.farm.id,
            "species_id": self.species.id,
        })
        self.assertEqual(animal.state, "active")
        self.assertTrue(animal.code.startswith("ANI-") or animal.code == "Nouveau")

    def test_animal_birth_date_future_invalid(self):
        from odoo import fields
        from datetime import timedelta
        with self.assertRaises(ValidationError):
            self.env["agriculture.livestock.animal"].create({
                "name": "Animal futur",
                "farm_id": self.farm.id,
                "species_id": self.species.id,
                "birth_date": fields.Date.today() + timedelta(days=1),
            })

    def test_herd_create(self):
        herd = self.env["agriculture.livestock.herd"].create({
            "name": "Lot test",
            "farm_id": self.farm.id,
            "species_id": self.species.id,
            "tracking_mode": "batch",
            "quantity": 10,
        })
        self.assertEqual(herd.tracking_mode, "batch")
