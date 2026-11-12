# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

import psycopg2

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


# L'index unique PostgreSQL est levé au moment de l'INSERT, donc avant la
# contrainte Python. Au niveau web, Odoo convertit cette erreur en
# ValidationError (odoo/http/retrying.py) ; au niveau ORM, l'erreur brute
# psycopg2 est propagée. Les deux sont acceptées (cf. test_patrimony.py).
UNIQUE_ERRORS = (ValidationError, psycopg2.errors.UniqueViolation)


class TestReproduction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")

        cls.user_a = cls._create_user("repro_user_a", [cls.base_user, cls.group_user])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme repro A", "code": "RA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme repro B", "code": "RB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create({"name": "Site RA", "code": "SRA", "farm_id": cls.farm_a.id})
        cls.site_b = cls.env["gest_agri.site"].create({"name": "Site RB", "code": "SRB", "farm_id": cls.farm_b.id})

        cls.species = cls.env["gest_agri.livestock.species"].create(
            {"name": "Bovin", "code": "BOV", "company_id": cls.company.id, "gestation_duration_days": 280}
        )
        cls.species_sheep = cls.env["gest_agri.livestock.species"].create(
            {"name": "Ovin", "code": "OVI", "company_id": cls.company.id}
        )
        cls.breed = cls.env["gest_agri.livestock.breed"].create(
            {"name": "Holstein", "code": "HOL", "company_id": cls.company.id, "species_id": cls.species.id}
        )

        cls.female = cls.env["gest_agri.animal"].create(
            {"name": "Vache A", "species_id": cls.species.id, "breed_id": cls.breed.id,
             "sex": "female", "farm_id": cls.farm_a.id, "site_id": cls.site_a.id,
             "birth_date": date(2020, 1, 1)}
        )
        cls.female.action_activate()
        cls.male = cls.env["gest_agri.animal"].create(
            {"name": "Taureau A", "species_id": cls.species.id, "sex": "male",
             "farm_id": cls.farm_a.id, "birth_date": date(2019, 1, 1)}
        )
        cls.male.action_activate()
        cls.female_sheep = cls.env["gest_agri.animal"].create(
            {"name": "Brebis", "species_id": cls.species_sheep.id, "sex": "female",
             "farm_id": cls.farm_a.id, "birth_date": date(2021, 1, 1)}
        )
        cls.female_sheep.action_activate()

        cls.lot = cls.env["gest_agri.animal.lot"].create(
            {"name": "Lot repro", "species_id": cls.species.id, "farm_id": cls.farm_a.id}
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

    def _new_reproduction(self, **kwargs):
        vals = {"female_id": self.female.id, "male_id": self.male.id, "event_date": date(2026, 1, 10)}
        vals.update(kwargs)
        return self.env["gest_agri.animal.reproduction"].create(vals)

    def _new_gestation(self, **kwargs):
        repro = self._new_reproduction()
        vals = {"reproduction_id": repro.id, "start_date": date(2026, 2, 1)}
        vals.update(kwargs)
        return self.env["gest_agri.animal.gestation"].create(vals)

    # ------------------------------------------------------------------
    # Événements reproductifs
    # ------------------------------------------------------------------
    def test_reproduction_creation(self):
        r = self._new_reproduction()
        self.assertTrue(r.id)
        self.assertTrue(r.name.startswith("REP/"))
        self.assertEqual(r.farm_id, self.farm_a)
        self.assertEqual(r.species_id, self.species)
        self.assertEqual(r.state, "draft")

    def test_reproduction_confirm(self):
        r = self._new_reproduction()
        r.action_confirm()
        self.assertEqual(r.state, "confirmed")

    def test_reproduction_cancel(self):
        r = self._new_reproduction()
        r.action_cancel()
        self.assertEqual(r.state, "cancelled")

    def test_reproduction_female_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.animal.reproduction"].create({"event_date": date(2026, 1, 10)})

    def test_reproduction_female_sex(self):
        with self.assertRaises(ValidationError):
            self._new_reproduction(female_id=self.male.id)

    def test_reproduction_male_sex(self):
        with self.assertRaises(ValidationError):
            self._new_reproduction(male_id=self.female.id)

    def test_reproduction_species_coherence(self):
        with self.assertRaises(ValidationError):
            self._new_reproduction(male_id=self.female_sheep.id)

    def test_reproduction_site_farm_coherence(self):
        with self.assertRaises(ValidationError):
            self._new_reproduction(site_id=self.site_b.id)

    def test_reproduction_date_before_birth(self):
        with self.assertRaises(ValidationError):
            self._new_reproduction(event_date=date(2010, 1, 1))

    def test_reproduction_direct_state_write_forbidden(self):
        r = self._new_reproduction()
        with self.assertRaises(AccessError):
            r.write({"state": "confirmed"})

    def test_reproduction_delete_draft_allowed(self):
        r = self._new_reproduction()
        r.unlink()
        self.assertFalse(self.env["gest_agri.animal.reproduction"].browse(r.id).exists())

    def test_reproduction_delete_confirmed_forbidden(self):
        r = self._new_reproduction()
        r.action_confirm()
        with self.assertRaises(UserError):
            r.unlink()

    def test_reproduction_dead_animal_forbidden(self):
        dead = self.env["gest_agri.animal"].create(
            {"name": "Morte", "species_id": self.species.id, "sex": "female", "farm_id": self.farm_a.id}
        )
        dead.action_activate()
        dead.with_context(gest_agri_animal_state_transition=True).write({"state": "dead"})
        with self.assertRaises(ValidationError):
            self._new_reproduction(female_id=dead.id, male_id=False)

    # ------------------------------------------------------------------
    # Gestations
    # ------------------------------------------------------------------
    def test_gestation_creation(self):
        g = self._new_gestation()
        self.assertTrue(g.id)
        self.assertTrue(g.name.startswith("GES/"))
        self.assertEqual(g.female_id, self.female)
        self.assertEqual(g.male_id, self.male)

    def test_gestation_expected_birth_date_computed(self):
        g = self._new_gestation(start_date=date(2026, 2, 1))
        self.assertEqual(g.expected_birth_date, date(2026, 2, 1) + timedelta(days=280))

    def test_gestation_no_duration_leaves_expected_empty(self):
        repro = self.env["gest_agri.animal.reproduction"].create(
            {"female_id": self.female_sheep.id, "event_date": date(2026, 1, 10)}
        )
        g = self.env["gest_agri.animal.gestation"].create(
            {"reproduction_id": repro.id, "start_date": date(2026, 2, 1)}
        )
        self.assertFalse(g.expected_birth_date)

    def test_gestation_duplicate_for_event_forbidden(self):
        g = self._new_gestation()
        with self.assertRaises(UNIQUE_ERRORS):
            self.env["gest_agri.animal.gestation"].create(
                {"reproduction_id": g.reproduction_id.id, "start_date": date(2026, 2, 2)}
            )

    def test_gestation_female_coherence(self):
        repro = self._new_reproduction()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.gestation"].create(
                {"reproduction_id": repro.id, "female_id": self.female_sheep.id, "start_date": date(2026, 2, 1)}
            )

    def test_gestation_date_before_event(self):
        repro = self._new_reproduction(event_date=date(2026, 3, 1))
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.gestation"].create(
                {"reproduction_id": repro.id, "start_date": date(2026, 2, 1)}
            )

    def test_gestation_expected_before_start(self):
        repro = self._new_reproduction()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.gestation"].create(
                {"reproduction_id": repro.id, "start_date": date(2026, 2, 1),
                 "expected_birth_date": date(2026, 1, 15)}
            )

    def test_gestation_confirm(self):
        g = self._new_gestation()
        g.action_confirm()
        self.assertEqual(g.state, "confirmed")
        self.assertTrue(g.confirmation_date)

    def test_gestation_terminate(self):
        g = self._new_gestation()
        g.action_confirm()
        g.action_terminate()
        self.assertEqual(g.state, "terminated")
        self.assertTrue(g.actual_end_date)

    def test_gestation_abort(self):
        g = self._new_gestation()
        g.action_abort()
        self.assertEqual(g.state, "aborted")
        self.assertTrue(g.actual_end_date)

    def test_gestation_interrupt(self):
        g = self._new_gestation()
        g.action_confirm()
        g.action_interrupt()
        self.assertEqual(g.state, "interrupted")

    def test_gestation_locked_after_terminate(self):
        g = self._new_gestation()
        g.action_confirm()
        g.action_terminate()
        with self.assertRaises(UserError):
            g.write({"start_date": date(2026, 3, 1)})

    def test_gestation_direct_state_write_forbidden(self):
        g = self._new_gestation()
        with self.assertRaises(AccessError):
            g.write({"state": "confirmed"})

    def test_gestation_delete_to_confirm_allowed(self):
        g = self._new_gestation()
        g.unlink()
        self.assertFalse(self.env["gest_agri.animal.gestation"].browse(g.id).exists())

    def test_gestation_delete_confirmed_forbidden(self):
        g = self._new_gestation()
        g.action_confirm()
        with self.assertRaises(UserError):
            g.unlink()

    def test_species_incoherent_duration_refused(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.livestock.species"].create(
                {"name": "Test dur", "code": "TDU", "company_id": self.company.id, "gestation_duration_days": -5}
            )

    # ------------------------------------------------------------------
    # Mises bas et naissances
    # ------------------------------------------------------------------
    def _confirmed_gestation(self):
        g = self._new_gestation()
        g.action_confirm()
        return g

    def test_birth_creation(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1, 8, 0),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        self.assertTrue(b.id)
        self.assertTrue(b.name.startswith("NAI/"))
        self.assertEqual(b.mother_id, self.female)
        self.assertEqual(b.father_id, self.male)

    def test_birth_counts_coherence(self):
        g = self._confirmed_gestation()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.birth"].create(
                {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
                 "total_count": 2, "alive_count": 1, "stillborn_count": 0}
            )

    def test_birth_negative_counts(self):
        g = self._confirmed_gestation()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.birth"].create(
                {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
                 "total_count": 0, "alive_count": -1, "stillborn_count": 1}
            )

    def test_birth_multiple(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 3, "alive_count": 2, "stillborn_count": 1}
        )
        self.assertEqual(b.total_count, 3)
        self.assertEqual(b.alive_count, 2)
        self.assertEqual(b.stillborn_count, 1)

    def test_birth_validate(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        b.action_validate()
        self.assertEqual(b.state, "validated")

    def test_birth_validate_terminates_gestation(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        b.action_validate()
        self.assertEqual(g.state, "terminated")

    def test_birth_direct_state_write_forbidden(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        with self.assertRaises(AccessError):
            b.write({"state": "validated"})

    def test_birth_father_species_coherence(self):
        g = self._confirmed_gestation()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.birth"].create(
                {"gestation_id": g.id, "father_id": self.female_sheep.id,
                 "birth_datetime": datetime(2026, 11, 1), "total_count": 1, "alive_count": 1, "stillborn_count": 0}
            )

    def test_birth_create_newborn_animals(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 2, "alive_count": 2, "stillborn_count": 0}
        )
        b.action_validate()
        self.env["gest_agri.animal.birth.newborn"].create([
            {"birth_id": b.id, "name": "Veau 1", "sex": "female", "breed_id": self.breed.id},
            {"birth_id": b.id, "name": "Veau 2", "sex": "male", "breed_id": self.breed.id},
        ])
        b.action_create_newborn_animals()
        self.assertEqual(len(b.newborn_ids.filtered("animal_id")), 2)
        created = b.newborn_ids.mapped("animal_id")
        self.assertTrue(all(a.mother_id == self.female for a in created))
        self.assertTrue(all(a.father_id == self.male for a in created))
        self.assertTrue(all(a.species_id == self.species for a in created))
        self.assertTrue(all(a.farm_id == self.farm_a for a in created))

    def test_birth_newborn_requires_sex(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        b.action_validate()
        self.env["gest_agri.animal.birth.newborn"].create({"birth_id": b.id, "name": "Sans sexe"})
        with self.assertRaises(UserError):
            b.action_create_newborn_animals()

    def test_birth_newborn_existing_animal_coherence(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        foreign = self.env["gest_agri.animal"].create(
            {"name": "Étranger", "species_id": self.species.id, "sex": "male", "farm_id": self.farm_b.id}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.birth.newborn"].create(
                {"birth_id": b.id, "name": "Lien", "sex": "male", "animal_id": foreign.id}
            )

    def test_birth_delete_draft_allowed(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        b.unlink()
        self.assertFalse(self.env["gest_agri.animal.birth"].browse(b.id).exists())

    def test_birth_delete_validated_forbidden(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        b.action_validate()
        with self.assertRaises(UserError):
            b.unlink()

    # ------------------------------------------------------------------
    # Mortalité
    # ------------------------------------------------------------------
    def _animal_for_death(self):
        a = self.env["gest_agri.animal"].create(
            {"name": "À décéder", "species_id": self.species.id, "sex": "male", "farm_id": self.farm_a.id}
        )
        a.action_activate()
        return a

    def test_mortality_individual_creation(self):
        a = self._animal_for_death()
        m = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": a.id, "death_datetime": datetime(2026, 5, 1, 10, 0), "mortality_type": "disease"}
        )
        self.assertTrue(m.id)
        self.assertTrue(m.name.startswith("MOR/"))
        self.assertEqual(m.farm_id, self.farm_a)

    def test_mortality_requires_animal_or_lot(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.mortality"].create({"death_datetime": datetime(2026, 5, 1)})

    def test_mortality_animal_or_lot_exclusive(self):
        a = self._animal_for_death()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.mortality"].create(
                {"animal_id": a.id, "lot_id": self.lot.id, "death_datetime": datetime(2026, 5, 1)}
            )

    def test_mortality_validate_sets_animal_dead(self):
        a = self._animal_for_death()
        m = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": a.id, "death_datetime": datetime(2026, 5, 1, 10, 0), "mortality_type": "accident"}
        )
        m.action_validate()
        self.assertEqual(a.state, "dead")
        self.assertTrue(a.is_dead)
        self.assertEqual(a.death_date, date(2026, 5, 1))

    def test_mortality_duplicate_individual_forbidden(self):
        a = self._animal_for_death()
        m1 = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": a.id, "death_datetime": datetime(2026, 5, 1, 10, 0), "mortality_type": "disease"}
        )
        m1.action_validate()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.mortality"].create(
                {"animal_id": a.id, "death_datetime": datetime(2026, 5, 2, 10, 0), "mortality_type": "disease"}
            )

    def test_mortality_lot_creation(self):
        a1 = self.env["gest_agri.animal"].create(
            {"name": "Lot membre 1", "species_id": self.species.id, "sex": "male",
             "farm_id": self.farm_a.id, "lot_id": self.lot.id}
        )
        m = self.env["gest_agri.animal.mortality"].create(
            {"lot_id": self.lot.id, "death_datetime": datetime(2026, 5, 1, 10, 0),
             "mortality_type": "disease", "animal_count": 1}
        )
        self.assertEqual(m.farm_id, self.farm_a)
        self.assertGreaterEqual(self.lot.member_count, 1)

    def test_mortality_lot_count_positive(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.mortality"].create(
                {"lot_id": self.lot.id, "death_datetime": datetime(2026, 5, 1),
                 "mortality_type": "disease", "animal_count": 0}
            )

    def test_mortality_lot_count_exceeds(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.mortality"].create(
                {"lot_id": self.lot.id, "death_datetime": datetime(2026, 5, 1),
                 "mortality_type": "disease", "animal_count": 999}
            )

    def test_mortality_lot_duplicate_forbidden(self):
        self.env["gest_agri.animal"].create(
            {"name": "Lot membre dup", "species_id": self.species.id, "sex": "male",
             "farm_id": self.farm_a.id, "lot_id": self.lot.id}
        )
        self.env["gest_agri.animal.mortality"].create(
            {"lot_id": self.lot.id, "death_datetime": datetime(2026, 5, 1, 10, 0),
             "mortality_type": "disease", "animal_count": 1}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.mortality"].create(
                {"lot_id": self.lot.id, "death_datetime": datetime(2026, 5, 1, 10, 0),
                 "mortality_type": "disease", "animal_count": 1}
            )

    def test_mortality_direct_state_write_forbidden(self):
        a = self._animal_for_death()
        m = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": a.id, "death_datetime": datetime(2026, 5, 1), "mortality_type": "disease"}
        )
        with self.assertRaises(AccessError):
            m.write({"state": "validated"})

    def test_mortality_delete_draft_allowed(self):
        a = self._animal_for_death()
        m = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": a.id, "death_datetime": datetime(2026, 5, 1), "mortality_type": "disease"}
        )
        m.unlink()
        self.assertFalse(self.env["gest_agri.animal.mortality"].browse(m.id).exists())

    def test_mortality_delete_validated_forbidden(self):
        a = self._animal_for_death()
        m = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": a.id, "death_datetime": datetime(2026, 5, 1), "mortality_type": "disease"}
        )
        m.action_validate()
        with self.assertRaises(UserError):
            m.unlink()

    # ------------------------------------------------------------------
    # Indicateurs et intégration
    # ------------------------------------------------------------------
    def test_animal_reproduction_indicators(self):
        r = self._new_reproduction()
        g = self.env["gest_agri.animal.gestation"].create(
            {"reproduction_id": r.id, "start_date": date(2026, 2, 1)}
        )
        g.action_confirm()
        self.assertEqual(self.female.reproduction_count, 1)
        self.assertEqual(self.female.gestation_count, 1)
        self.assertEqual(self.female.next_expected_birth_date, date(2026, 2, 1) + timedelta(days=280))

    def test_animal_birth_indicators(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1, 9, 0),
             "total_count": 2, "alive_count": 1, "stillborn_count": 1}
        )
        b.action_validate()
        self.assertEqual(self.female.birth_count, 1)
        self.assertEqual(self.female.alive_newborn_count, 1)
        self.assertEqual(self.female.stillborn_count, 1)
        self.assertEqual(self.female.last_birth_date, date(2026, 11, 1))
        self.assertEqual(self.female.gestation_terminated_count, 1)

    def test_animal_mortality_indicators(self):
        a = self._animal_for_death()
        m = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": a.id, "death_datetime": datetime(2026, 5, 1), "mortality_type": "disease"}
        )
        m.action_validate()
        self.assertEqual(a.mortality_count, 1)
        self.assertTrue(a.is_dead)

    def test_lot_mortality_indicator(self):
        self.env["gest_agri.animal"].create(
            {"name": "Lot membre ind", "species_id": self.species.id, "sex": "male",
             "farm_id": self.farm_a.id, "lot_id": self.lot.id}
        )
        m = self.env["gest_agri.animal.mortality"].create(
            {"lot_id": self.lot.id, "death_datetime": datetime(2026, 5, 1), "mortality_type": "disease", "animal_count": 1}
        )
        m.action_validate()
        self.assertEqual(self.lot.mortality_count, 1)

    def test_reproduction_linked_to_health_integration(self):
        # Intégration : une consultation sanitaire reste liée à un animal ayant un historique reproductif
        r = self._new_reproduction()
        consult = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.female.id, "reason": "Suivi reproductif"}
        )
        self.assertEqual(consult.animal_id, self.female)
        self.assertEqual(self.female.reproduction_count, 1)

    # ------------------------------------------------------------------
    # Sécurité / isolation
    # ------------------------------------------------------------------
    def test_reproduction_isolation(self):
        r = self._new_reproduction()
        visible = self.env["gest_agri.animal.reproduction"].with_user(self.user_a).search([])
        self.assertNotIn(r, visible)

    def test_gestation_isolation(self):
        g = self._new_gestation()
        visible = self.env["gest_agri.animal.gestation"].with_user(self.user_a).search([])
        self.assertNotIn(g, visible)

    def test_mortality_isolation(self):
        a = self._animal_for_death()
        m = self.env["gest_agri.animal.mortality"].create(
            {"animal_id": a.id, "death_datetime": datetime(2026, 5, 1), "mortality_type": "disease"}
        )
        visible = self.env["gest_agri.animal.mortality"].with_user(self.user_a).search([])
        self.assertNotIn(m, visible)

    def test_birth_isolation(self):
        g = self._confirmed_gestation()
        b = self.env["gest_agri.animal.birth"].create(
            {"gestation_id": g.id, "birth_datetime": datetime(2026, 11, 1),
             "total_count": 1, "alive_count": 1, "stillborn_count": 0}
        )
        visible = self.env["gest_agri.animal.birth"].with_user(self.user_a).search([])
        self.assertNotIn(b, visible)
