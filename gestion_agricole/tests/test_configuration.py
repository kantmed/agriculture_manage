# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestConfiguration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

    def test_referential_creation(self):
        farm_type = self.env["gest_agri.farm.type"].create(
            {
                "name": "Exploitation céréalière",
                "code": "CER",
                "company_id": self.company.id,
            }
        )
        self.assertEqual(farm_type.company_id, self.company)
        self.assertTrue(farm_type.active)

        global_type = self.env["gest_agri.farm.type"].create(
            {"name": "Exploitation générique", "code": "GEN", "company_id": False}
        )
        self.assertFalse(global_type.company_id)

        crop_type = self.env["gest_agri.crop.type"].create(
            {
                "name": "Blé dur",
                "code": "BLE",
                "crop_cycle": "annual",
                "company_id": self.company.id,
            }
        )
        variety = self.env["gest_agri.crop.variety"].create(
            {
                "name": "Blé dur variété locale",
                "code": "BLE-LOC",
                "crop_type_id": crop_type.id,
                "company_id": self.company.id,
            }
        )
        self.assertEqual(variety.crop_type_id, crop_type)

        species = self.env["gest_agri.livestock.species"].create(
            {"name": "Bovins", "code": "BOV", "company_id": self.company.id}
        )
        breed = self.env["gest_agri.livestock.breed"].create(
            {
                "name": "Holstein",
                "code": "HOL",
                "species_id": species.id,
                "company_id": self.company.id,
            }
        )
        self.assertEqual(breed.species_id, species)

        for model, label in [
            ("gest_agri.soil.type", "Limoneux"),
            ("gest_agri.operation.type", "Labour"),
            ("gest_agri.treatment.type", "Traitement fongique"),
            ("gest_agri.fertilizer.type", "Engrais organique"),
            ("gest_agri.irrigation.type", "Goutte-à-goutte"),
            ("gest_agri.equipment.type", "Tracteur"),
            ("gest_agri.building.type", "Hangar"),
            ("gest_agri.production.type", "Production laitière"),
        ]:
            record = self.env[model].create(
                {
                    "name": label,
                    "code": label[:3].upper(),
                    "company_id": self.company.id,
                }
            )
            self.assertTrue(record.id, f"{model} doit être créé")

    def test_code_uniqueness_in_same_scope(self):
        self.env["gest_agri.soil.type"].create(
            {"name": "Argileux", "code": "ARG", "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.soil.type"].create(
                {"name": "Argile lourde", "code": "arg", "company_id": self.company.id}
            )

    def test_global_code_conflicts_with_company_code(self):
        self.env["gest_agri.soil.type"].create(
            {"name": "Sableux", "code": "SAB", "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.soil.type"].create(
                {"name": "Sable global", "code": "SAB", "company_id": False}
            )

    def test_same_code_in_other_company(self):
        other_company = self.env["res.company"].create({"name": "Autre société"})
        self.env["gest_agri.soil.type"].create(
            {"name": "Calcaire", "code": "CAL", "company_id": self.company.id}
        )
        other_type = self.env["gest_agri.soil.type"].create(
            {"name": "Calcaire autre société", "code": "CAL", "company_id": other_company.id}
        )
        self.assertEqual(other_type.company_id, other_company)
