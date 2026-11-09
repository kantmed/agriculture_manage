# -*- coding: utf-8 -*-
"""Tests for agriculture_manage_crop."""

import uuid

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from dateutil.relativedelta import relativedelta


class TestFarmCrop(TransactionCase):
    def test_create_crop(self):
        crop_type = self.env.ref("agriculture_manage_crop.crop_type_cereal")
        crop = self.env["agriculture.farm.crop"].create({
            "name": "Blé",
            "crop_type_id": crop_type.id,
            "abbreviation": "ble",
        })
        self.assertRegex(crop.code, r"^BLE-\d{2}$")
        self.assertEqual(crop.abbreviation, "BLE")
        self.assertEqual(crop.name, "Blé")

    def test_crop_reference_sequence_is_per_abbreviation(self):
        crop_type = self.env.ref("agriculture_manage_crop.crop_type_cereal")
        abbreviation = f"T{uuid.uuid4().hex[:12]}".upper()
        other_abbreviation = f"U{uuid.uuid4().hex[:12]}".upper()
        crops = self.env["agriculture.farm.crop"].create([
            {
                "name": "Culture 1",
                "crop_type_id": crop_type.id,
                "abbreviation": abbreviation,
            },
            {
                "name": "Culture 2",
                "crop_type_id": crop_type.id,
                "abbreviation": abbreviation,
            },
            {
                "name": "Autre culture",
                "crop_type_id": crop_type.id,
                "abbreviation": other_abbreviation,
            },
        ])

        self.assertEqual(crops[0].code, f"{abbreviation}-01")
        self.assertEqual(crops[1].code, f"{abbreviation}-02")
        self.assertEqual(crops[2].code, f"{other_abbreviation}-01")

    def test_crop_requires_a_valid_abbreviation(self):
        crop_type = self.env.ref("agriculture_manage_crop.crop_type_cereal")
        with self.assertRaises(ValidationError):
            self.env["agriculture.farm.crop"].create({
                "name": "Culture sans abréviation",
                "crop_type_id": crop_type.id,
            })

    def test_create_operation_reference(self):
        operation_model = self.env["agriculture.farm.operation"]
        operation = self.env["agriculture.farm.operation"].create({
            "name": "Semis",
        })
        today = fields.Date.context_today(operation_model).strftime("%Y%m%d")
        self.assertRegex(operation.code, rf"^OPE-{today}-\d{{2}}$")


class TestFarmCropCampaign(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.farm = cls.env["agriculture.farm"].create({
            "name": "Exploitation de test",
            "total_area": 10,
        })
        crop_type = cls.env.ref("agriculture_manage_crop.crop_type_cereal")
        cls.crop = cls.env["agriculture.farm.crop"].create({
            "name": "Culture de test",
            "crop_type_id": crop_type.id,
            "abbreviation": f"T{uuid.uuid4().hex[:12]}",
        })

    def _create_campaign(self, name):
        return self.env["agriculture.farm.crop.campaign"].create({
            "name": name,
            "farm_id": self.farm.id,
            "crop_id": self.crop.id,
        })

    def test_campaign_reference_uses_years_in_name(self):
        campaign = self._create_campaign("Campagne céréalière 2025-2026")
        self.assertEqual(campaign.code, "CAM-2025-2026")

    def test_campaign_reference_falls_back_to_current_year(self):
        current_year = fields.Date.context_today(self.env["agriculture.farm.crop.campaign"]).year
        campaign = self._create_campaign("Campagne sans période")
        self.assertEqual(campaign.code, f"CAM-{current_year}-{current_year}")

    def test_campaign_reference_uses_fallback_when_years_are_ambiguous(self):
        current_year = fields.Date.context_today(self.env["agriculture.farm.crop.campaign"]).year
        campaign = self._create_campaign("Campagne 2024, 2025 et 2026")
        self.assertEqual(campaign.code, f"CAM-{current_year}-{current_year}")

    def test_campaign_references_may_be_duplicated(self):
        first = self._create_campaign("Campagne 2025-2026")
        second = self._create_campaign("Autre campagne 2025-2026")
        self.assertEqual(first.code, second.code)

    def test_campaign_dates_must_be_valid(self):
        with self.assertRaises(ValidationError):
            self.env["agriculture.farm.crop.campaign"].create({
                "name": "Campagne avec date de fin antérieure",
                "farm_id": self.farm.id,
                "crop_id": self.crop.id,
                "start_date": "2026-02-01",
                "end_date": "2026-01-01",
            })

    def test_campaign_variety_must_match_crop(self):
        # create a variety for a different crop
        other_crop = self.env["agriculture.farm.crop"].create({
            "name": "Autre culture",
            "crop_type_id": self.env.ref("agriculture_manage_crop.crop_type_cereal").id,
            "abbreviation": f"O{uuid.uuid4().hex[:12]}",
        })
        other_variety = self.env["agriculture.farm.crop.variety"].create({
            "name": "Autre variété",
            "crop_id": other_crop.id,
        })
        with self.assertRaises(ValidationError):
            self.env["agriculture.farm.crop.campaign"].create({
                "name": "Campagne avec variété invalide",
                "farm_id": self.farm.id,
                "crop_id": self.crop.id,
                "variety_id": other_variety.id,
            })


class TestFarmCropCampaignPlot(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.farm = cls.env["agriculture.farm"].create({
            "name": "Exploitation de test",
            "total_area": 10,
        })
        crop_type = cls.env.ref("agriculture_manage_crop.crop_type_cereal")
        cls.crop = cls.env["agriculture.farm.crop"].create({
            "name": "Culture de test",
            "crop_type_id": crop_type.id,
            "abbreviation": "TESTCROP",
        })
        cls.plot1 = cls.env["agriculture.farm.plot"].create({
            "name": "Parcelle 1",
            "farm_id": cls.farm.id,
            "area": 5,
            "area_unit": "ha",
        })
        cls.plot2 = cls.env["agriculture.farm.plot"].create({
            "name": "Parcelle 2",
            "farm_id": cls.farm.id,
            "area": 5,
            "area_unit": "ha",
        })
        cls.other_farm = cls.env["agriculture.farm"].create({
            "name": "Autre exploitation",
            "total_area": 10,
        })
        cls.other_plot = cls.env["agriculture.farm.plot"].create({
            "name": "Parcelle tierce",
            "farm_id": cls.other_farm.id,
            "area": 5,
            "area_unit": "ha",
        })
        cls.campaign = cls.env["agriculture.farm.crop.campaign"].create({
            "name": "Campagne test",
            "farm_id": cls.farm.id,
            "crop_id": cls.crop.id,
        })

    def test_create_plot_in_campaign(self):
        plot_in_campaign = self.env["agriculture.farm.crop.campaign.plot"].create({
            "campaign_id": self.campaign.id,
            "plot_id": self.plot1.id,
            "planting_date": fields.Date.today(),
            "expected_harvest_date": fields.Date.today() + relativedelta(months=6),
        })
        self.assertEqual(plot_in_campaign.area_ha, 5)
        self.assertEqual(plot_in_campaign.state, "planned")

    def test_plot_farm_must_match_campaign_farm(self):
        with self.assertRaises(ValidationError):
            self.env["agriculture.farm.crop.campaign.plot"].create({
                "campaign_id": self.campaign.id,
                "plot_id": self.other_plot.id,
            })

    def test_planting_date_must_be_before_harvest_date(self):
        with self.assertRaises(ValidationError):
            self.env["agriculture.farm.crop.campaign.plot"].create({
                "campaign_id": self.campaign.id,
                "plot_id": self.plot1.id,
                "planting_date": fields.Date.today() + relativedelta(months=6),
                "expected_harvest_date": fields.Date.today(),
            })

    def test_state_transitions(self):
        record = self.env["agriculture.farm.crop.campaign.plot"].create({
            "campaign_id": self.campaign.id,
            "plot_id": self.plot1.id,
        })

        # Planned -> Planted
        record.write({
            "planting_date": fields.Date.today(),
            "state": "planted",
        })
        self.assertEqual(record.state, "planted")

        # Planted -> Growing
        record.write({
            "expected_harvest_date": fields.Date.today() + relativedelta(months=6),
            "state": "growing",
        })
        self.assertEqual(record.state, "growing")

        # Growing -> Harvested
        record.write({
            "state": "harvested",
        })
        self.assertEqual(record.state, "harvested")

