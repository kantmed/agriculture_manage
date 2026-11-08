from odoo import api, fields, models, _


class AgricultureFarmDashboard(models.TransientModel):
    _name = "agriculture.farm.dashboard"
    _description = "Tableau de bord agricole"

    company_name = fields.Char(
        string="Société",
        compute="_compute_kpis",
    )
    site_count = fields.Integer(
        string="Sites actifs",
        compute="_compute_kpis",
    )
    plot_count = fields.Integer(
        string="Parcelles actives",
        compute="_compute_kpis",
    )
    total_area = fields.Float(
        string="Superficie totale (ha)",
        digits=(16, 2),
        compute="_compute_kpis",
    )
    cultivated_area = fields.Float(
        string="Superficie en culture (ha)",
        digits=(16, 2),
        compute="_compute_kpis",
    )
    available_area = fields.Float(
        string="Superficie disponible (ha)",
        digits=(16, 2),
        compute="_compute_kpis",
    )
    infrastructure_count = fields.Integer(
        string="Infrastructures actives",
        compute="_compute_kpis",
    )

    @api.depends_context("company")
    def _compute_kpis(self):
        company = self.env.company
        site_domain = [
            ("company_id", "=", company.id),
            ("farm_id.active", "=", True),
            ("active", "=", True),
        ]
        plot_domain = [
            ("farm_id.company_id", "=", company.id),
            ("farm_id.active", "=", True),
            ("active", "=", True),
        ]
        infrastructure_domain = [
            ("company_id", "=", company.id),
            ("farm_id.active", "=", True),
            ("active", "=", True),
        ]
        plot_groups = self.env["agriculture.farm.plot"]._read_group(
            plot_domain,
            ["state"],
            ["__count", "area_ha:sum"],
        )
        areas_by_state = {
            state: (count, area or 0.0)
            for state, count, area in plot_groups
        }

        for dashboard in self:
            dashboard.company_name = company.display_name
            dashboard.site_count = self.env[
                "agriculture.farm.site"
            ].search_count(site_domain)
            dashboard.plot_count = sum(
                count for count, _area in areas_by_state.values()
            )
            dashboard.total_area = sum(
                area for _count, area in areas_by_state.values()
            )
            dashboard.cultivated_area = areas_by_state.get(
                "cultivated", (0, 0.0)
            )[1]
            dashboard.available_area = areas_by_state.get(
                "available", (0, 0.0)
            )[1]
            dashboard.infrastructure_count = self.env[
                "agriculture.farm.infrastructure"
            ].search_count(infrastructure_domain)

    def _open_records(self, model, name, domain):
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": model,
            "view_mode": "list,form",
            "domain": domain,
        }

    @api.model
    def action_open_dashboard(self):
        dashboard = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": _("Tableau de bord"),
            "res_model": self._name,
            "views": [
                (
                    self.env.ref(
                        "agriculture_manage.view_farm_dashboard_board"
                    ).id,
                    "form",
                )
            ],
            "res_id": dashboard.id,
            "target": "current",
        }

    def action_open_sites(self):
        return self._open_records(
            "agriculture.farm.site",
            _("Sites actifs"),
            [
                ("company_id", "=", self.env.company.id),
                ("farm_id.active", "=", True),
                ("active", "=", True),
            ],
        )

    def action_open_plots(self):
        return self._open_records(
            "agriculture.farm.plot",
            _("Parcelles actives"),
            [
                ("farm_id.company_id", "=", self.env.company.id),
                ("farm_id.active", "=", True),
                ("active", "=", True),
            ],
        )

    def action_open_cultivated_plots(self):
        return self._open_records(
            "agriculture.farm.plot",
            _("Parcelles en culture"),
            [
                ("farm_id.company_id", "=", self.env.company.id),
                ("farm_id.active", "=", True),
                ("active", "=", True),
                ("state", "=", "cultivated"),
            ],
        )

    def action_open_available_plots(self):
        return self._open_records(
            "agriculture.farm.plot",
            _("Parcelles disponibles"),
            [
                ("farm_id.company_id", "=", self.env.company.id),
                ("farm_id.active", "=", True),
                ("active", "=", True),
                ("state", "=", "available"),
            ],
        )

    def action_open_infrastructures(self):
        return self._open_records(
            "agriculture.farm.infrastructure",
            _("Infrastructures actives"),
            [
                ("company_id", "=", self.env.company.id),
                ("farm_id.active", "=", True),
                ("active", "=", True),
            ],
        )

    def action_open_farms(self):
        return self._open_records(
            "agriculture.farm",
            _("Exploitations actives"),
            [
                ("company_id", "=", self.env.company.id),
                ("active", "=", True),
            ],
        )
