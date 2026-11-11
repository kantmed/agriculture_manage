# -*- coding: utf-8 -*-
import psycopg2

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


# L'index unique PostgreSQL est levé au moment de l'INSERT / de l'UPDATE,
# donc avant (ou à la place de) la contrainte Python. Au niveau web, Odoo
# convertit cette erreur en ValidationError avec le message de l'index
# (odoo/http/retrying.py -> model._sql_error_to_message) ; au niveau ORM,
# l'erreur brute psycopg2 est propagée. Les deux sont acceptées.
UNIQUE_ERRORS = (ValidationError, psycopg2.errors.UniqueViolation)


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
        with self.assertRaises(UNIQUE_ERRORS):
            self.env["gest_agri.soil.type"].create(
                {"name": "Argile lourde", "code": "arg", "company_id": self.company.id}
            )

    def test_global_code_conflicts_with_company_code(self):
        """Teste que la règle globale/société est respectée.

        Scénario : création d'un code dans une société, puis tentative de création
        du même code en global doit être refusée, et inversement.
        """
        # Cas 1 : code société créé en premier, création globale ensuite refusée
        self.env["gest_agri.soil.type"].create(
            {"name": "Sableux", "code": "SAB", "company_id": self.company.id}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.soil.type"].create(
                {"name": "Sable global", "code": "SAB", "company_id": False}
            )

        # Cas 2 : code global créé en premier, création société ensuite refusée
        # On réinitialise et on teste l'inverse
        SoilType = self.env["gest_agri.soil.type"]
        # On supprime les entrées de test pour partir sur un état propre
        SoilType.search([("code", "=", "SAB")]).unlink()
        SoilType.search([("code", "=", "SAB_global")]).unlink()

        # Création globale d'abord
        global_type = SoilType.create({"name": "Sable global", "code": "SAB", "company_id": False})
        # Puis tentative de création dans une société doit échouer
        with self.assertRaises(ValidationError):
            SoilType.create({"name": "Sable société", "code": "SAB", "company_id": self.company.id})

        # Nettoyage
        global_type.unlink()

    def test_same_code_in_other_company(self):
        other_company = self.env["res.company"].create({"name": "Autre société"})
        self.env["gest_agri.soil.type"].create(
            {"name": "Calcaire", "code": "CAL", "company_id": self.company.id}
        )
        other_type = self.env["gest_agri.soil.type"].create(
            {"name": "Calcaire autre société", "code": "CAL", "company_id": other_company.id}
        )
        self.assertEqual(other_type.company_id, other_company)

    def test_same_code_in_lot_creation(self):
        """Teste que deux références identiques dans une création en lot sont refusées."""
        with self.assertRaises(UNIQUE_ERRORS):
            self.env["gest_agri.soil.type"].create([
                {"name": "Sable 1", "code": "SAB", "company_id": self.company.id},
                {"name": "Sable 2", "code": "SAB", "company_id": self.company.id},
            ])

    def test_code_modification_with_conflict(self):
        """Teste que la modification du code lève une erreur en cas de conflit."""
        SoilType = self.env["gest_agri.soil.type"]
        SoilType.create(
            {"name": "Sable", "code": "SAB", "company_id": self.company.id}
        )
        other = SoilType.create(
            {"name": "Argile", "code": "ARG", "company_id": self.company.id}
        )
        # Le changement de code vers un code déjà utilisé doit être refusé.
        with self.assertRaises(UNIQUE_ERRORS):
            other.write({"name": "Sable modifié", "code": "SAB"})

    def test_code_unchanged_is_not_a_conflict(self):
        """Réécrire le même code sur le même enregistrement n'est pas un conflit."""
        SoilType = self.env["gest_agri.soil.type"]
        record = SoilType.create(
            {"name": "Sable", "code": "SABLE", "company_id": self.company.id}
        )
        record.write({"name": "Sable renommé", "code": "SABLE"})
        self.assertEqual(record.code, "SABLE")

    def test_farm_type_description(self):
        """La description d'un type d'exploitation peut être créée, modifiée et relue."""
        farm_type = self.env["gest_agri.farm.type"].create(
            {"name": "Polyculture", "code": "POLY", "company_id": self.company.id}
        )
        self.assertFalse(farm_type.description)
        farm_type.write({"description": "Exploitation mixte céréales et élevage."})
        self.assertEqual(farm_type.description, "Exploitation mixte céréales et élevage.")
        reloaded = self.env["gest_agri.farm.type"].browse(farm_type.id)
        self.assertEqual(reloaded.description, "Exploitation mixte céréales et élevage.")

