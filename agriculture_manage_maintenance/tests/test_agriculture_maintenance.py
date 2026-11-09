from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestAgricultureMaintenance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.farm = cls.env["agriculture.farm"].create({
            "name": "Exploitation maintenance test",
            "company_id": cls.company.id,
            "total_area": 10.0,
        })
        cls.site = cls.env["agriculture.farm.site"].create({
            "name": "Site maintenance test",
            "farm_id": cls.farm.id,
        })
        cls.infrastructure = cls.env["agriculture.farm.infrastructure"].create({
            "name": "Hangar maintenance test",
            "farm_id": cls.farm.id,
            "site_id": cls.site.id,
            "infrastructure_type": "warehouse",
        })

    def test_equipment_inherits_company_from_farm(self):
        equipment = self.env["maintenance.equipment"].create({
            "name": "Pompe agricole test",
            "effective_date": "2026-01-01",
            "agriculture_farm_id": self.farm.id,
            "agriculture_site_id": self.site.id,
            "agriculture_infrastructure_id": self.infrastructure.id,
        })
        self.assertEqual(equipment.company_id, self.company)
        self.assertEqual(equipment.agriculture_farm_id, self.farm)

    def test_equipment_rejects_site_from_another_farm(self):
        other_farm = self.env["agriculture.farm"].create({
            "name": "Autre exploitation maintenance test",
            "company_id": self.company.id,
            "total_area": 5.0,
        })
        other_site = self.env["agriculture.farm.site"].create({
            "name": "Autre site maintenance test",
            "farm_id": other_farm.id,
        })
        with self.assertRaises(ValidationError):
            self.env["maintenance.equipment"].create({
                "name": "Équipement incohérent",
                "effective_date": "2026-01-01",
                "agriculture_farm_id": self.farm.id,
                "agriculture_site_id": other_site.id,
            })
