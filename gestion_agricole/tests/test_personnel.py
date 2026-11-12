# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestPersonnel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")

        cls.user_a = cls._create_user("per_user_a", [cls.base_user, cls.group_user])
        cls.manager = cls._create_user("per_manager", [cls.base_user, cls.group_manager])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme personnel A", "code": "PERA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme personnel B", "code": "PERB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create(
            {"name": "Site A", "code": "SA", "farm_id": cls.farm_a.id}
        )
        cls.plot_a = cls.env["gest_agri.plot"].create(
            {"name": "Parcelle A", "code": "PA", "farm_id": cls.farm_a.id, "area": 10.0}
        )
        cls.cycle = cls.env["gest_agri.crop.cycle"].create(
            {"plot_id": cls.plot_a.id, "crop_type_id": cls.env["gest_agri.crop.type"].create({"name": "Blé", "code": "BLE", "company_id": cls.company.id}).id, "date_start": date(2026, 2, 1), "date_end_planned": date(2026, 8, 30)}
        )

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

    def _create_worker(self, **kwargs):
        vals = {"name": "Dupont", "firstname": "Jean", "farm_id": self.farm_a.id}
        vals.update(kwargs)
        return self.env["gest_agri.worker"].create(vals)

    def _create_team(self, **kwargs):
        vals = {"name": "Équipe A", "farm_id": self.farm_a.id}
        vals.update(kwargs)
        return self.env["gest_agri.team"].create(vals)

    def _create_assignment(self, **kwargs):
        vals = {
            "name": "Affectation test",
            "farm_id": self.farm_a.id,
            "worker_id": self.worker.id if hasattr(self, "worker") else None,
        }
        vals.update(kwargs)
        if not vals.get("worker_id") and not vals.get("team_id"):
            w = self._create_worker()
            vals["worker_id"] = w.id
        return self.env["gest_agri.work.assignment"].create(vals)

    def _create_time(self, assignment=None, worker=None, **kwargs):
        if assignment is None:
            if not hasattr(self, "_assignment"):
                self._assignment = self._create_assignment()
            assignment = self._assignment
        if worker is None:
            worker = assignment.worker_id
        vals = {
            "assignment_id": assignment.id,
            "worker_id": worker.id,
            "work_date": date(2026, 7, 1),
            "start_time": 8.0,
            "end_time": 12.0,
        }
        vals.update(kwargs)
        return self.env["gest_agri.work.time"].create(vals)

    # ------------------------------------------------------------------
    # Travailleurs
    # ------------------------------------------------------------------
    def test_worker_creation(self):
        w = self._create_worker()
        self.assertTrue(w.id)
        self.assertTrue(w.reference.startswith("TRV/"))

    def test_worker_farm_required(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.worker"].create({"name": "Sans ferme"})

    def test_worker_full_name(self):
        w = self._create_worker(firstname="Jean", name="Dupont")
        self.assertEqual(w.full_name, "Jean Dupont")

    def test_worker_state_transitions(self):
        w = self._create_worker()
        w.action_activate()
        self.assertEqual(w.state, "active")
        w.action_suspend()
        self.assertEqual(w.state, "suspended")
        w.action_exit()
        self.assertEqual(w.state, "exited")
        w.action_reset_draft()
        self.assertEqual(w.state, "draft")

    def test_worker_direct_state_write_forbidden(self):
        w = self._create_worker()
        with self.assertRaises(AccessError):
            w.write({"state": "active"})

    def test_worker_archivable(self):
        w = self._create_worker()
        w.write({"active": False})
        self.assertFalse(w.active)

    def test_worker_assignment_count(self):
        w = self._create_worker()
        self.env["gest_agri.work.assignment"].create(
            {"name": "A1", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        w.invalidate_recordset()
        self.assertEqual(w.assignment_count, 1)

    # ------------------------------------------------------------------
    # Équipes
    # ------------------------------------------------------------------
    def test_team_creation(self):
        t = self._create_team()
        self.assertTrue(t.id)
        self.assertTrue(t.reference.startswith("EQU/"))

    def test_team_member_coherence(self):
        w = self._create_worker()
        other_farm = self.farm_b
        t = self._create_team(farm_id=other_farm.id)
        with self.assertRaises(ValidationError):
            t.write({"member_ids": [(4, w.id)]})

    def test_team_leader_coherence(self):
        w = self._create_worker()
        other_farm = self.farm_b
        t = self._create_team(farm_id=other_farm.id)
        with self.assertRaises(ValidationError):
            t.write({"leader_id": w.id})

    def test_team_member_count(self):
        w = self._create_worker()
        t = self._create_team(member_ids=[(4, w.id)])
        self.assertEqual(t.member_count, 1)

    # ------------------------------------------------------------------
    # Affectations
    # ------------------------------------------------------------------
    def test_assignment_creation(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "Aff1", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        self.assertTrue(a.id)
        self.assertTrue(a.reference.startswith("AFF/"))

    def test_assignment_requires_worker_or_team(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.work.assignment"].create(
                {"name": "Sans", "farm_id": self.farm_a.id}
            )

    def test_assignment_worker_or_team_coherence(self):
        w = self._create_worker()
        other_farm = self.farm_b
        with self.assertRaises(ValidationError):
            self.env["gest_agri.work.assignment"].create(
                {"name": "X", "farm_id": other_farm.id, "worker_id": w.id}
            )

    def test_assignment_plot_coherence(self):
        w = self._create_worker()
        other_plot = self.env["gest_agri.plot"].create(
            {"name": "P2", "code": "P2", "farm_id": self.farm_b.id, "area": 5.0}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.work.assignment"].create(
                {"name": "X", "farm_id": self.farm_a.id, "worker_id": w.id, "plot_id": other_plot.id}
            )

    def test_assignment_cycle_coherence(self):
        w = self._create_worker()
        other_plot = self.env["gest_agri.plot"].create(
            {"name": "P3", "code": "P3", "farm_id": self.farm_b.id, "area": 5.0}
        )
        other_cycle = self.env["gest_agri.crop.cycle"].create(
            {"plot_id": other_plot.id, "crop_type_id": self.cycle.crop_type_id.id, "date_start": date(2026, 2, 1)}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.work.assignment"].create(
                {"name": "X", "farm_id": self.farm_a.id, "worker_id": w.id, "cycle_id": other_cycle.id}
            )

    def test_assignment_workflow(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        a.action_plan()
        self.assertEqual(a.state, "planned")
        a.action_start()
        self.assertEqual(a.state, "in_progress")
        a.action_done()
        self.assertEqual(a.state, "done")

    def test_assignment_cancel(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        a.action_cancel()
        self.assertEqual(a.state, "cancelled")

    def test_assignment_direct_state_write_forbidden(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        with self.assertRaises(AccessError):
            a.write({"state": "planned"})

    def test_assignment_planned_duration(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {
                "name": "A",
                "farm_id": self.farm_a.id,
                "worker_id": w.id,
                "planned_start": datetime(2026, 7, 1, 8, 0),
                "planned_end": datetime(2026, 7, 1, 12, 0),
            }
        )
        self.assertAlmostEqual(a.planned_duration, 4.0)

    def test_assignment_time_count(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 10.0}
        )
        a.invalidate_recordset()
        self.assertEqual(a.time_count, 1)

    # ------------------------------------------------------------------
    # Temps de travail
    # ------------------------------------------------------------------
    def test_time_creation(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        t = self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
        )
        self.assertTrue(t.id)
        self.assertTrue(t.name.startswith("TEM/"))
        self.assertAlmostEqual(t.duration, 4.0)
        self.assertAlmostEqual(t.net_duration, 4.0)

    def test_time_net_duration_with_break(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        t = self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0, "break_duration": 1.0}
        )
        self.assertAlmostEqual(t.net_duration, 3.0)

    def test_time_invalid_duration(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.work.time"].create(
                {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 12.0, "end_time": 8.0}
            )

    def test_time_overlap_rejected(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.work.time"].create(
                {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 10.0, "end_time": 14.0}
            )

    def test_time_worker_assignment_coherence(self):
        w = self._create_worker()
        w2 = self._create_worker(name="Martin", farm_id=self.farm_b.id)
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.work.time"].create(
                {"assignment_id": a.id, "worker_id": w2.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
            )

    def test_time_cancelled_assignment_rejected(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        a.action_cancel()
        with self.assertRaises(ValidationError):
            self.env["gest_agri.work.time"].create(
                {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
            )

    def test_time_validate_transition(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        t = self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
        )
        t.action_validate()
        self.assertEqual(t.state, "validated")
        # direct write forbidden
        with self.assertRaises(UserError):
            t.write({"start_time": 9.0})

    def test_time_cancel_transition(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        t = self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
        )
        t.action_cancel()
        self.assertEqual(t.state, "cancelled")

    def test_time_delete_draft_allowed(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        t = self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
        )
        t.unlink()
        self.assertFalse(self.env["gest_agri.work.time"].browse(t.id).exists())

    def test_time_delete_validated_forbidden(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        t = self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
        )
        t.action_validate()
        with self.assertRaises(UserError):
            t.unlink()

    def test_worker_total_hours(self):
        w = self._create_worker()
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id}
        )
        t = self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
        )
        t.action_validate()
        w.invalidate_recordset()
        self.assertAlmostEqual(w.total_hours, 4.0)

    def test_team_total_hours(self):
        w = self._create_worker()
        t = self._create_team(member_ids=[(4, w.id)])
        a = self.env["gest_agri.work.assignment"].create(
            {"name": "A", "farm_id": self.farm_a.id, "worker_id": w.id, "team_id": t.id}
        )
        tm = self.env["gest_agri.work.time"].create(
            {"assignment_id": a.id, "worker_id": w.id, "work_date": date(2026, 7, 1), "start_time": 8.0, "end_time": 12.0}
        )
        tm.action_validate()
        t.invalidate_recordset()
        self.assertAlmostEqual(t.total_hours, 4.0)

    def test_parse_and_install(self):
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "gestion_agricole")]))

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_worker_company_isolation(self):
        other_company = self.env["res.company"].create({"name": "Société B"})
        other_farm = self.env["gest_agri.farm"].create(
            {"name": "Ferme B", "code": "FB", "company_id": other_company.id, "total_area": 10.0}
        )
        other_worker = self.env["gest_agri.worker"].create(
            {"name": "Autre", "farm_id": other_farm.id}
        )
        visible = self.env["gest_agri.worker"].with_user(self.user_a).search([])
        self.assertNotIn(other_worker, visible)
