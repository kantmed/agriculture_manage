from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class AgricultureFarmSite(models.Model):
    _name = "agriculture.farm.site"
    _description = "Site agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "farm_id, name"

    name = fields.Char(
        string="Nom du site",
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
    company_id = fields.Many2one(
        related="farm_id.company_id",
        store=True,
        readonly=True,
    )

    site_type = fields.Selection(
        [
            ("production", "Production"),
            ("storage", "Stockage"),
            ("livestock", "Élevage"),
            ("greenhouse", "Serres"),
            ("administration", "Administration"),
            ("mixed", "Mixte"),
            ("other", "Autre"),
        ],
        string="Type de site",
        default="production",
        required=True,
    )

    address = fields.Char(string="Adresse")
    city = fields.Char(string="Commune")
    notes = fields.Html(string="Observations")

    has_coordinates = fields.Boolean(
        string="Coordonnées GPS renseignées",
        default=False,
    )
    latitude = fields.Float(string="Latitude")
    longitude = fields.Float(string="Longitude")

    osm_url = fields.Char(
        string="Carte OpenStreetMap",
        compute="_compute_osm_url",
    )

    plot_ids = fields.One2many(
        "agriculture.farm.plot",
        "site_id",
        string="Parcelles",
    )
    infrastructure_ids = fields.One2many(
        "agriculture.farm.infrastructure",
        "site_id",
        string="Infrastructures",
    )

    plot_count = fields.Integer(
        string="Nombre de parcelles",
        compute="_compute_counts",
    )
    infrastructure_count = fields.Integer(
        string="Nombre d'infrastructures",
        compute="_compute_counts",
    )

    @api.depends("plot_ids", "infrastructure_ids")
    def _compute_counts(self):
        for site in self:
            site.plot_count = len(site.plot_ids)
            site.infrastructure_count = len(site.infrastructure_ids)

    @api.depends(
        "has_coordinates",
        "latitude",
        "longitude",
    )
    def _compute_osm_url(self):
        for site in self:
            if site.has_coordinates:
                site.osm_url = (
                    "https://www.openstreetmap.org/"
                    f"?mlat={site.latitude}&mlon={site.longitude}"
                    f"#map=16/{site.latitude}/{site.longitude}"
                )
            else:
                site.osm_url = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (
                vals.get("code", "Nouveau") == "Nouveau"
                and vals.get("farm_id")
            ):
                farm = self.env["agriculture.farm"].sudo().browse(vals["farm_id"])
                self.env.cr.execute(
                    SQL(
                        "SELECT id FROM %s WHERE id = %s FOR UPDATE",
                        SQL.identifier(farm._table),
                        farm.id,
                    )
                )
                farm.invalidate_recordset(["site_sequence"])
                site_number = farm.site_sequence + 1
                farm.write({"site_sequence": site_number})
                vals["code"] = f"{farm.code}-SIT-{site_number:02d}"
        return super().create(vals_list)

    @api.constrains("latitude", "longitude", "has_coordinates")
    def _check_coordinates(self):
        for site in self:
            if site.has_coordinates:
                if not -90 <= site.latitude <= 90:
                    raise ValidationError(_("Latitude invalide."))
                if not -180 <= site.longitude <= 180:
                    raise ValidationError(_("Longitude invalide."))