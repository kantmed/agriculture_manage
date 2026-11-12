# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

import psycopg2

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


# Index unique PostgreSQL levé à l'INSERT (avant la contrainte Python).
# Au niveau ORM l'erreur brute psycopg2 est propagée, les deux sont acceptées
# (cf. test_patrimony.py / test_reproduction.py).
UNIQUE_ERRORS = (ValidationError, psycopg2.errors.UniqueViolation)


class TestAnimalProduction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")

        cls.user_a = cls._create_user("prod_user_a", [cls.base_user, cls.group_user])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme production A", "code": "PA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme production B", "code": "PB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create({"name": "Site PA", "code": "SPA", "farm_id": cls.farm_a.id})
        cls.site_b = cls.env["gest_agri.site"].create({"name": "Site PB", "code": "SPB", "farm_id": cls.farm_b.id})

        cls.species = cls.env["gest_agri.livestock.species"].create(
            {"name": "Bovin", "code": "BOVP", "company_id": cls.company.id}
        )
        cls.species_hen = cls.env["gest_agri.livestock.species"].create(
            {"name": "Poule", "code": "POUL", "company_id": cls.company.id}
        )
        cls.breed = cls.env["gest_agri.livestock.breed"].create(
            {"name": "Holstein P", "code": "HOLP", "company_id": cls.company.id, "species_id": cls.species.id}
        )

        cls.uom_kg = cls.env.ref("uom.product_uom_kgm")
        cls.uom_g = cls.env.ref("uom.product_uom_gram")
        cls.uom_l = cls.env.ref("uom.product_uom_unit")

        cls.cow = cls.env["gest_agri.animal"].create(
            {"name": "Vache P1", "species_id": cls.species.id, "breed_id": cls.breed.id,
             "sex": "female", "farm_id": cls.farm_a.id, "site_id": cls.site_a.id,
             "birth_date": date(2020, 1, 1)}
        )
        cls.cow.action_activate()
        cls.cow2 = cls.env["gest_agri.animal"].create(
            {"name": "Vache P2", "species_id": cls.species.id, "sex": "female",
             "farm_id": cls.farm_a.id, "birth_date": date(2021, 1, 1)}
        )
        cls.cow2.action_activate()

        cls.foreign_animal = cls.env["gest_agri.animal"].create(
            {"name": "Vache B", "species_id": cls.species.id, "sex": "female",
             "farm_id": cls.farm_b.id, "birth_date": date(2020, 6, 1)}
        )
        cls.foreign_animal.action_activate()

        cls.lot_a = cls.env["gest_agri.animal.lot"].create(
            {"name": "Lot production A", "species_id": cls.species.id, "farm_id": cls.farm_a.id}
        )
        cls.lot_b = cls.env["gest_agri.animal.lot"].create(
            {"name": "Lot production B", "species_id": cls.species.id, "farm_id": cls.farm_b.id}
        )
        cls.hen_lot = cls.env["gest_agri.animal.lot"].create(
            {"name": "Lot pondeuses A", "species_id": cls.species_hen.id, "farm_id": cls.farm_a.id}
        )

        cls.production_type = cls.env["gest_agri.production.type"].create(
            {"name": "Viande bovine", "code": "VBOV", "company_id": cls.company.id}
        )

        cls.category_big = cls.env["gest_agri.egg.category"].create(
            {"name": "Gros P", "code": "GROSP", "company_id": cls.company.id, "is_loss": False}
        )
        cls.category_broken = cls.env["gest_agri.egg.category"].create(
            {"name": "Cassé P", "code": "CASSEP", "company_id": cls.company.id, "is_loss": True}
        )

    @classmethod
    def _create_user(cls, login, groups):
        group_ids = [g.id if hasattr(g, "id") else int(g) for g in groups]
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create({
                "name": login, "login": login, "email": f"{login}@example.com",
                "company_id": cls.company.id, "company_ids": [(6, 0, [cls.company.id])],
                "group_ids": [(6, 0, group_ids)],
            })
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _milk(self, **kwargs):
        vals = {
            "animal_id": self.cow.id, "production_mode": "individual",
            "production_date": date(2026, 3, 1), "milking_period": "morning",
            "quantity": 12.5, "uom_id": self.uom_l.id,
        }
        vals.update(kwargs)
        return self.env["gest_agri.milk.production"].create(vals)

    def _weight(self, **kwargs):
        vals = {
            "animal_id": self.cow.id, "weighing_mode": "individual",
            "weighing_type": "periodic", "weighing_datetime": datetime(2026, 3, 1, 8, 0),
            "weight": 500.0, "uom_id": self.uom_kg.id,
        }
        vals.update(kwargs)
        return self.env["gest_agri.animal.weight"].create(vals)

    def _meat(self, **kwargs):
        vals = {
            "animal_id": self.cow.id, "production_date": date(2026, 6, 1),
            "production_type_id": self.production_type.id, "uom_id": self.uom_kg.id,
        }
        vals.update(kwargs)
        return self.env["gest_agri.meat.production"].create(vals)

    def _egg(self, **kwargs):
        vals = {"lot_id": self.hen_lot.id, "collection_date": date(2026, 4, 1), "egg_count": 100}
        vals.update(kwargs)
        return self.env["gest_agri.egg.production"].create(vals)

    def _dead_animal(self, death_dt):
        animal = self.env["gest_agri.animal"].create(
            {"name": "Animal décédé", "species_id": self.species.id, "sex": "male",
             "farm_id": self.farm_a.id, "birth_date": date(2020, 1, 1)}
        )
        animal.action_activate()
        mortality = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": animal.id, "death_datetime": death_dt, "mortality_type": "disease"}
        )
        mortality.action_validate()
        return animal

    # ==================================================================
    # PRODUCTION LAITIÈRE
    # ==================================================================
    def test_01_milk_individual_creation(self):
        m = self._milk()
        self.assertTrue(m.name.startswith("LAI/"))
        self.assertEqual(m.production_mode, "individual")
        self.assertEqual(m.farm_id, self.farm_a)
        self.assertEqual(m.species_id, self.species)
        self.assertEqual(m.state, "draft")

    def test_02_milk_collective_creation(self):
        m = self._milk(animal_id=False, lot_id=self.lot_a.id, production_mode="collective", animal_count=20)
        self.assertEqual(m.production_mode, "collective")
        self.assertEqual(m.lot_id, self.lot_a)
        self.assertEqual(m.farm_id, self.farm_a)
        self.assertEqual(m.species_id, self.species)

    def test_03_milk_validate(self):
        m = self._milk()
        m.action_validate()
        self.assertEqual(m.state, "validated")

    def test_04_milk_cancel(self):
        m = self._milk()
        m.action_cancel()
        self.assertEqual(m.state, "cancelled")

    def test_05_milk_negative_quantity_refused(self):
        with self.assertRaises(ValidationError):
            self._milk(quantity=-1.0)

    def test_06_milk_zero_quantity_refused(self):
        with self.assertRaises(ValidationError):
            self._milk(quantity=0.0)

    def test_07_milk_uom_recorded(self):
        m = self._milk(uom_id=self.uom_l.id)
        self.assertEqual(m.uom_id, self.uom_l)

    def test_08_milk_individual_requires_animal(self):
        with self.assertRaises(ValidationError):
            self._milk(animal_id=False, production_mode="individual")

    def test_09_milk_individual_rejects_lot(self):
        with self.assertRaises(ValidationError):
            self._milk(production_mode="individual", lot_id=self.lot_a.id)

    def test_10_milk_collective_requires_lot(self):
        with self.assertRaises(ValidationError):
            self._milk(animal_id=False, production_mode="collective")

    def test_11_milk_collective_rejects_animal(self):
        with self.assertRaises(ValidationError):
            self._milk(animal_id=self.cow.id, production_mode="collective", lot_id=self.lot_a.id)

    def test_12_milk_farm_derived_from_animal(self):
        m = self._milk()
        self.assertEqual(m.farm_id, self.cow.farm_id)

    def test_13_milk_cross_farm_attribution(self):
        m = self._milk(animal_id=self.foreign_animal.id)
        self.assertEqual(m.farm_id, self.farm_b)

    def test_14_milk_site_farm_coherence(self):
        with self.assertRaises(ValidationError):
            self._milk(site_id=self.site_b.id)

    def test_15_milk_dead_animal_refused(self):
        dead = self.env["gest_agri.animal"].create(
            {"name": "Vache morte", "species_id": self.species.id, "sex": "female", "farm_id": self.farm_a.id}
        )
        dead.action_activate()
        dead.action_die()
        with self.assertRaises(ValidationError):
            self._milk(animal_id=dead.id)

    def test_16_milk_date_before_birth_refused(self):
        with self.assertRaises(ValidationError):
            self._milk(production_date=date(2010, 1, 1))

    def test_17_milk_all_periods_accepted(self):
        for i, period in enumerate(("morning", "noon", "evening", "other")):
            m = self._milk(production_date=date(2026, 3, 2), milking_period=period)
            self.assertEqual(m.milking_period, period)

    def test_18_milk_duplicate_individual(self):
        self._milk()
        with self.assertRaises(UNIQUE_ERRORS):
            self._milk()

    def test_19_milk_duplicate_collective(self):
        self._milk(animal_id=False, lot_id=self.lot_a.id, production_mode="collective")
        with self.assertRaises(UNIQUE_ERRORS):
            self._milk(animal_id=False, lot_id=self.lot_a.id, production_mode="collective")

    def test_20_milk_direct_state_write_forbidden(self):
        m = self._milk()
        with self.assertRaises(AccessError):
            m.write({"state": "validated"})

    def test_21_milk_unlink_validated_forbidden(self):
        m = self._milk()
        m.action_validate()
        with self.assertRaises(UserError):
            m.unlink()

    def test_22_milk_unlink_draft_allowed(self):
        m = self._milk()
        m.unlink()
        self.assertFalse(m.exists())

    def test_23_milk_negative_animal_count_refused(self):
        with self.assertRaises(ValidationError):
            self._milk(animal_id=False, lot_id=self.lot_a.id, production_mode="collective", animal_count=-2)

    # ==================================================================
    # SESSIONS DE TRAITE
    # ==================================================================
    def test_24_session_creation(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        self.assertTrue(s.name.startswith("TRA/"))
        self.assertEqual(s.state, "draft")
        self.assertEqual(s.farm_id, self.farm_a)

    def test_25_session_dates_coherence(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.milking.session"].create({
                "farm_id": self.farm_a.id,
                "start_datetime": datetime(2026, 3, 1, 10, 0),
                "end_datetime": datetime(2026, 3, 1, 8, 0),
            })

    def test_26_session_line_negative_quantity_refused(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        with self.assertRaises(ValidationError):
            self.env["gest_agri.milking.session.line"].create({
                "session_id": s.id, "animal_id": self.cow.id, "quantity": -3.0,
            })

    def test_27_session_line_zero_quantity_refused(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        with self.assertRaises(ValidationError):
            self.env["gest_agri.milking.session.line"].create({
                "session_id": s.id, "animal_id": self.cow.id, "quantity": 0.0,
            })

    def test_28_session_totals_from_lines(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        self.env["gest_agri.milking.session.line"].create(
            {"session_id": s.id, "animal_id": self.cow.id, "quantity": 10.0})
        self.env["gest_agri.milking.session.line"].create(
            {"session_id": s.id, "animal_id": self.cow2.id, "quantity": 8.0})
        self.assertAlmostEqual(s.total_quantity, 18.0, places=3)
        self.assertEqual(s.animal_count, 2)

    def test_29_session_done_requires_line(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        with self.assertRaises(UserError):
            s.action_done()

    def test_30_session_done_ok(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        self.env["gest_agri.milking.session.line"].create(
            {"session_id": s.id, "animal_id": self.cow.id, "quantity": 10.0})
        s.action_done()
        self.assertEqual(s.state, "done")

    def test_31_session_line_target_exclusive(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        with self.assertRaises(ValidationError):
            self.env["gest_agri.milking.session.line"].create({
                "session_id": s.id, "animal_id": self.cow.id, "lot_id": self.lot_a.id, "quantity": 5.0,
            })

    def test_32_session_line_farm_coherence(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        with self.assertRaises(ValidationError):
            self.env["gest_agri.milking.session.line"].create({
                "session_id": s.id, "animal_id": self.foreign_animal.id, "quantity": 5.0,
            })

    def test_33_session_cancel(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        s.action_cancel()
        self.assertEqual(s.state, "cancelled")

    def test_34_session_site_farm_coherence(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id, "site_id": self.site_b.id})

    def test_35_session_direct_state_write_forbidden(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        with self.assertRaises(AccessError):
            s.write({"state": "done"})

    # ==================================================================
    # QUALITÉ DU LAIT
    # ==================================================================
    def _milk_quality(self, **kwargs):
        m = kwargs.pop("production", None) or self._milk()
        vals = {"production_id": m.id, "control_date": date(2026, 3, 2)}
        vals.update(kwargs)
        return self.env["gest_agri.milk.quality"].create(vals)

    def test_36_milk_quality_creation(self):
        q = self._milk_quality()
        self.assertTrue(q.name.startswith("QLA/"))
        self.assertEqual(q.conformity, "pending")
        self.assertEqual(q.farm_id, self.farm_a)

    def test_37_milk_quality_conforme(self):
        q = self._milk_quality(conformity="conforme", fat_rate=3.8, protein_rate=3.2)
        self.assertEqual(q.conformity, "conforme")
        self.assertFalse(q.production_id.has_non_conformity)

    def test_38_milk_quality_non_conforme(self):
        q = self._milk_quality(conformity="non_conforme")
        self.assertEqual(q.conformity, "non_conforme")
        self.assertTrue(q.production_id.has_non_conformity)

    def test_39_milk_quality_pending_not_conforme(self):
        q = self._milk_quality()
        self.assertEqual(q.conformity, "pending")
        self.assertNotEqual(q.conformity, "conforme")

    def test_40_milk_quality_negative_rate_refused(self):
        with self.assertRaises(ValidationError):
            self._milk_quality(fat_rate=-1.0)

    def test_41_milk_quality_ph_range(self):
        with self.assertRaises(ValidationError):
            self._milk_quality(ph=20.0)

    def test_42_milk_quality_health_animal_coherence(self):
        m = self._milk()
        health = self.env["gest_agri.animal.health"].create(
            {"animal_id": self.cow2.id, "observation_date": date(2026, 3, 2)}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.milk.quality"].create(
                {"production_id": m.id, "control_date": date(2026, 3, 2), "health_record_id": health.id}
            )

    def test_43_milk_quality_count_indicator(self):
        m = self._milk()
        self._milk_quality(production=m)
        self._milk_quality(production=m)
        self.assertEqual(m.quality_count, 2)

    # ==================================================================
    # CROISSANCE ET PESÉES
    # ==================================================================
    def test_44_weight_creation(self):
        w = self._weight()
        self.assertTrue(w.name.startswith("PES/"))
        self.assertEqual(w.farm_id, self.farm_a)
        self.assertEqual(w.state, "draft")

    def test_45_weight_negative_refused(self):
        with self.assertRaises(ValidationError):
            self._weight(weight=-10.0)

    def test_46_weight_zero_refused(self):
        with self.assertRaises(ValidationError):
            self._weight(weight=0.0)

    def test_47_weight_gain_computed(self):
        self._weight(weighing_datetime=datetime(2026, 3, 1, 8, 0), weight=400.0)
        w2 = self._weight(weighing_datetime=datetime(2026, 3, 11, 8, 0), weight=430.0)
        self.assertAlmostEqual(w2.previous_weight, 400.0, places=3)
        self.assertAlmostEqual(w2.weight_gain, 30.0, places=3)
        self.assertEqual(w2.days_interval, 10)

    def test_48_weight_gmq_computed(self):
        self._weight(weighing_datetime=datetime(2026, 3, 1, 8, 0), weight=400.0)
        w2 = self._weight(weighing_datetime=datetime(2026, 3, 11, 8, 0), weight=430.0)
        self.assertAlmostEqual(w2.average_daily_gain, 3.0, places=4)

    def test_49_weight_same_datetime_no_gmq(self):
        self._weight(weighing_datetime=datetime(2026, 3, 1, 8, 0), weight=400.0)
        w2 = self._weight(weighing_datetime=datetime(2026, 3, 1, 8, 0), weight=430.0)
        self.assertEqual(w2.previous_weight, 0.0)
        self.assertEqual(w2.average_daily_gain, 0.0)

    def test_50_weight_uom_mismatch_no_gmq(self):
        self._weight(weighing_datetime=datetime(2026, 3, 1, 8, 0), weight=400.0, uom_id=self.uom_kg.id)
        w2 = self._weight(weighing_datetime=datetime(2026, 3, 11, 8, 0), weight=430.0, uom_id=self.uom_g.id)
        self.assertEqual(w2.previous_weight, 0.0)
        self.assertEqual(w2.average_daily_gain, 0.0)

    def test_51_weight_collective(self):
        w = self._weight(animal_id=False, lot_id=self.lot_a.id, weighing_mode="collective",
                         weight=0.0, average_weight=450.0, animal_count=12)
        self.assertEqual(w.weighing_mode, "collective")
        self.assertAlmostEqual(w.average_weight, 450.0, places=3)
        self.assertEqual(w.animal_count, 12)

    def test_52_weight_collective_requires_count(self):
        with self.assertRaises(ValidationError):
            self._weight(animal_id=False, lot_id=self.lot_a.id, weighing_mode="collective",
                         weight=0.0, average_weight=450.0, animal_count=0)

    def test_53_weight_individual_requires_animal(self):
        with self.assertRaises(ValidationError):
            self._weight(animal_id=False, weighing_mode="individual")

    def test_54_weight_collective_requires_lot(self):
        with self.assertRaises(ValidationError):
            self._weight(animal_id=False, weighing_mode="collective",
                         weight=0.0, average_weight=450.0, animal_count=5)

    def test_55_weight_after_death_refused(self):
        dead = self._dead_animal(datetime(2026, 2, 1, 10, 0))
        with self.assertRaises(ValidationError):
            self._weight(animal_id=dead.id, weighing_datetime=datetime(2026, 3, 1, 8, 0))

    def test_56_weight_before_birth_refused(self):
        with self.assertRaises(ValidationError):
            self._weight(weighing_datetime=datetime(2010, 1, 1, 8, 0))

    def test_57_weight_validate(self):
        w = self._weight()
        w.action_validate()
        self.assertEqual(w.state, "validated")

    def test_58_weight_direct_state_write_forbidden(self):
        w = self._weight()
        with self.assertRaises(AccessError):
            w.write({"state": "validated"})

    def test_59_weight_cancel_recomputes_following(self):
        w1 = self._weight(weighing_datetime=datetime(2026, 3, 1, 8, 0), weight=400.0)
        w2 = self._weight(weighing_datetime=datetime(2026, 3, 11, 8, 0), weight=430.0)
        self.assertAlmostEqual(w2.previous_weight, 400.0, places=3)
        w1.action_cancel()
        self.assertEqual(w2.previous_weight, 0.0)
        self.assertEqual(w2.average_daily_gain, 0.0)

    def test_60_weight_unlink_validated_forbidden(self):
        w = self._weight()
        w.action_validate()
        with self.assertRaises(UserError):
            w.unlink()

    # ==================================================================
    # PRODUCTION DE VIANDE
    # ==================================================================
    def test_61_meat_creation(self):
        mp = self._meat()
        self.assertTrue(mp.name.startswith("VIA/"))
        self.assertEqual(mp.farm_id, self.farm_a)
        self.assertEqual(mp.species_id, self.species)
        self.assertEqual(mp.state, "draft")

    def test_62_meat_carcass_yield(self):
        mp = self._meat(live_weight=500.0, carcass_weight=275.0)
        self.assertAlmostEqual(mp.carcass_yield, 55.0, places=2)

    def test_63_meat_live_weight_not_carcass(self):
        mp = self._meat(live_weight=500.0)
        self.assertEqual(mp.carcass_yield, 0.0)

    def test_64_meat_carcass_exceeds_live_refused(self):
        with self.assertRaises(ValidationError):
            self._meat(live_weight=400.0, carcass_weight=450.0)

    def test_65_meat_marketable_exceeds_carcass_refused(self):
        with self.assertRaises(ValidationError):
            self._meat(carcass_weight=200.0, marketable_weight=250.0)

    def test_66_meat_negative_weight_refused(self):
        with self.assertRaises(ValidationError):
            self._meat(live_weight=-5.0)

    def test_67_meat_after_death_refused(self):
        dead = self._dead_animal(datetime(2026, 5, 1, 10, 0))
        with self.assertRaises(ValidationError):
            self._meat(animal_id=dead.id, production_date=date(2026, 6, 1))

    def test_68_meat_before_birth_refused(self):
        with self.assertRaises(ValidationError):
            self._meat(production_date=date(2010, 1, 1))

    def test_69_meat_duplicate(self):
        self._meat()
        with self.assertRaises(UNIQUE_ERRORS):
            self._meat()

    def test_70_meat_validate_cancel(self):
        mp = self._meat()
        mp.action_validate()
        self.assertEqual(mp.state, "validated")
        mp.action_cancel()
        self.assertEqual(mp.state, "cancelled")

    # ==================================================================
    # PRODUCTION D'ŒUFS
    # ==================================================================
    def test_71_egg_creation(self):
        e = self._egg()
        self.assertTrue(e.name.startswith("OEU/"))
        self.assertEqual(e.farm_id, self.farm_a)
        self.assertEqual(e.species_id, self.species_hen)
        self.assertEqual(e.state, "draft")

    def test_72_egg_line_creation(self):
        e = self._egg()
        line = self.env["gest_agri.egg.production.line"].create(
            {"production_id": e.id, "category_id": self.category_big.id, "egg_count": 60, "total_weight": 3.6})
        self.assertEqual(line.egg_count, 60)
        self.assertAlmostEqual(line.average_weight, 0.06, places=4)

    def test_73_egg_lines_exceed_total_refused(self):
        e = self._egg(egg_count=50)
        with self.assertRaises(ValidationError):
            self.env["gest_agri.egg.production.line"].create(
                {"production_id": e.id, "category_id": self.category_big.id, "egg_count": 60})

    def test_74_egg_validate_requires_sum_equal(self):
        e = self._egg(egg_count=100)
        self.env["gest_agri.egg.production.line"].create(
            {"production_id": e.id, "category_id": self.category_big.id, "egg_count": 60})
        with self.assertRaises(UserError):
            e.action_validate()

    def test_75_egg_validate_ok(self):
        e = self._egg(egg_count=100)
        self.env["gest_agri.egg.production.line"].create(
            {"production_id": e.id, "category_id": self.category_big.id, "egg_count": 100})
        e.action_validate()
        self.assertEqual(e.state, "validated")

    def test_76_egg_loss_count(self):
        e = self._egg(egg_count=100)
        self.env["gest_agri.egg.production.line"].create(
            {"production_id": e.id, "category_id": self.category_big.id, "egg_count": 90})
        self.env["gest_agri.egg.production.line"].create(
            {"production_id": e.id, "category_id": self.category_broken.id, "egg_count": 10})
        self.assertEqual(e.loss_egg_count, 10)
        self.assertEqual(e.line_egg_count, 100)

    def test_77_egg_negative_count_refused(self):
        with self.assertRaises(ValidationError):
            self._egg(egg_count=-1)

    def test_78_egg_duplicate_lot_date(self):
        self._egg()
        with self.assertRaises(UNIQUE_ERRORS):
            self._egg()

    def test_79_egg_cross_farm_attribution(self):
        e = self._egg(lot_id=self.lot_b.id)
        self.assertEqual(e.farm_id, self.farm_b)

    def test_80_egg_site_farm_coherence(self):
        with self.assertRaises(ValidationError):
            self._egg(site_id=self.site_b.id)

    def test_81_egg_category_unique_code(self):
        with self.assertRaises(UNIQUE_ERRORS):
            self.env["gest_agri.egg.category"].create(
                {"name": "Autre gros", "code": "GROSP", "company_id": self.company.id})

    def test_82_egg_quality_creation(self):
        e = self._egg()
        q = self.env["gest_agri.egg.quality"].create({"production_id": e.id, "control_date": date(2026, 4, 2)})
        self.assertTrue(q.name.startswith("QOE/"))
        self.assertEqual(q.conformity, "pending")
        self.assertEqual(q.farm_id, self.farm_a)

    def test_83_egg_quality_pending_not_conforme(self):
        e = self._egg()
        q = self.env["gest_agri.egg.quality"].create({"production_id": e.id, "control_date": date(2026, 4, 2)})
        self.assertNotEqual(q.conformity, "conforme")
        self.assertFalse(e.has_non_conformity)

    def test_84_egg_quality_non_conforme_indicator(self):
        e = self._egg()
        self.env["gest_agri.egg.quality"].create(
            {"production_id": e.id, "control_date": date(2026, 4, 2), "conformity": "non_conforme"})
        self.assertTrue(e.has_non_conformity)

    def test_85_egg_quality_negative_weight_refused(self):
        e = self._egg()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.egg.quality"].create(
                {"production_id": e.id, "control_date": date(2026, 4, 2), "weight": -1.0})

    def test_86_egg_cancel(self):
        e = self._egg()
        e.action_cancel()
        self.assertEqual(e.state, "cancelled")

    def test_87_egg_direct_state_write_forbidden(self):
        e = self._egg()
        with self.assertRaises(AccessError):
            e.write({"state": "validated"})

    # ==================================================================
    # HISTORIQUE / INDICATEURS
    # ==================================================================
    def test_88_animal_milk_indicator_validated_only(self):
        m = self._milk()
        self.assertEqual(self.cow.milk_production_count, 0)
        m.action_validate()
        self.assertEqual(self.cow.milk_production_count, 1)
        self.assertAlmostEqual(self.cow.milk_total_quantity, 12.5, places=3)

    def test_89_animal_milk_indicator_cancelled_excluded(self):
        m = self._milk()
        m.action_validate()
        m.action_cancel()
        self.assertEqual(self.cow.milk_production_count, 0)

    def test_90_animal_weight_last_weight(self):
        self._weight(weighing_datetime=datetime(2026, 3, 1, 8, 0), weight=400.0).action_validate()
        self._weight(weighing_datetime=datetime(2026, 3, 20, 8, 0), weight=450.0).action_validate()
        self.assertAlmostEqual(self.cow.last_weight, 450.0, places=3)
        self.assertEqual(self.cow.last_weight_date, date(2026, 3, 20))
        self.assertEqual(self.cow.weight_count, 2)

    def test_91_lot_milk_indicator(self):
        m = self._milk(animal_id=False, lot_id=self.lot_a.id, production_mode="collective", quantity=80.0)
        m.action_validate()
        self.assertEqual(self.lot_a.milk_production_count, 1)
        self.assertAlmostEqual(self.lot_a.milk_total_quantity, 80.0, places=3)

    def test_92_lot_egg_indicator(self):
        e = self._egg(egg_count=120)
        e.action_validate()
        self.assertEqual(self.hen_lot.egg_production_count, 1)
        self.assertEqual(self.hen_lot.egg_total_count, 120)

    def test_93_animal_meat_indicator(self):
        mp = self._meat(carcass_weight=250.0)
        mp.action_validate()
        self.assertEqual(self.cow.meat_production_count, 1)
        self.assertAlmostEqual(self.cow.meat_carcass_total, 250.0, places=3)

    def test_94_animal_view_actions(self):
        m = self._milk()
        action = self.cow.action_view_milk_productions()
        self.assertEqual(action["res_model"], "gest_agri.milk.production")
        self.assertIn(("animal_id", "=", self.cow.id), action["domain"])

    def test_95_lot_view_actions(self):
        action = self.hen_lot.action_view_egg_productions()
        self.assertEqual(action["res_model"], "gest_agri.egg.production")
        self.assertIn(("lot_id", "=", self.hen_lot.id), action["domain"])

    # ==================================================================
    # SÉCURITÉ / ISOLATION
    # ==================================================================
    def test_96_milk_isolation(self):
        m = self._milk()
        visible = self.env["gest_agri.milk.production"].with_user(self.user_a).search([])
        self.assertNotIn(m, visible)

    def test_97_weight_isolation(self):
        w = self._weight()
        visible = self.env["gest_agri.animal.weight"].with_user(self.user_a).search([])
        self.assertNotIn(w, visible)

    def test_98_meat_isolation(self):
        mp = self._meat()
        visible = self.env["gest_agri.meat.production"].with_user(self.user_a).search([])
        self.assertNotIn(mp, visible)

    def test_99_egg_isolation(self):
        e = self._egg()
        visible = self.env["gest_agri.egg.production"].with_user(self.user_a).search([])
        self.assertNotIn(e, visible)

    def test_100_session_isolation(self):
        s = self.env["gest_agri.milking.session"].create({"farm_id": self.farm_a.id})
        visible = self.env["gest_agri.milking.session"].with_user(self.user_a).search([])
        self.assertNotIn(s, visible)
