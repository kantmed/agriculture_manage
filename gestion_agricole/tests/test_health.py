# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestHealth(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")

        cls.user_a = cls._create_user("health_user_a", [cls.base_user, cls.group_user])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme santé A", "code": "SA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme santé B", "code": "SB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create({"name": "Site A", "code": "SA", "farm_id": cls.farm_a.id})
        cls.species = cls.env["gest_agri.livestock.species"].create(
            {"name": "Bovin", "code": "BOV", "company_id": cls.company.id}
        )
        cls.animal = cls.env["gest_agri.animal"].create(
            {"name": "Vache 1", "species_id": cls.species.id, "sex": "female", "farm_id": cls.farm_a.id}
        )
        cls.lot = cls.env["gest_agri.animal.lot"].create(
            {"name": "Lot A", "species_id": cls.species.id, "farm_id": cls.farm_a.id}
        )
        cls.disease = cls.env["gest_agri.animal.disease"].create(
            {"name": "Fièvre aphteuse", "code": "FA", "company_id": cls.company.id, "species_ids": [(4, cls.species.id)]}
        )
        cls.partner_vet = cls.env["res.partner"].create({"name": "Vétérinaire"})

    @classmethod
    def _create_user(cls, login, groups):
        group_ids = [g.id if hasattr(g, "id") else int(g) for g in groups]
        return (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "company_id": cls.company.id,
                    "company_ids": [(6, 0, [cls.company.id])],
                    "group_ids": [(6, 0, group_ids)],
                }
            )
        )

    # ------------------------------------------------------------------
    # Maladies
    # ------------------------------------------------------------------
    def test_disease_creation(self):
        d = self.env["gest_agri.animal.disease"].create(
            {"name": "Brucellose", "code": "BRU", "company_id": self.company.id}
        )
        self.assertTrue(d.id)

    def test_disease_species_compatibility(self):
        other_species = self.env["gest_agri.livestock.species"].create(
            {"name": "Ovin", "code": "OVI", "company_id": self.company.id}
        )
        other_animal = self.env["gest_agri.animal"].create(
            {"name": "Mouton", "species_id": other_species.id, "sex": "female", "farm_id": self.farm_a.id}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.health"].create(
                {"animal_id": other_animal.id, "observation_date": date(2026, 7, 1), "disease_id": self.disease.id}
            )

    def test_disease_code_unique(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.animal.disease"].create(
                {"name": "Dup", "code": "FA", "company_id": self.company.id}
            )

    # ------------------------------------------------------------------
    # Dossiers sanitaires
    # ------------------------------------------------------------------
    def test_health_creation(self):
        h = self.env["gest_agri.animal.health"].create(
            {"animal_id": self.animal.id, "observation_date": date(2026, 7, 1)}
        )
        self.assertTrue(h.id)
        self.assertTrue(h.name.startswith("SAN/"))

    def test_health_animal_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.animal.health"].create({"observation_date": date(2026, 7, 1)})

    def test_health_date_coherence(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.health"].create(
                {"animal_id": self.animal.id, "observation_date": date(2026, 7, 1), "declaration_date": date(2026, 6, 1)}
            )

    def test_health_site_farm_coherence(self):
        other_site = self.env["gest_agri.site"].create({"name": "S2", "code": "S2", "farm_id": self.farm_b.id})
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.health"].create(
                {"animal_id": self.animal.id, "observation_date": date(2026, 7, 1), "site_id": other_site.id}
            )

    def test_health_workflow(self):
        h = self.env["gest_agri.animal.health"].create(
            {"animal_id": self.animal.id, "observation_date": date(2026, 7, 1)}
        )
        h.action_validate()
        self.assertEqual(h.state, "validated")
        h2 = self.env["gest_agri.animal.health"].create(
            {"animal_id": self.animal.id, "observation_date": date(2026, 7, 2)}
        )
        h2.action_cancel()
        self.assertEqual(h2.state, "cancelled")

    def test_health_direct_state_write_forbidden(self):
        h = self.env["gest_agri.animal.health"].create(
            {"animal_id": self.animal.id, "observation_date": date(2026, 7, 1)}
        )
        with self.assertRaises(AccessError):
            h.write({"state": "validated"})

    def test_health_delete_draft_allowed(self):
        h = self.env["gest_agri.animal.health"].create(
            {"animal_id": self.animal.id, "observation_date": date(2026, 7, 1)}
        )
        h.unlink()
        self.assertFalse(self.env["gest_agri.animal.health"].browse(h.id).exists())

    def test_health_delete_validated_forbidden(self):
        h = self.env["gest_agri.animal.health"].create(
            {"animal_id": self.animal.id, "observation_date": date(2026, 7, 1)}
        )
        h.action_validate()
        with self.assertRaises(UserError):
            h.unlink()

    # ------------------------------------------------------------------
    # Vaccinations
    # ------------------------------------------------------------------
    def test_vaccination_creation(self):
        v = self.env["gest_agri.vaccination"].create(
            {"animal_id": self.animal.id, "vaccine_name": "Vaccin A", "vaccination_date": date(2026, 7, 1)}
        )
        self.assertTrue(v.id)
        self.assertTrue(v.name.startswith("VAC/"))

    def test_vaccination_requires_animal_or_lot(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.vaccination"].create(
                {"vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
            )

    def test_vaccination_animal_or_lot_exclusive(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.vaccination"].create(
                {"animal_id": self.animal.id, "lot_id": self.lot.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
            )

    def test_vaccination_next_due_date(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.vaccination"].create(
                {"animal_id": self.animal.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 15), "next_due_date": date(2026, 7, 1)}
            )

    def test_vaccination_dose_positive(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.vaccination"].create(
                {"animal_id": self.animal.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1), "dose": -1.0}
            )

    def test_vaccination_workflow(self):
        v = self.env["gest_agri.vaccination"].create(
            {"animal_id": self.animal.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
        )
        v.action_done()
        self.assertEqual(v.state, "done")
        v2 = self.env["gest_agri.vaccination"].create(
            {"animal_id": self.animal.id, "vaccine_name": "V2", "vaccination_date": date(2026, 7, 2)}
        )
        v2.action_cancel()
        self.assertEqual(v2.state, "cancelled")

    def test_vaccination_direct_state_write_forbidden(self):
        v = self.env["gest_agri.vaccination"].create(
            {"animal_id": self.animal.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
        )
        with self.assertRaises(AccessError):
            v.write({"state": "done"})

    def test_vaccination_delete_draft_allowed(self):
        v = self.env["gest_agri.vaccination"].create(
            {"animal_id": self.animal.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
        )
        v.unlink()
        self.assertFalse(self.env["gest_agri.vaccination"].browse(v.id).exists())

    def test_vaccination_delete_done_forbidden(self):
        v = self.env["gest_agri.vaccination"].create(
            {"animal_id": self.animal.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
        )
        v.action_done()
        with self.assertRaises(UserError):
            v.unlink()

    def test_vaccination_lot_based(self):
        v = self.env["gest_agri.vaccination"].create(
            {"lot_id": self.lot.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
        )
        self.assertEqual(v.lot_id, self.lot)
        self.assertFalse(v.animal_id)

    # ------------------------------------------------------------------
    # Traitements
    # ------------------------------------------------------------------
    def test_treatment_creation(self):
        t = self.env["gest_agri.animal.treatment"].create(
            {"animal_id": self.animal.id, "product_name": "Antibiotique", "start_date": date(2026, 7, 1)}
        )
        self.assertTrue(t.id)
        self.assertTrue(t.name.startswith("TRT/"))

    def test_treatment_requires_animal_or_lot(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.treatment"].create(
                {"product_name": "P", "start_date": date(2026, 7, 1)}
            )

    def test_treatment_animal_or_lot_exclusive(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.treatment"].create(
                {"animal_id": self.animal.id, "lot_id": self.lot.id, "product_name": "P", "start_date": date(2026, 7, 1)}
            )

    def test_treatment_dates(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.treatment"].create(
                {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 10), "end_date_planned": date(2026, 7, 1)}
            )

    def test_treatment_dosage_positive(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.animal.treatment"].create(
                {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 1), "dosage": -1.0}
            )

    def test_treatment_workflow(self):
        t = self.env["gest_agri.animal.treatment"].create(
            {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 1)}
        )
        t.action_start()
        self.assertEqual(t.state, "in_progress")
        t.action_done()
        self.assertEqual(t.state, "done")
        self.assertTrue(t.end_date_actual)

    def test_treatment_cancel(self):
        t = self.env["gest_agri.animal.treatment"].create(
            {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 1)}
        )
        t.action_start()
        t.action_cancel()
        self.assertEqual(t.state, "cancelled")

    def test_treatment_direct_state_write_forbidden(self):
        t = self.env["gest_agri.animal.treatment"].create(
            {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 1)}
        )
        with self.assertRaises(AccessError):
            t.write({"state": "in_progress"})

    def test_treatment_delete_draft_allowed(self):
        t = self.env["gest_agri.animal.treatment"].create(
            {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 1)}
        )
        t.unlink()
        self.assertFalse(self.env["gest_agri.animal.treatment"].browse(t.id).exists())

    def test_treatment_delete_done_forbidden(self):
        t = self.env["gest_agri.animal.treatment"].create(
            {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 1)}
        )
        t.action_start()
        t.action_done()
        with self.assertRaises(UserError):
            t.unlink()

    # ------------------------------------------------------------------
    # Interventions sanitaires
    # ------------------------------------------------------------------
    def test_sanitary_intervention_creation(self):
        si = self.env["gest_agri.sanitary.intervention"].create(
            {"lot_id": self.lot.id, "intervention_type": "control", "intervention_date": date(2026, 7, 1)}
        )
        self.assertTrue(si.id)
        self.assertTrue(si.name.startswith("ISA/"))

    def test_sanitary_intervention_lot_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.sanitary.intervention"].create(
                {"intervention_type": "control", "intervention_date": date(2026, 7, 1)}
            )

    def test_sanitary_intervention_animal_count_positive(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.sanitary.intervention"].create(
                {"lot_id": self.lot.id, "intervention_type": "control", "intervention_date": date(2026, 7, 1), "animal_count": -1}
            )

    def test_sanitary_intervention_workflow(self):
        si = self.env["gest_agri.sanitary.intervention"].create(
            {"lot_id": self.lot.id, "intervention_type": "control", "intervention_date": date(2026, 7, 1)}
        )
        si.action_done()
        self.assertEqual(si.state, "done")
        si2 = self.env["gest_agri.sanitary.intervention"].create(
            {"lot_id": self.lot.id, "intervention_type": "inspection", "intervention_date": date(2026, 7, 2)}
        )
        si2.action_cancel()
        self.assertEqual(si2.state, "cancelled")

    def test_sanitary_intervention_direct_state_write_forbidden(self):
        si = self.env["gest_agri.sanitary.intervention"].create(
            {"lot_id": self.lot.id, "intervention_type": "control", "intervention_date": date(2026, 7, 1)}
        )
        with self.assertRaises(AccessError):
            si.write({"state": "done"})

    def test_sanitary_intervention_delete_draft_allowed(self):
        si = self.env["gest_agri.sanitary.intervention"].create(
            {"lot_id": self.lot.id, "intervention_type": "control", "intervention_date": date(2026, 7, 1)}
        )
        si.unlink()
        self.assertFalse(self.env["gest_agri.sanitary.intervention"].browse(si.id).exists())

    def test_sanitary_intervention_delete_done_forbidden(self):
        si = self.env["gest_agri.sanitary.intervention"].create(
            {"lot_id": self.lot.id, "intervention_type": "control", "intervention_date": date(2026, 7, 1)}
        )
        si.action_done()
        with self.assertRaises(UserError):
            si.unlink()

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_parse_and_install(self):
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "gestion_agricole")]))

    def test_health_isolation(self):
        other_farm = self.farm_b
        other_animal = self.env["gest_agri.animal"].create(
            {"name": "Autre", "species_id": self.species.id, "sex": "female", "farm_id": other_farm.id}
        )
        h = self.env["gest_agri.animal.health"].create(
            {"animal_id": other_animal.id, "observation_date": date(2026, 7, 1)}
        )
        visible = self.env["gest_agri.animal.health"].with_user(self.user_a).search([])
        self.assertNotIn(h, visible)

    # ------------------------------------------------------------------
    # Consultations vétérinaires
    # ------------------------------------------------------------------
    def test_consultation_creation(self):
        c = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Contrôle"}
        )
        self.assertTrue(c.id)
        self.assertTrue(c.name.startswith("CONS/"))
        self.assertEqual(c.state, "draft")

    def test_consultation_requires_animal_or_lot(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.veterinary.consultation"].create({"reason": "Contrôle"})

    def test_consultation_animal_or_lot_exclusive(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.veterinary.consultation"].create(
                {"animal_id": self.animal.id, "lot_id": self.lot.id, "reason": "Contrôle"}
            )

    def test_consultation_lot_based(self):
        c = self.env["gest_agri.veterinary.consultation"].create(
            {"lot_id": self.lot.id, "reason": "Contrôle du lot"}
        )
        self.assertEqual(c.lot_id, self.lot)
        self.assertFalse(c.animal_id)
        self.assertEqual(c.farm_id, self.farm_a)

    def test_consultation_site_farm_coherence(self):
        other_site = self.env["gest_agri.site"].create({"name": "S3", "code": "S3", "farm_id": self.farm_b.id})
        with self.assertRaises(ValidationError):
            self.env["gest_agri.veterinary.consultation"].create(
                {"animal_id": self.animal.id, "site_id": other_site.id, "reason": "Contrôle"}
            )

    def test_consultation_workflow(self):
        c = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Contrôle"}
        )
        c.action_done()
        self.assertEqual(c.state, "done")
        c2 = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Autre"}
        )
        c2.action_cancel()
        self.assertEqual(c2.state, "cancelled")

    def test_consultation_direct_state_write_forbidden(self):
        c = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Contrôle"}
        )
        with self.assertRaises(AccessError):
            c.write({"state": "done"})

    def test_consultation_delete_draft_allowed(self):
        c = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Contrôle"}
        )
        c.unlink()
        self.assertFalse(self.env["gest_agri.veterinary.consultation"].browse(c.id).exists())

    def test_consultation_delete_done_forbidden(self):
        c = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Contrôle"}
        )
        c.action_done()
        with self.assertRaises(UserError):
            c.unlink()

    # ------------------------------------------------------------------
    # Historique et échéances sanitaires
    # ------------------------------------------------------------------
    def test_animal_health_history_counts(self):
        self.env["gest_agri.animal.health"].create(
            {"animal_id": self.animal.id, "observation_date": date(2026, 7, 1)}
        )
        self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Contrôle"}
        )
        self.env["gest_agri.vaccination"].create(
            {"animal_id": self.animal.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
        )
        self.env["gest_agri.animal.treatment"].create(
            {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 1)}
        )
        self.assertEqual(self.animal.health_record_count, 1)
        self.assertEqual(self.animal.consultation_count, 1)
        self.assertEqual(self.animal.vaccination_count, 1)
        self.assertEqual(self.animal.treatment_count, 1)

    def test_animal_next_vaccination_due_date(self):
        future = date.today() + timedelta(days=20)
        v = self.env["gest_agri.vaccination"].create(
            {
                "animal_id": self.animal.id, "vaccine_name": "V",
                "vaccination_date": date.today(), "next_due_date": future,
            }
        )
        v.action_done()
        self.assertEqual(self.animal.next_vaccination_due_date, future)
        self.assertFalse(self.animal.has_overdue_sanitary_deadline)

    def test_animal_overdue_sanitary_deadline(self):
        v = self.env["gest_agri.vaccination"].create(
            {
                "animal_id": self.animal.id, "vaccine_name": "V",
                "vaccination_date": date.today() - timedelta(days=30),
                "next_due_date": date.today() - timedelta(days=5),
            }
        )
        v.action_done()
        self.assertTrue(self.animal.has_overdue_sanitary_deadline)

    def test_animal_next_control_date(self):
        future = date.today() + timedelta(days=10)
        c = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Contrôle", "next_control_date": future}
        )
        c.action_done()
        self.assertEqual(self.animal.next_control_date, future)

    def test_draft_records_not_counted_as_deadline(self):
        self.env["gest_agri.vaccination"].create(
            {
                "animal_id": self.animal.id, "vaccine_name": "V",
                "vaccination_date": date.today() - timedelta(days=30),
                "next_due_date": date.today() - timedelta(days=5),
            }
        )
        self.assertFalse(self.animal.has_overdue_sanitary_deadline)

    def test_lot_sanitary_intervention_count(self):
        self.env["gest_agri.sanitary.intervention"].create(
            {"lot_id": self.lot.id, "intervention_type": "control", "intervention_date": date(2026, 7, 1)}
        )
        self.assertEqual(self.lot.sanitary_intervention_count, 1)

    def test_vaccination_farm_from_lot(self):
        v = self.env["gest_agri.vaccination"].create(
            {"lot_id": self.lot.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
        )
        self.assertEqual(v.farm_id, self.farm_a)

    # ------------------------------------------------------------------
    # Cloisonnement inter-exploitations (santé)
    # ------------------------------------------------------------------
    def test_consultation_isolation(self):
        c = self.env["gest_agri.veterinary.consultation"].create(
            {"animal_id": self.animal.id, "reason": "Contrôle"}
        )
        visible = self.env["gest_agri.veterinary.consultation"].with_user(self.user_a).search([])
        self.assertNotIn(c, visible)

    def test_vaccination_isolation(self):
        v = self.env["gest_agri.vaccination"].create(
            {"animal_id": self.animal.id, "vaccine_name": "V", "vaccination_date": date(2026, 7, 1)}
        )
        visible = self.env["gest_agri.vaccination"].with_user(self.user_a).search([])
        self.assertNotIn(v, visible)

    def test_treatment_isolation(self):
        t = self.env["gest_agri.animal.treatment"].create(
            {"animal_id": self.animal.id, "product_name": "P", "start_date": date(2026, 7, 1)}
        )
        visible = self.env["gest_agri.animal.treatment"].with_user(self.user_a).search([])
        self.assertNotIn(t, visible)

    def test_disease_read_allowed_for_user(self):
        visible = self.env["gest_agri.animal.disease"].with_user(self.user_a).search([])
        self.assertIn(self.disease, visible)
