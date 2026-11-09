from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AgricultureFarmInfrastructure(models.Model):
    _name = "agriculture.farm.infrastructure"
    _description = "Infrastructure agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "farm_id, name"

    name = fields.Char(
        string="Nom de l'infrastructure",
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default="Nouveau",
    )
    active = fields.Boolean(default=True)

    farm_id = fields.Many2one(
        "agriculture.farm",
        string="Exploitation",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    site_id = fields.Many2one(
        "agriculture.farm.site",
        string="Site",
        domain="[('farm_id', '=', farm_id)]",
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        related="farm_id.company_id",
        store=True,
        readonly=True,
    )

    infrastructure_type = fields.Selection(
        [
            ("warehouse", "Entrepôt"),
            ("greenhouse", "Serre"),
            ("well", "Puits"),
            ("reservoir", "Réservoir"),
            ("pump_station", "Station de pompage"),
            ("livestock_building", "Bâtiment d'élevage"),
            ("workshop", "Atelier"),
            ("office", "Bureau"),
            ("irrigation_network", "Réseau d'irrigation"),
            ("other", "Autre"),
        ],
        string="Type d'infrastructure",
        required=True,
        default="other",
        tracking=True,
    )

    construction_date = fields.Date(
        string="Date de construction",
        tracking=True,
    )
    responsible_id = fields.Many2one(
        "res.users",
        string="Responsable",
        tracking=True,
        domain=[("share", "=", False)],
    )
    latitude = fields.Float(
        string="Latitude",
        digits=(10, 7),
        help="Coordonnée GPS en degrés décimaux, entre -90 et 90.",
    )
    longitude = fields.Float(
        string="Longitude",
        digits=(10, 7),
        help="Coordonnée GPS en degrés décimaux, entre -180 et 180.",
    )
    last_maintenance_date = fields.Date(
        string="Dernière maintenance",
        tracking=True,
    )
    next_maintenance_date = fields.Date(
        string="Prochaine maintenance",
        tracking=True,
    )
    maintenance_due = fields.Boolean(
        string="Maintenance à effectuer",
        compute="_compute_maintenance_due",
        search="_search_maintenance_due",
        help="Indique si la prochaine date de maintenance est atteinte ou dépassée.",
    )
    maintenance_notes = fields.Text(string="Notes de maintenance")
    area = fields.Float(
        string="Surface (m²)",
    )
    capacity = fields.Float(
        string="Capacité",
    )
    capacity_unit = fields.Char(
        string="Unité de capacité",
        help="Exemple : m³, tonnes, têtes.",
    )

    condition = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Bon"),
            ("average", "Moyen"),
            ("poor", "Mauvais"),
            ("out_of_service", "Hors service"),
        ],
        string="État",
        default="good",
        tracking=True,
    )

    description = fields.Html(string="Description")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code(
                        "farm.infrastructure"
                    )
                    or "Nouveau"
                )
        return super().create(vals_list)

    @api.constrains("site_id", "farm_id")
    def _check_site_farm(self):
        for infrastructure in self:
            if (
                infrastructure.site_id
                and infrastructure.site_id.farm_id
                != infrastructure.farm_id
            ):
                raise ValidationError(
                    _("Le site doit appartenir à la même exploitation.")
                )

    @api.depends("next_maintenance_date", "condition")
    def _compute_maintenance_due(self):
        today = fields.Date.context_today(self)
        for infrastructure in self:
            infrastructure.maintenance_due = bool(
                infrastructure.next_maintenance_date
                and infrastructure.next_maintenance_date <= today
                and infrastructure.condition != "out_of_service"
            )

    @api.model
    def _search_maintenance_due(self, operator, value):
        if operator not in ("=", "!="):
            raise NotImplementedError("Opérateur non pris en charge pour maintenance_due")
        today = fields.Date.context_today(self)
        due_domain = [
            ("next_maintenance_date", "<=", today),
            ("condition", "!=", "out_of_service"),
        ]
        # Odoo 20 no longer exposes the legacy odoo.osv.expression import.
        # This prefix domain is the equivalent OR of the three conditions.
        not_due_domain = [
            "|", "|",
            ("next_maintenance_date", "=", False),
            ("next_maintenance_date", ">", today),
            ("condition", "=", "out_of_service"),
        ]
        is_due = bool(value) if operator == "=" else not bool(value)
        return due_domain if is_due else not_due_domain

    @api.constrains("latitude", "longitude")
    def _check_gps_coordinates(self):
        for infrastructure in self:
            if infrastructure.latitude and not -90 <= infrastructure.latitude <= 90:
                raise ValidationError(_("La latitude doit être comprise entre -90 et 90."))
            if infrastructure.longitude and not -180 <= infrastructure.longitude <= 180:
                raise ValidationError(_("La longitude doit être comprise entre -180 et 180."))

    @api.constrains("last_maintenance_date", "next_maintenance_date")
    def _check_maintenance_dates(self):
        for infrastructure in self:
            if (
                infrastructure.last_maintenance_date
                and infrastructure.next_maintenance_date
                and infrastructure.next_maintenance_date < infrastructure.last_maintenance_date
            ):
                raise ValidationError(
                    _("La prochaine maintenance ne peut pas précéder la dernière maintenance.")
                )

    @api.constrains("area", "capacity")
    def _check_measurements(self):
        for infrastructure in self:
            if infrastructure.area < 0 or infrastructure.capacity < 0:
                raise ValidationError(
                    _("La surface et la capacité ne peuvent pas être négatives.")
                )