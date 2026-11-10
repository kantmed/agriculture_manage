# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ._common import check_same_company


class GestAgriFarm(models.Model):
    _name = "gest_agri.farm"
    _description = "Exploitation agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"
    _check_company_auto = True

    name = fields.Char(
        string="Nom",
        required=True,
        tracking=True,
        index=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        tracking=True,
        index=True,
    )
    farm_type_id = fields.Many2one(
        "gest_agri.farm.type",
        string="Type d'exploitation",
        check_company=True,
        ondelete="restrict",
        index=True,
    )
    manager_id = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        domain=[("share", "=", False)],
        tracking=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Propriétaire / exploitant",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Compte analytique",
        check_company=True,
        ondelete="restrict",
        index=True,
        help="Compte analytique utilisé pour suivre les coûts de l'exploitation.",
    )
    total_area = fields.Float(
        string="Surface totale (ha)",
        digits=(16, 2),
        default=0.0,
        tracking=True,
        help="Surface totale déclarée de l'exploitation, en hectares.",
    )
    allocated_area = fields.Float(
        string="Surface affectée (ha)",
        digits=(16, 2),
        compute="_compute_allocated_area",
        store=True,
        compute_sudo=True,
        help="Somme des surfaces des parcelles rattachées à l'exploitation.",
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    sequence = fields.Integer(string="Séquence", default=10)

    site_ids = fields.One2many("gest_agri.site", "farm_id", string="Sites")
    plot_ids = fields.One2many("gest_agri.plot", "farm_id", string="Parcelles")
    building_ids = fields.One2many("gest_agri.building", "farm_id", string="Bâtiments")
    infrastructure_ids = fields.One2many(
        "gest_agri.infrastructure", "farm_id", string="Infrastructures"
    )
    water_source_ids = fields.One2many(
        "gest_agri.water.source", "farm_id", string="Sources d'eau"
    )
    irrigation_network_ids = fields.One2many(
        "gest_agri.irrigation.network", "farm_id", string="Réseaux d'irrigation"
    )
    irrigation_sector_ids = fields.One2many(
        "gest_agri.irrigation.sector", "farm_id", string="Secteurs d'irrigation"
    )
    irrigation_pump_ids = fields.One2many(
        "gest_agri.irrigation.pump", "farm_id", string="Pompes d'irrigation"
    )
    access_ids = fields.One2many(
        "gest_agri.farm.access", "farm_id", string="Droits d'accès"
    )

    site_count = fields.Integer(string="Sites", compute="_compute_counts")
    plot_count = fields.Integer(string="Parcelles", compute="_compute_counts")
    building_count = fields.Integer(string="Bâtiments", compute="_compute_counts")
    infrastructure_count = fields.Integer(
        string="Infrastructures", compute="_compute_counts"
    )
    water_source_count = fields.Integer(string="Sources d'eau", compute="_compute_counts")
    irrigation_network_count = fields.Integer(
        string="Réseaux d'irrigation", compute="_compute_counts"
    )
    access_count = fields.Integer(string="Droits d'accès", compute="_compute_counts")

    _code_company_unique = models.UniqueIndex(
        "(company_id, UPPER(code)) WHERE active IS TRUE",
        "Le code de l'exploitation doit être unique par société.",
    )

    @api.depends("plot_ids", "plot_ids.area", "plot_ids.active")
    def _compute_allocated_area(self):
        for farm in self:
            # Ne somme que les parcelles actives (non archivées)
            farm.allocated_area = sum(
                plot.area for plot in farm.plot_ids.filtered('active')
            )

    @api.depends(
        "site_ids",
        "plot_ids",
        "building_ids",
        "infrastructure_ids",
        "water_source_ids",
        "irrigation_network_ids",
        "access_ids",
    )
    def _compute_counts(self):
        for farm in self:
            farm.site_count = len(farm.site_ids)
            farm.plot_count = len(farm.plot_ids)
            farm.building_count = len(farm.building_ids)
            farm.infrastructure_count = len(farm.infrastructure_ids)
            farm.water_source_count = len(farm.water_source_ids)
            farm.irrigation_network_count = len(farm.irrigation_network_ids)
            farm.access_count = len(farm.access_ids)

    @api.constrains("code", "company_id", "active")
    def _check_code_unique(self):
        # Le code d'une exploitation est unique dans sa société.
        for farm in self:
            if not farm.code or not farm.company_id:
                continue
            domain = [
                ("active", "=", True),
                ("id", "!=", farm.id),
                ("company_id", "=", farm.company_id.id),
            ]
            normalized = farm.code.strip().casefold()
            for other in self.sudo().search(domain):
                if other.code and other.code.strip().casefold() == normalized:
                    raise ValidationError(
                        self.env._(
                            "Le code « %(code)s » est déjà utilisé pour une autre "
                            "exploitation de cette société.",
                            code=farm.code,
                        )
                    )

    @api.constrains("total_area", "allocated_area")
    def _check_areas(self):
        for farm in self:
            if farm.total_area < 0:
                raise ValidationError(
                    self.env._("La surface totale ne peut pas être négative.")
                )
            if farm.allocated_area < 0:
                raise ValidationError(
                    self.env._("La surface affectée ne peut pas être négative.")
                )
            if farm.allocated_area > farm.total_area:
                raise ValidationError(
                    self.env._(
                        "La surface affectée (%(allocated)s ha) dépasse la surface "
                        "totale (%(total)s ha) de l'exploitation « %(name)s ».",
                        allocated=farm.allocated_area,
                        total=farm.total_area,
                        name=farm.name,
                    )
                )

    @api.constrains("analytic_account_id", "farm_type_id")
    def _check_company_relations(self):
        check_same_company(self, ["analytic_account_id", "farm_type_id"])

    def _invalidate_farm_access_cache(self):
        # Ciblage cible : on ne fait pas invalidate_all
        # On cible seulement les caches d acce
        self.env.transaction.invalidate_access_cache()
        self.env.transaction.invalidate_ormcache("stable")
        self.env.transaction.invalidate_ormcache("default")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("manager_id"):
                vals["manager_id"] = self.env.uid
        farms = super().create(vals_list)
        farms._invalidate_farm_access_cache()
        return farms

    def write(self, vals):
        if "farm_id" in vals:
            for record in self.filtered(
                lambda r: not r.env.user.has_group(
                    "gestion_agricole.group_gest_agri_admin"
                )
            ):
                target_farm_id = vals["farm_id"]
                target_farm = record.env["gest_agri.farm"].browse(target_farm_id)
                # Vérifier que la cible appartient à la même société
                if target_farm.company_id != record.company_id:
                    raise AccessError(
                        "Vous ne pouvez pas déplacer cet exploit vers une "
                        "exploitation d'une autre société."
                    )
                # Vérifier que le responsable a le droit sur la cible
                user = record.env.user
                if not user.has_group(
                    "gestion_agricole.group_gest_agri_manager"
                ) and user.id != target_farm.manager_id.id:
                    raise AccessError(
                        "Vous ne pouvez pas modifier l'exploitation vers une "
                        "exploitation que vous ne gérez pas."
                    )
        result = super().write(vals)
        if {"manager_id", "company_id", "active"} & set(vals):
            self._invalidate_farm_access_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env.invalidate_all()
        self.env.transaction.invalidate_access_cache()
        self.env.transaction.invalidate_ormcache("default")
        self.env.transaction.invalidate_ormcache("stable")
        return result

    def action_view_sites(self):
        self.ensure_one()
        return self._get_action("gestion_agricole.action_gest_agri_site", "site")

    def action_view_plots(self):
        self.ensure_one()
        return self._get_action("gestion_agricole.action_gest_agri_plot", "plot")

    def action_view_buildings(self):
        self.ensure_one()
        return self._get_action("gestion_agricole.action_gest_agri_building", "building")

    def action_view_infrastructures(self):
        self.ensure_one()
        return self._get_action(
            "gestion_agricole.action_gest_agri_infrastructure", "infrastructure"
        )

    def action_view_water_sources(self):
        self.ensure_one()
        return self._get_action(
            "gestion_agricole.action_gest_agri_water_source", "water_source"
        )

    def action_view_irrigation_networks(self):
        self.ensure_one()
        return self._get_action(
            "gestion_agricole.action_gest_agri_irrigation_network",
            "irrigation_network",
        )

    def action_view_accesses(self):
        self.ensure_one()
        return self._get_action(
            "gestion_agricole.action_gest_agri_farm_access", "access"
        )

    def _get_action(self, xmlid, key):
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        action["domain"] = [("farm_id", "=", self.id)]
        action["context"] = {
            "default_farm_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action
