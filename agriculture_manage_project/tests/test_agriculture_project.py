from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestAgricultureProjectLinks(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.farm = cls.env["agriculture.farm"].create({
            "name": "Exploitation test projet",
            "company_id": cls.company.id,
            "total_area": 100,
        })
        cls.plot = cls.env["agriculture.farm.plot"].create({
            "name": "Parcelle projet test",
            "farm_id": cls.farm.id,
            "area": 10,
            "area_unit": "ha",
        })

    def test_project_is_independent_from_campaign(self):
        project = self.env["project.project"].create({
            "name": "Projet irrigation test",
            "company_id": self.company.id,
            "agriculture_farm_id": self.farm.id,
            "agriculture_plot_ids": [(6, 0, self.plot.ids)],
            "agriculture_project_type": "irrigation",
        })
        self.assertEqual(project.agriculture_farm_id, self.farm)
        self.assertFalse(project.agriculture_operation_ids)

    def test_reject_plot_from_another_farm(self):
        other_farm = self.env["agriculture.farm"].create({
            "name": "Autre exploitation projet test",
            "company_id": self.company.id,
            "total_area": 20,
        })
        other_plot = self.env["agriculture.farm.plot"].create({
            "name": "Parcelle étrangère test",
            "farm_id": other_farm.id,
            "area": 2,
            "area_unit": "ha",
        })
        with self.assertRaises(ValidationError):
            self.env["project.project"].create({
                "name": "Projet invalide",
                "company_id": self.company.id,
                "agriculture_farm_id": self.farm.id,
                "agriculture_plot_ids": [(6, 0, other_plot.ids)],
            })

    def test_operation_must_have_one_owner(self):
        with self.assertRaises(ValidationError):
            self.env["agriculture.farm.operation"].create({
                "name": "Opération sans rattachement",
                "operation_type": "other",
            })
