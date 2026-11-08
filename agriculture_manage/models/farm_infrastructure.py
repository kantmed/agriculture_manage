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
    )
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

    @api.constrains("area", "capacity")
    def _check_measurements(self):
        for infrastructure in self:
            if infrastructure.area < 0 or infrastructure.capacity < 0:
                raise ValidationError(
                    _("La surface et la capacité ne peuvent pas être négatives.")
                )