from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestAgricultureFarm(TransactionCase):
    def test_farm_reference_uses_current_year_and_four_digits(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation référence", "total_area": 5}
        )

        self.assertRegex(farm.code, rf"^EXP-{date.today().year}-\d{{4}}$")

    def test_plot_areas_cannot_exceed_global_farm_area(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation superficie", "total_area": 1}
        )
        self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle 1",
                "farm_id": farm.id,
                "area": 60,
                "area_unit": "are",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["agriculture.farm.plot"].create(
                {
                    "name": "Parcelle 2",
                    "farm_id": farm.id,
                    "area": 41,
                    "area_unit": "are",
                }
            )

    def test_plot_areas_can_equal_global_area_across_units(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation superficie exacte", "total_area": 1}
        )
        self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle hectares",
                "farm_id": farm.id,
                "area": 0.5,
                "area_unit": "ha",
            }
        )
        self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle ares",
                "farm_id": farm.id,
                "area": 50,
                "area_unit": "are",
            }
        )

        self.assertAlmostEqual(farm.allocated_area, farm.total_area)

    def test_global_area_cannot_be_reduced_below_plot_total(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation superficie", "total_area": 1}
        )
        self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle",
                "farm_id": farm.id,
                "area": 75,
                "area_unit": "are",
            }
        )

        with self.assertRaises(ValidationError):
            farm.write({"total_area": 0.5})

    def test_site_reference_contains_farm_reference_and_per_farm_number(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation avec sites", "total_area": 5}
        )
        other_farm = self.env["agriculture.farm"].create(
            {"name": "Autre exploitation avec site", "total_area": 5}
        )

        first_site = self.env["agriculture.farm.site"].create(
            {"name": "Site 1", "farm_id": farm.id}
        )
        second_site = self.env["agriculture.farm.site"].create(
            {"name": "Site 2", "farm_id": farm.id}
        )
        other_site = self.env["agriculture.farm.site"].create(
            {"name": "Site autre exploitation", "farm_id": other_farm.id}
        )

        self.assertEqual(first_site.code, f"{farm.code}-SIT-01")
        self.assertEqual(second_site.code, f"{farm.code}-SIT-02")
        self.assertEqual(other_site.code, f"{other_farm.code}-SIT-01")

    def test_plot_reference_contains_farm_reference_and_per_farm_number(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation avec parcelles", "total_area": 5}
        )
        other_farm = self.env["agriculture.farm"].create(
            {"name": "Autre exploitation avec parcelle", "total_area": 5}
        )

        first_plot = self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle 1",
                "farm_id": farm.id,
                "area": 1,
            }
        )
        second_plot = self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle 2",
                "farm_id": farm.id,
                "area": 1,
            }
        )
        other_plot = self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle autre exploitation",
                "farm_id": other_farm.id,
                "area": 1,
            }
        )

        self.assertEqual(first_plot.code, f"{farm.code}-PAR-001")
        self.assertEqual(second_plot.code, f"{farm.code}-PAR-002")
        self.assertEqual(other_plot.code, f"{other_farm.code}-PAR-001")