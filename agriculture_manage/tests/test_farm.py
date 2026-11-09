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

    def test_archiving_plot_recomputes_allocated_area(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation parcelle archivée", "total_area": 2}
        )
        plot = self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle à archiver",
                "farm_id": farm.id,
                "area": 75,
                "area_unit": "are",
            }
        )
        self.assertAlmostEqual(farm.allocated_area, 0.75)

        plot.write({"active": False})
        farm.invalidate_recordset(["allocated_area"])
        self.assertAlmostEqual(farm.allocated_area, 0.0)

        plot.write({"active": True})
        farm.invalidate_recordset(["allocated_area"])
        self.assertAlmostEqual(farm.allocated_area, 0.75)


    def test_site_area_and_counts_follow_active_plots(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation statistiques site", "total_area": 3}
        )
        site = self.env["agriculture.farm.site"].create(
            {"name": "Site statistiques", "farm_id": farm.id}
        )
        plot = self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle statistiques",
                "farm_id": farm.id,
                "site_id": site.id,
                "area": 125,
                "area_unit": "are",
            }
        )
        self.assertEqual(site.plot_count, 1)
        self.assertAlmostEqual(site.plot_area, 1.25)

        plot.write({"active": False})
        site.invalidate_recordset(["plot_count", "plot_area"])
        self.assertEqual(site.plot_count, 0)
        self.assertAlmostEqual(site.plot_area, 0.0)

        plot.write({"active": True})
        site.invalidate_recordset(["plot_count", "plot_area"])
        self.assertEqual(site.plot_count, 1)
        self.assertAlmostEqual(site.plot_area, 1.25)


    def test_infrastructure_gps_and_maintenance_validation(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation infrastructure", "total_area": 4}
        )
        infrastructure = self.env["agriculture.farm.infrastructure"].create(
            {
                "name": "Forage principal",
                "farm_id": farm.id,
                "infrastructure_type": "well",
                "latitude": 32.4912,
                "longitude": 3.6735,
                "last_maintenance_date": "2026-01-10",
                "next_maintenance_date": "2026-12-10",
            }
        )
        self.assertEqual(infrastructure.latitude, 32.4912)
        self.assertFalse(infrastructure.maintenance_due)

        with self.assertRaises(ValidationError):
            infrastructure.write({"latitude": 91})
        with self.assertRaises(ValidationError):
            infrastructure.write({"longitude": 181})
        with self.assertRaises(ValidationError):
            infrastructure.write({"next_maintenance_date": "2025-12-01"})

    def test_infrastructure_maintenance_due_flag(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation maintenance", "total_area": 4}
        )
        infrastructure = self.env["agriculture.farm.infrastructure"].create(
            {
                "name": "Réservoir principal",
                "farm_id": farm.id,
                "infrastructure_type": "reservoir",
                "next_maintenance_date": "2020-01-01",
            }
        )
        self.assertTrue(infrastructure.maintenance_due)
        infrastructure.write({"condition": "out_of_service"})
        self.assertFalse(infrastructure.maintenance_due)

    def test_plot_soil_measurements_are_validated(self):
        farm = self.env["agriculture.farm"].create(
            {"name": "Exploitation analyse du sol", "total_area": 2}
        )
        plot = self.env["agriculture.farm.plot"].create(
            {
                "name": "Parcelle analyse",
                "farm_id": farm.id,
                "area": 1,
                "soil_ph": 6.5,
                "organic_matter_percent": 2.4,
                "slope_percent": 5,
                "soil_fertility": "medium",
                "irrigation_water_source": "well",
            }
        )
        self.assertEqual(plot.soil_ph, 6.5)
        self.assertEqual(plot.soil_fertility, "medium")

        with self.assertRaises(ValidationError):
            plot.write({"soil_ph": 15})
        with self.assertRaises(ValidationError):
            plot.write({"organic_matter_percent": 101})
        with self.assertRaises(ValidationError):
            plot.write({"slope_percent": -1})

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