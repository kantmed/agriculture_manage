# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

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
    status = fields.Selection(
        selection=[
            ("draft", "Brouillon"),
            ("active", "Active"),
            ("suspended", "Suspendue"),
            ("closed", "Clôturée"),
        ],
        string="Statut",
        default="draft",
        tracking=True,
        index=True,
        help="Statut opérationnel de l'exploitation agricole.",
    )
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

    site_count = fields.Integer(string="Nb sites", compute="_compute_counts")
    plot_count = fields.Integer(string="Nb parcelles", compute="_compute_counts")
    building_count = fields.Integer(string="Nb bâtiments", compute="_compute_counts")
    infrastructure_count = fields.Integer(
        string="Nb infrastructures", compute="_compute_counts"
    )
    water_source_count = fields.Integer(string="Nb sources d'eau", compute="_compute_counts")
    irrigation_network_count = fields.Integer(
        string="Nb réseaux d'irrigation", compute="_compute_counts"
    )
    access_count = fields.Integer(string="Nb droits d'accès", compute="_compute_counts")

    _code_company_unique = models.UniqueIndex(
        "(company_id, UPPER(code)) WHERE active IS TRUE",
        "Le code de l'exploitation doit être unique par société.",
    )

    @api.depends("plot_ids", "plot_ids.area", "plot_ids.active")
    def _compute_allocated_area(self):
        # Agrégation en base : la somme des surfaces actives est calculée par
        # SQL, sans charger l'intégralité des parcelles de l'exploitation en
        # mémoire (l'ancienne implementation parcourait farm.plot_ids).
        groups = self.env["gest_agri.plot"]._read_group(
            [("farm_id", "in", self.ids), ("active", "=", True)],
            ["farm_id"],
            ["area:sum"],
        )
        totals = {group[0].id: group[1] for group in groups}
        for farm in self:
            farm.allocated_area = totals.get(farm.id, 0.0)

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
        # Comptage en base : chaque compteur est obtenu par un COUNT
        # groupé, sans charger les enregistrements enfants.
        counts = {}
        for model_name, field_name in (
            ("gest_agri.site", "site_count"),
            ("gest_agri.plot", "plot_count"),
            ("gest_agri.building", "building_count"),
            ("gest_agri.infrastructure", "infrastructure_count"),
            ("gest_agri.water.source", "water_source_count"),
            ("gest_agri.irrigation.network", "irrigation_network_count"),
            ("gest_agri.farm.access", "access_count"),
        ):
            groups = self.env[model_name]._read_group(
                [("farm_id", "in", self.ids)],
                ["farm_id"],
                ["__count"],
            )
            counts[field_name] = {group[0].id: group[1] for group in groups}
        for farm in self:
            for field_name, per_farm in counts.items():
                farm[field_name] = per_farm.get(farm.id, 0)

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
            # search_fetch ne charge que la colonne utile au lieu de
            # l'intégralité des enregistrements du périmètre.
            for other in self.sudo().search_fetch(domain, ["code"]):
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
        """Invalide les caches de sécurité dépendant des droits d'accès.

        Trois caches sont concernés :

        * le cache de valeurs des deux champs calculés de ``res.users``
          (``gest_agri_farm_ids`` / ``gest_agri_managed_farm_ids``), qui
          portent les périmètres d'accès ;
        * le cache ormcache « default », qui contient le domaine d'accès
          ``BaseModel._access_domain``. Ce domaine est évalué à partir de
          ``user.gest_agri_farm_ids`` : sans invalidation, un droit d'accès
          créé ou modifié ne serait pris en compte qu'à la fin de la
          transaction, et l'utilisateur ne verrait pas ses exploitations ;
        * le cache d'accès Odoo (décisions de lecture par enregistrement).

        L'ancien ``env.invalidate_all()`` vidait l'intégralité du cache ORM
        (donc celui de tous les modules) : il est remplacé par une invalidation
        ciblée, tout en conservant l'invalidation ormcache indispensable.
        """
        self.env["res.users"].invalidate_model(
            ["gest_agri_farm_ids", "gest_agri_managed_farm_ids"]
        )
        self.env.transaction.invalidate_ormcache("default")
        self.env.transaction.invalidate_access_cache()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("manager_id"):
                vals["manager_id"] = self.env.uid
        farms = super().create(vals_list)
        farms._invalidate_farm_access_cache()
        return farms

    def write(self, vals):
        # Note : gest_agri.farm ne possède pas de champ farm_id. Le contrôle de
        # déplacement d'exploitation vers une autre exploitation était un code
        # mort (copié de gest_agri.farm.access) : il a été supprimé.
        result = super().write(vals)
        if {"manager_id", "company_id", "active"} & set(vals):
            self._invalidate_farm_access_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self._invalidate_farm_access_cache()
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
