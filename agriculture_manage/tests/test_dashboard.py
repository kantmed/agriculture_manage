from odoo.tests.common import TransactionCase


class TestAgricultureFarmDashboard(TransactionCase):
    def test_dashboard_action_is_available_to_farm_user(self):
        company = self.env.company
        farm_user_group = self.env.ref("agriculture_manage.group_farm_user")
        user = self.env["res.users"].create(
            {
                "name": "Dashboard user",
                "login": "agriculture_dashboard_user",
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "group_ids": [(6, 0, [farm_user_group.id])],
            }
        )
        server_action = self.env.ref(
            "agriculture_manage.action_open_farm_dashboard"
        )

        action = server_action.with_user(user).with_context(
            allowed_company_ids=[company.id]
        ).run()

        self.assertEqual(action["res_model"], "agriculture.farm.dashboard")
        self.assertTrue(action["res_id"])

    def test_kpis_are_limited_to_active_company_records(self):
        company = self.env["res.company"].create({"name": "Dashboard company"})
        other_company = self.env["res.company"].create(
            {"name": "Other dashboard company"}
        )
        allowed_company_ids = self.env.user.company_ids.ids + [
            company.id,
            other_company.id,
        ]
        scoped_env = self.env["agriculture.farm"].with_context(
            allowed_company_ids=allowed_company_ids,
        ).with_company(company).env

        farm = scoped_env["agriculture.farm"].create(
            {
                "name": "Active farm",
                "company_id": company.id,
                "total_area": 4,
            }
        )
        scoped_env["agriculture.farm.site"].create(
            {"name": "Active site", "farm_id": farm.id}
        )
        scoped_env["agriculture.farm.plot"].create(
            {
                "name": "Cultivated plot",
                "farm_id": farm.id,
                "area": 3,
                "area_unit": "ha",
                "state": "cultivated",
            }
        )
        scoped_env["agriculture.farm.plot"].create(
            {
                "name": "Available plot",
                "farm_id": farm.id,
                "area": 2,
                "area_unit": "are",
                "state": "available",
            }
        )
        scoped_env["agriculture.farm.infrastructure"].create(
            {"name": "Active infrastructure", "farm_id": farm.id}
        )

        other_farm = scoped_env["agriculture.farm"].create(
            {
                "name": "Other company farm",
                "company_id": other_company.id,
                "total_area": 10,
            }
        )
        scoped_env["agriculture.farm.plot"].create(
            {
                "name": "Other company plot",
                "farm_id": other_farm.id,
                "area": 10,
                "area_unit": "ha",
            }
        )
        archived_farm = scoped_env["agriculture.farm"].create(
            {
                "name": "Archived farm",
                "company_id": company.id,
                "active": False,
                "total_area": 5,
            }
        )
        scoped_env["agriculture.farm.plot"].create(
            {
                "name": "Archived farm plot",
                "farm_id": archived_farm.id,
                "area": 5,
                "area_unit": "ha",
            }
        )

        dashboard = scoped_env["agriculture.farm.dashboard"].create({})
        kpis = dashboard.read(
            [
                "company_name",
                "farm_count",
                "site_count",
                "plot_count",
                "total_area",
                "allocated_area",
                "unallocated_area",
                "cultivated_area",
                "available_area",
                "infrastructure_count",
            ]
        )[0]

        self.assertEqual(kpis["company_name"], company.display_name)
        self.assertEqual(kpis["farm_count"], 1)
        self.assertEqual(kpis["site_count"], 1)
        self.assertEqual(kpis["plot_count"], 2)
        self.assertEqual(kpis["total_area"], 4.0)
        self.assertEqual(kpis["allocated_area"], 3.02)
        self.assertAlmostEqual(kpis["unallocated_area"], 0.98)
        self.assertEqual(kpis["cultivated_area"], 3.0)
        self.assertEqual(kpis["available_area"], 0.02)
        self.assertEqual(kpis["infrastructure_count"], 1)

        plots_action = dashboard.action_open_plots()
        self.assertIn(("farm_id.company_id", "=", company.id), plots_action["domain"])
