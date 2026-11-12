# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestIrrigation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.group_user = cls.env.ref("gestion_agricole.group_gest_agri_user")
        cls.group_manager = cls.env.ref("gestion_agricole.group_gest_agri_manager")
        cls.group_admin = cls.env.ref("gestion_agricole.group_gest_agri_admin")

        cls.user_a = cls._create_user("irr_user_a", [cls.base_user, cls.group_user])

        cls.farm_a = cls.env["gest_agri.farm"].create(
            {"name": "Ferme irr A", "code": "IRRA", "company_id": cls.company.id, "total_area": 50.0}
        )
        cls.farm_b = cls.env["gest_agri.farm"].create(
            {"name": "Ferme irr B", "code": "IRRB", "company_id": cls.company.id, "total_area": 30.0}
        )
        cls.site_a = cls.env["gest_agri.site"].create({"name": "Site A", "code": "SA", "farm_id": cls.farm_a.id})
        cls.plot_a = cls.env["gest_agri.plot"].create({"name": "Parcelle A", "code": "PA", "farm_id": cls.farm_a.id, "area": 10.0})
        cls.water_source = cls.env["gest_agri.water.source"].create(
            {"name": "Source A", "code": "SRC-A", "farm_id": cls.farm_a.id, "source_type": "well"}
        )
        cls.network = cls.env["gest_agri.irrigation.network"].create(
            {"name": "Réseau A", "code": "NET-A", "farm_id": cls.farm_a.id, "water_source_id": cls.water_source.id, "network_type": "drip"}
        )
        cls.sector = cls.env["gest_agri.irrigation.sector"].create(
            {"name": "Secteur A", "code": "SEC-A", "network_id": cls.network.id, "area": 5.0, "plot_ids": [(4, cls.plot_a.id)]}
        )
        cls.pump = cls.env["gest_agri.irrigation.pump"].create(
            {"name": "Pompe A", "code": "PMP-A", "network_id": cls.network.id, "power_kw": 5.0, "flow_rate_m3_h": 10.0}
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

    def _create_operation(self, **kwargs):
        vals = {
            "sector_id": self.sector.id,
            "start_datetime": datetime(2026, 7, 1, 8, 0),
            "end_datetime": datetime(2026, 7, 1, 10, 0),
            "volume_m3": 20.0,
        }
        vals.update(kwargs)
        return self.env["gest_agri.irrigation.operation"].create(vals)

    # ------------------------------------------------------------------
    # Sources d'eau
    # ------------------------------------------------------------------
    def test_water_source_creation(self):
        ws = self.env["gest_agri.water.source"].create(
            {"name": "Source B", "code": "SRC-B", "farm_id": self.farm_a.id, "source_type": "well"}
        )
        self.assertTrue(ws.id)

    # ------------------------------------------------------------------
    # Réseaux
    # ------------------------------------------------------------------
    def test_network_creation(self):
        net = self.env["gest_agri.irrigation.network"].create(
            {"name": "Net B", "code": "NET-B", "farm_id": self.farm_a.id, "network_type": "sprinkler"}
        )
        self.assertTrue(net.id)

    def test_network_water_source_coherence(self):
        other_farm = self.farm_b
        other_source = self.env["gest_agri.water.source"].create(
            {"name": "S2", "code": "S2", "farm_id": other_farm.id, "source_type": "well"}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.irrigation.network"].create(
                {"name": "N2", "code": "N2", "farm_id": self.farm_a.id, "water_source_id": other_source.id, "network_type": "drip"}
            )

    # ------------------------------------------------------------------
    # Secteurs
    # ------------------------------------------------------------------
    def test_sector_creation(self):
        sec = self.env["gest_agri.irrigation.sector"].create(
            {"name": "Sec B", "code": "SEC-B", "network_id": self.network.id, "area": 3.0}
        )
        self.assertTrue(sec.id)

    def test_sector_plot_coherence(self):
        other_plot = self.env["gest_agri.plot"].create(
            {"name": "P2", "code": "P2", "farm_id": self.farm_b.id, "area": 5.0}
        )
        with self.assertRaises(ValidationError):
            self.env["gest_agri.irrigation.sector"].create(
                {"name": "Sec X", "code": "SEC-X", "network_id": self.network.id, "area": 1.0, "plot_ids": [(4, other_plot.id)]}
            )

    def test_sector_area_positive(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.irrigation.sector"].create(
                {"name": "Sec Neg", "code": "SEC-NEG", "network_id": self.network.id, "area": -1.0}
            )

    # ------------------------------------------------------------------
    # Pompes
    # ------------------------------------------------------------------
    def test_pump_creation(self):
        pump = self.env["gest_agri.irrigation.pump"].create(
            {"name": "Pompe B", "code": "PMP-B", "network_id": self.network.id, "power_kw": 3.0}
        )
        self.assertTrue(pump.id)

    def test_pump_coherence(self):
        other_net = self.env["gest_agri.irrigation.network"].create(
            {"name": "Net2", "code": "NET2", "farm_id": self.farm_b.id, "network_type": "drip"}
        )
        # network farm mismatch is handled by network creation; pump requires network
        pump = self.env["gest_agri.irrigation.pump"].create(
            {"name": "P2", "code": "P2", "network_id": other_net.id}
        )
        self.assertEqual(pump.farm_id, other_net.farm_id)

    def test_pump_positive_values(self):
        with self.assertRaises(ValidationError):
            self.env["gest_agri.irrigation.pump"].create(
                {"name": "Pneg", "code": "PNEG", "network_id": self.network.id, "power_kw": -1.0}
            )

    # ------------------------------------------------------------------
    # Opérations d'irrigation
    # ------------------------------------------------------------------
    def test_operation_creation(self):
        op = self._create_operation()
        self.assertTrue(op.id)
        self.assertTrue(op.name.startswith("IRR/"))
        self.assertAlmostEqual(op.duration_hours, 2.0)
        self.assertAlmostEqual(op.flow_rate_m3_h, 10.0)

    def test_operation_requires_sector(self):
        with self.assertRaises(Exception):
            self.env["gest_agri.irrigation.operation"].create(
                {"start_datetime": datetime(2026, 7, 1, 8, 0), "end_datetime": datetime(2026, 7, 1, 10, 0)}
            )

    def test_operation_dates(self):
        with self.assertRaises(ValidationError):
            self._create_operation(
                start_datetime=datetime(2026, 7, 1, 10, 0),
                end_datetime=datetime(2026, 7, 1, 8, 0),
            )

    def test_operation_volume_positive(self):
        with self.assertRaises(ValidationError):
            self._create_operation(volume_m3=-5.0)

    def test_operation_pump_network_coherence(self):
        other_net = self.env["gest_agri.irrigation.network"].create(
            {"name": "Net2", "code": "NET2", "farm_id": self.farm_a.id, "network_type": "drip"}
        )
        other_sector = self.env["gest_agri.irrigation.sector"].create(
            {"name": "Sec2", "code": "SEC2", "network_id": other_net.id, "area": 2.0}
        )
        with self.assertRaises(ValidationError):
            self._create_operation(sector_id=other_sector.id, pump_id=self.pump.id)

    def test_operation_overlap_rejected(self):
        self._create_operation()
        with self.assertRaises(ValidationError):
            self._create_operation(
                start_datetime=datetime(2026, 7, 1, 9, 0),
                end_datetime=datetime(2026, 7, 1, 11, 0),
            )

    def test_operation_workflow(self):
        op = self._create_operation()
        op.action_done()
        self.assertEqual(op.state, "done")
        op2 = self._create_operation(
            start_datetime=datetime(2026, 7, 2, 8, 0),
            end_datetime=datetime(2026, 7, 2, 10, 0),
        )
        op2.action_cancel()
        self.assertEqual(op2.state, "cancelled")

    def test_operation_direct_state_write_forbidden(self):
        op = self._create_operation()
        with self.assertRaises(AccessError):
            op.write({"state": "done"})

    def test_operation_delete_draft_allowed(self):
        op = self._create_operation()
        op.unlink()
        self.assertFalse(self.env["gest_agri.irrigation.operation"].browse(op.id).exists())

    def test_operation_delete_validated_forbidden(self):
        op = self._create_operation()
        op.action_done()
        with self.assertRaises(UserError):
            op.unlink()

    def test_operation_cycle_coherence(self):
        other_farm = self.farm_b
        other_plot = self.env["gest_agri.plot"].create(
            {"name": "P2", "code": "P2", "farm_id": other_farm.id, "area": 5.0}
        )
        other_cycle = self.env["gest_agri.crop.cycle"].create(
            {"plot_id": other_plot.id, "crop_type_id": self.env["gest_agri.crop.type"].create({"name": "Blé2", "code": "BLE2", "company_id": self.company.id}).id, "date_start": date(2026, 2, 1)}
        )
        with self.assertRaises(ValidationError):
            self._create_operation(cycle_id=other_cycle.id)

    def test_sector_operation_count(self):
        self._create_operation()
        self.sector.invalidate_recordset()
        self.assertEqual(self.sector.operation_count, 1)

    def test_parse_and_install(self):
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "gestion_agricole")]))

    # ------------------------------------------------------------------
    # Sécurité
    # ------------------------------------------------------------------
    def test_security_isolation(self):
        other_farm = self.farm_b
        other_source = self.env["gest_agri.water.source"].create(
            {"name": "S2", "code": "S2", "farm_id": other_farm.id, "source_type": "well"}
        )
        other_net = self.env["gest_agri.irrigation.network"].create(
            {"name": "N2", "code": "N2", "farm_id": other_farm.id, "network_type": "drip"}
        )
        other_sector = self.env["gest_agri.irrigation.sector"].create(
            {"name": "Sec2", "code": "SEC2", "network_id": other_net.id, "area": 2.0}
        )
        other_op = self.env["gest_agri.irrigation.operation"].create(
            {"sector_id": other_sector.id, "start_datetime": datetime(2026, 7, 1, 8, 0), "end_datetime": datetime(2026, 7, 1, 10, 0)}
        )
        visible = self.env["gest_agri.irrigation.operation"].with_user(self.user_a).search([])
        self.assertNotIn(other_op, visible)
