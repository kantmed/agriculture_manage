# -*- coding: utf-8 -*-
"""Tests complémentaires — audit correctif Prompt 63 BIS.

Ces tests sécurisent les annulations, la cohérence des historiques, la création
des nouveau-nés et la capacité des mortalités de lot. Ils vérifient le refus
explicite des opérations dangereuses pour protéger l'historique.
"""
from datetime import date, datetime, timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestReproductionAudit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")

        cls.user_a = cls._create_user("repro_audit_user_a", [cls.base_user, cls.group_user])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme audit A", "code": "AUA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme audit B", "code": "AUB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create({"name": "Site audit A", "code": "SAU", "farm_id": cls.farm_a.id})

        cls.species = cls.env["gest_agri.livestock.species"].create(
            {"name": "Bovin audit", "code": "BAU", "company_id": cls.company.id, "gestation_duration_days": 280}
        )
        cls.breed = cls.env["gest_agri.livestock.breed"].create(
            {"name": "Holstein audit", "code": "HAU", "company_id": cls.company.id, "species_id": cls.species.id}
        )

        cls.female = cls._active_animal("Vache audit", "female", breed=cls.breed)
        cls.male = cls._active_animal("Taureau audit", "male", breed=cls.breed)

        cls.lot = cls.env["gest_agri.animal.lot"].create(
            {"name": "Lot audit", "species_id": cls.species.id, "farm_id": cls.farm_a.id}
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

    @classmethod
    def _active_animal(cls, name, sex, breed=None, farm=None, lot=None, activate=True):
        animal = cls.env["gest_agri.animal"].create({
            "name": name, "species_id": cls.species.id, "sex": sex,
            "breed_id": breed.id if breed else False,
            "farm_id": (farm or cls.farm_a).id,
            "lot_id": lot.id if lot else False,
            "birth_date": date(2020, 1, 1),
        })
        if activate:
            animal.action_activate()
        return animal

    def _reproduction(self, female=None, male=None, **kwargs):
        vals = {
            "female_id": (female or self.female).id,
            "male_id": (male if male is not None else self.male).id,
            "event_date": date(2026, 1, 10),
        }
        vals.update(kwargs)
        return self.env["gest_agri.animal.reproduction"].create(vals)

    def _gestation(self, repro=None, start=None, confirm=False):
        vals = {
            "reproduction_id": (repro or self._reproduction()).id,
            "start_date": start or date(2026, 2, 1),
        }
        gestation = self.env["gest_agri.animal.gestation"].create(vals)
        if confirm:
            gestation.action_confirm()
        return gestation

    def _birth(self, gestation, validate=False, **kwargs):
        vals = {
            "gestation_id": gestation.id,
            "birth_datetime": datetime(2026, 11, 1, 8, 0),
            "total_count": 1, "alive_count": 1, "stillborn_count": 0,
        }
        vals.update(kwargs)
        birth = self.env["gest_agri.animal.birth"].create(vals)
        if validate:
            birth.action_validate()
        return birth

    def _individual_mortality(self, animal, validate=False):
        mortality = self.env["gest_agri.animal.mortality"].create({
            "animal_id": animal.id,
            "death_datetime": datetime(2026, 5, 1, 10, 0),
            "mortality_type": "disease",
        })
        if validate:
            mortality.action_validate()
        return mortality

    def _lot_mortality(self, lot, count, validate=False):
        mortality = self.env["gest_agri.animal.mortality"].create({
            "lot_id": lot.id,
            "death_datetime": datetime(2026, 5, 1, 10, 0),
            "mortality_type": "disease",
            "animal_count": count,
        })
        if validate:
            mortality.action_validate()
        return mortality

    # ==================================================================
    # 1. Annulation des mortalités
    # ==================================================================
    def test_mortality_cancel_draft_allowed(self):
        animal = self._active_animal("Brouillon mort", "male")
        mortality = self._individual_mortality(animal)
        mortality.action_cancel()
        self.assertEqual(mortality.state, "cancelled")
        self.assertEqual(animal.state, "active")

    def test_mortality_cancel_validated_restores_active_state(self):
        animal = self._active_animal("Restauration active", "male")
        mortality = self._individual_mortality(animal, validate=True)
        self.assertEqual(animal.state, "dead")
        mortality.action_cancel()
        self.assertEqual(mortality.state, "cancelled")
        self.assertEqual(animal.state, "active")

    def test_mortality_cancel_validated_restores_draft_state(self):
        animal = self._active_animal("Restauration brouillon", "male", activate=False)
        self.assertEqual(animal.state, "draft")
        mortality = self._individual_mortality(animal, validate=True)
        self.assertEqual(animal.state, "dead")
        mortality.action_cancel()
        self.assertEqual(animal.state, "draft")

    def test_mortality_cancel_validated_restores_sold_state(self):
        animal = self._active_animal("Restauration vendu", "male")
        animal.action_sell()
        self.assertEqual(animal.state, "sold")
        mortality = self._individual_mortality(animal, validate=True)
        mortality.action_cancel()
        self.assertEqual(animal.state, "sold")

    def test_mortality_cancel_refused_if_animal_state_changed(self):
        animal = self._active_animal("Changement état", "male")
        mortality = self._individual_mortality(animal, validate=True)
        # Modification légitime intervenue entre-temps.
        animal.with_context(gest_agri_animal_state_transition=True).write({"state": "retired"})
        with self.assertRaises(UserError):
            mortality.action_cancel()
        self.assertEqual(mortality.state, "validated")
        self.assertEqual(animal.state, "retired")

    def test_mortality_cancel_refused_without_previous_state(self):
        animal = self._active_animal("Sans état antérieur", "male")
        mortality = self._individual_mortality(animal, validate=True)
        mortality.write({"previous_animal_state": False})
        with self.assertRaises(UserError):
            mortality.action_cancel()
        self.assertEqual(mortality.state, "validated")

    def test_mortality_cancel_twice_forbidden(self):
        animal = self._active_animal("Double annulation", "male")
        mortality = self._individual_mortality(animal)
        mortality.action_cancel()
        with self.assertRaises(UserError):
            mortality.action_cancel()

    def test_mortality_cancel_updates_indicators(self):
        animal = self._active_animal("Indicateurs annulation", "male")
        mortality = self._individual_mortality(animal, validate=True)
        self.assertEqual(animal.mortality_count, 1)
        self.assertTrue(animal.is_dead)
        self.assertEqual(animal.death_date, date(2026, 5, 1))
        mortality.action_cancel()
        self.assertEqual(animal.mortality_count, 0)
        self.assertFalse(animal.death_date)
        self.assertFalse(animal.is_dead)

    def test_mortality_lot_cancel_validated_allowed(self):
        self._active_animal("Membre lot annulation", "male", lot=self.lot)
        mortality = self._lot_mortality(self.lot, 1, validate=True)
        self.assertEqual(self.lot.mortality_count, 1)
        mortality.action_cancel()
        self.assertEqual(mortality.state, "cancelled")
        self.assertEqual(self.lot.mortality_count, 0)

    def test_mortality_restored_animal_can_reproduce(self):
        female = self._active_animal("Femelle restaurée", "female")
        mortality = self._individual_mortality(female, validate=True)
        self.assertEqual(female.state, "dead")
        mortality.action_cancel()
        self.assertEqual(female.state, "active")
        event = self._reproduction(female=female, male=self.male)
        self.assertTrue(event.id)

    def test_mortality_validation_then_cancel_keeps_history(self):
        animal = self._active_animal("Historique conservé", "male")
        mortality = self._individual_mortality(animal, validate=True)
        mortality.action_cancel()
        # La mortalité annulée reste consultable (traçabilité conservée).
        self.assertTrue(mortality.exists())
        self.assertEqual(mortality.state, "cancelled")

    # ==================================================================
    # 2. Annulation des mises bas
    # ==================================================================
    def test_birth_cancel_draft_allowed(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation)
        birth.action_cancel()
        self.assertEqual(birth.state, "cancelled")

    def test_birth_cancel_validated_forbidden(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True)
        with self.assertRaises(UserError):
            birth.action_cancel()
        self.assertEqual(birth.state, "validated")

    def test_birth_cancel_validated_forbidden_with_newborns(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True, total_count=1, alive_count=1)
        self.env["gest_agri.animal.birth.newborn"].create(
            {"birth_id": birth.id, "name": "Petit", "sex": "female", "breed_id": self.breed.id}
        )
        birth.action_create_newborn_animals()
        with self.assertRaises(UserError):
            birth.action_cancel()
        # Les nouveau-nés créés ne sont pas supprimés.
        self.assertEqual(len(birth.newborn_ids.filtered("animal_id")), 1)

    def test_birth_cancel_validated_keeps_gestation_terminated(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True)
        with self.assertRaises(UserError):
            birth.action_cancel()
        self.assertEqual(gestation.state, "terminated")
        self.assertEqual(birth.state, "validated")

    def test_birth_validate_twice_forbidden(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True)
        with self.assertRaises(UserError):
            birth.action_validate()

    def test_birth_validate_requires_confirmed_gestation(self):
        gestation = self._gestation(confirm=False)
        birth = self._birth(gestation)
        with self.assertRaises(UserError):
            birth.action_validate()
        self.assertEqual(birth.state, "draft")

    def test_birth_indicator_excludes_cancelled(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation)
        self.assertEqual(self.female.birth_count, 1)
        birth.action_cancel()
        self.assertEqual(self.female.birth_count, 0)
        self.assertEqual(self.female.alive_newborn_count, 0)

    def test_birth_delete_validated_forbidden(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True)
        with self.assertRaises(UserError):
            birth.unlink()

    # ==================================================================
    # 3. Création des nouveau-nés
    # ==================================================================
    def test_newborn_create_requires_validated_birth(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation)
        self.env["gest_agri.animal.birth.newborn"].create(
            {"birth_id": birth.id, "name": "Petit", "sex": "female"}
        )
        with self.assertRaises(UserError):
            birth.action_create_newborn_animals()

    def test_newborn_create_idempotent(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True, total_count=2, alive_count=2)
        self.env["gest_agri.animal.birth.newborn"].create([
            {"birth_id": birth.id, "name": "Jumeau 1", "sex": "female", "breed_id": self.breed.id},
            {"birth_id": birth.id, "name": "Jumeau 2", "sex": "male", "breed_id": self.breed.id},
        ])
        birth.action_create_newborn_animals()
        first = self.env["gest_agri.animal"].search([("birth_id", "=", birth.id)])
        self.assertEqual(len(first), 2)
        # Second appel : aucun doublon.
        birth.action_create_newborn_animals()
        second = self.env["gest_agri.animal"].search([("birth_id", "=", birth.id)])
        self.assertEqual(len(second), 2)

    def test_newborn_atomic_no_partial_creation(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True, total_count=2, alive_count=2)
        self.env["gest_agri.animal.birth.newborn"].create([
            {"birth_id": birth.id, "name": "Valide", "sex": "female", "breed_id": self.breed.id},
            {"birth_id": birth.id, "name": "Sans sexe"},
        ])
        with self.assertRaises(UserError):
            birth.action_create_newborn_animals()
        # Aucune création partielle.
        self.assertEqual(self.env["gest_agri.animal"].search_count([("birth_id", "=", birth.id)]), 0)

    def test_newborn_count_exceeds_alive_refused(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True, total_count=1, alive_count=1)
        self.env["gest_agri.animal.birth.newborn"].create([
            {"birth_id": birth.id, "name": "Trop 1", "sex": "female"},
            {"birth_id": birth.id, "name": "Trop 2", "sex": "male"},
        ])
        with self.assertRaises(UserError):
            birth.action_create_newborn_animals()
        self.assertEqual(self.env["gest_agri.animal"].search_count([("birth_id", "=", birth.id)]), 0)

    def test_newborn_creation_full_coherence(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True, total_count=1, alive_count=1)
        birth.write({"site_id": self.site_a.id})
        self.env["gest_agri.animal.birth.newborn"].create(
            {"birth_id": birth.id, "name": "Cohérent", "sex": "female", "breed_id": self.breed.id, "lot_id": self.lot.id}
        )
        birth.action_create_newborn_animals()
        animal = self.env["gest_agri.animal"].search([("birth_id", "=", birth.id)], limit=1)
        self.assertEqual(animal.species_id, self.species)
        self.assertEqual(animal.breed_id, self.breed)
        self.assertEqual(animal.farm_id, self.farm_a)
        self.assertEqual(animal.site_id, self.site_a)
        self.assertEqual(animal.lot_id, self.lot)
        self.assertEqual(animal.mother_id, self.female)
        self.assertEqual(animal.father_id, self.male)
        self.assertEqual(animal.birth_date, date(2026, 11, 1))

    def test_newborn_existing_animal_line_not_recreated(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True, total_count=2, alive_count=2)
        existing = self._active_animal("Déjà enregistré", "male")
        self.env["gest_agri.animal.birth.newborn"].create([
            {"birth_id": birth.id, "name": "Lien existant", "sex": "male", "animal_id": existing.id},
            {"birth_id": birth.id, "name": "Nouveau", "sex": "female"},
        ])
        birth.action_create_newborn_animals()
        animals = self.env["gest_agri.animal"].search([("birth_id", "=", birth.id)])
        self.assertEqual(len(animals), 1)
        self.assertEqual(animals, self.env["gest_agri.animal"].search([("name", "=", "Nouveau")]))

    def test_newborn_foreign_animal_refused(self):
        gestation = self._gestation(confirm=True)
        birth = self._birth(gestation, validate=True)
        foreign = self._active_animal("Étranger", "male", farm=self.farm_b)
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.birth.newborn"].create(
                {"birth_id": birth.id, "name": "Lien étranger", "sex": "male", "animal_id": foreign.id}
            )

    # ==================================================================
    # 4. Indicateurs et cohérence des historiques
    # ==================================================================
    def test_reproduction_indicator_excludes_cancelled(self):
        event = self._reproduction()
        self.assertEqual(self.female.reproduction_count, 1)
        event.action_cancel()
        self.assertEqual(self.female.reproduction_count, 0)

    def test_reproduction_cancel_with_gestation_forbidden(self):
        event = self._reproduction()
        self._gestation(repro=event)
        with self.assertRaises(UserError):
            event.action_cancel()
        self.assertEqual(event.state, "draft")

    def test_reproduction_cancel_confirmed_without_gestation_allowed(self):
        event = self._reproduction()
        event.action_confirm()
        event.action_cancel()
        self.assertEqual(event.state, "cancelled")

    def test_reproduction_delete_with_gestation_forbidden(self):
        event = self._reproduction()
        self._gestation(repro=event)
        with self.assertRaises(UserError):
            event.unlink()

    def test_gestation_failed_indicator_counts(self):
        gestation = self._gestation(confirm=True)
        gestation.action_abort()
        self.assertEqual(self.female.gestation_failed_count, 1)
        self.assertEqual(self.female.gestation_terminated_count, 0)

    def test_gestation_terminated_indicator_counts(self):
        gestation = self._gestation(confirm=True)
        gestation.action_terminate()
        self.assertEqual(self.female.gestation_terminated_count, 1)

    def test_animal_indicators_after_full_cycle(self):
        event = self._reproduction()
        event.action_confirm()
        gestation = self._gestation(repro=event, confirm=True)
        birth = self._birth(gestation, validate=True, total_count=2, alive_count=1, stillborn_count=1)
        self.assertEqual(self.female.reproduction_count, 1)
        self.assertEqual(self.female.gestation_count, 1)
        self.assertEqual(self.female.gestation_terminated_count, 1)
        self.assertEqual(self.female.birth_count, 1)
        self.assertEqual(self.female.alive_newborn_count, 1)
        self.assertEqual(self.female.stillborn_count, 1)
        self.assertEqual(self.female.last_birth_date, date(2026, 11, 1))

    # ==================================================================
    # 5. Mortalités de lot (capacité cumulée et concurrence)
    # ==================================================================
    def _lot_with_members(self, count):
        for index in range(count):
            self._active_animal(f"Membre {index}", "male", lot=self.lot)
        return self.lot

    def test_lot_mortality_cumulative_capacity_enforced(self):
        self._lot_with_members(3)
        self._lot_mortality(self.lot, 2)
        with self.assertRaises(ValidationError):
            self._lot_mortality(self.lot, 2)

    def test_lot_mortality_validated_blocks_over_declaration(self):
        self._lot_with_members(3)
        self._lot_mortality(self.lot, 3, validate=True)
        with self.assertRaises(ValidationError):
            self._lot_mortality(self.lot, 1)

    def test_lot_mortality_cancel_frees_capacity(self):
        self._lot_with_members(3)
        mortality = self._lot_mortality(self.lot, 3, validate=True)
        with self.assertRaises(ValidationError):
            self._lot_mortality(self.lot, 1)
        mortality.action_cancel()
        freed = self._lot_mortality(self.lot, 3)
        self.assertTrue(freed.id)

    def test_lot_mortality_indicator_after_cancel(self):
        self._lot_with_members(2)
        mortality = self._lot_mortality(self.lot, 2, validate=True)
        self.assertEqual(self.lot.mortality_count, 1)
        mortality.action_cancel()
        self.assertEqual(self.lot.mortality_count, 0)

    def test_lot_mortality_requires_positive_count(self):
        self._lot_with_members(1)
        with self.assertRaises(ValidationError):
            self._lot_mortality(self.lot, 0)

    # ==================================================================
    # 6. Sécurité / isolation
    # ==================================================================
    def test_audit_reproduction_isolation(self):
        event = self._reproduction()
        visible = self.env["gest_agri.animal.reproduction"].with_user(self.user_a).search([])
        self.assertNotIn(event, visible)

    def test_audit_mortality_isolation(self):
        animal = self._active_animal("Isolation mort", "male")
        mortality = self._individual_mortality(animal)
        visible = self.env["gest_agri.animal.mortality"].with_user(self.user_a).search([])
        self.assertNotIn(mortality, visible)

    def test_audit_direct_state_write_forbidden(self):
        animal = self._active_animal("État direct", "male")
        mortality = self._individual_mortality(animal)
        with self.assertRaises(AccessError):
            mortality.write({"state": "validated"})
