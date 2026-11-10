from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL, float_compare


class AgricultureFarmPlot(models.Model):
    _name = "agriculture.farm.plot"
    _description = "Parcelle agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(
        string="Nom de la parcelle",
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
    )

    area = fields.Float(
        string="Superficie",
        required=True,
        tracking=True,
    )

    area_unit = fields.Selection(
        [
            ("ha", "Hectare"),
            ("are", "Are"),
            ("m2", "Mètre carré"),
        ],
        string="Unité",
        default="ha",
        required=True,
    )

    area_ha = fields.Float(
        string="Superficie en hectares",
        compute="_compute_area_ha",
        store=True,
    )

    soil_type = fields.Selection(
        [
            ("clay", "Argileux"),
            ("sandy", "Sableux"),
            ("loam", "Limoneux"),
            ("calcareous", "Calcaire"),
            ("other", "Autre"),
        ],
        string="Type de sol",
    )

    irrigation_type_id = fields.Many2one(
        "agriculture.farm.irrigation.type",
        string="Type d'irrigation",
    )

    soil_ph = fields.Float(
        string="pH du sol",
        digits=(4, 2),
        tracking=True,
        help="Valeur mesurée du pH, comprise entre 0 et 14.",
    )

    soil_fertility = fields.Selection(
        [
            ("low", "Faible"),
            ("medium", "Moyenne"),
            ("high", "Élevée"),
            ("unknown", "Non évaluée"),
        ],
        string="Fertilité du sol",
        default="unknown",
        tracking=True,
    )

    organic_matter_percent = fields.Float(
        string="Matière organique (%)",
        digits=(5, 2),
        tracking=True,
    )

    slope_percent = fields.Float(
        string="Pente (%)",
        digits=(5, 2),
        help="Inclinaison moyenne de la parcelle.",
    )

    soil_analysis_date = fields.Date(string="Date d'analyse du sol")
    soil_notes = fields.Text(string="Observations sur le sol")
    soil_analysis_ids = fields.One2many(
        "agriculture.farm.soil.analysis", "plot_id", string="Historique des analyses de sol",
    )

    irrigation_water_source = fields.Selection(
        [
            ("well", "Puits"),
            ("borehole", "Forage"),
            ("dam", "Barrage / retenue"),
            ("network", "Réseau d'irrigation"),
            ("rain", "Eaux pluviales"),
            ("other", "Autre"),
        ],
        string="Source d'eau",
        tracking=True,
    )

    water_availability = fields.Selection(
        [
            ("reliable", "Régulière"),
            ("seasonal", "Saisonnière"),
            ("limited", "Limitée"),
            ("none", "Indisponible"),
            ("unknown", "Non renseignée"),
        ],
        string="Disponibilité de l'eau",
        default="unknown",
        tracking=True,
    )

    state = fields.Selection(
        [
            ("available", "Disponible"),
            ("cultivated", "En culture"),
            ("fallow", "En jachère"),
            ("inactive", "Inactive"),
        ],
        string="État",
        default="available",
        tracking=True,
    )

    latitude = fields.Float(string="Latitude")
    longitude = fields.Float(string="Longitude")

    osm_url = fields.Char(
        string="Carte OpenStreetMap",
        compute="_compute_osm_url",
    )

    has_coordinates = fields.Boolean(
        string="Coordonnées GPS renseignées",
        default=False,
    )

    @api.depends("area", "area_unit")
    def _compute_area_ha(self):
        for plot in self:
            if plot.area_unit == "ha":
                plot.area_ha = plot.area
            elif plot.area_unit == "are":
                plot.area_ha = plot.area / 100
            else:
                plot.area_ha = plot.area / 10000

    @api.depends("has_coordinates", "latitude", "longitude")
    def _compute_osm_url(self):
        for plot in self:
            if plot.has_coordinates:
                plot.osm_url = (
                    "https://www.openstreetmap.org/"
                    f"?mlat={plot.latitude}&mlon={plot.longitude}"
                    f"#map=16/{plot.latitude}/{plot.longitude}"
                )
            else:
                plot.osm_url = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (
                vals.get("code", "Nouveau") == "Nouveau"
                and vals.get("farm_id")
            ):
                farm = (
                    self.env["agriculture.farm"]
                    .sudo()
                    .browse(vals["farm_id"])
                )
                self.env.cr.execute(
                    SQL(
                        "SELECT id FROM %s WHERE id = %s FOR UPDATE",
                        SQL.identifier(farm._table),
                        farm.id,
                    )
                )
                farm.invalidate_recordset(["plot_sequence"])
                plot_number = farm.plot_sequence + 1
                farm.write({"plot_sequence": plot_number})
                vals["code"] = f"{farm.code}-PAR-{plot_number:03d}"
        return super().create(vals_list)

    @api.constrains("area", "area_unit", "farm_id")
    def _check_area(self):
        for plot in self:
            if plot.area <= 0:
                raise ValidationError(
                    _("La superficie doit être supérieure à zéro.")
                )
            if not plot.farm_id:
                continue
            allocated_area = sum(plot.farm_id.plot_ids.mapped("area_ha"))
            if float_compare(
                allocated_area,
                plot.farm_id.total_area,
                precision_digits=2,
            ) > 0:
                raise ValidationError(
                    _(
                        "Le cumul des superficies des parcelles "
                        "(%(allocated).2f ha) ne peut pas dépasser la "
                        "superficie globale de l'exploitation "
                        "(%(total).2f ha)."
                    )
                    % {
                        "allocated": allocated_area,
                        "total": plot.farm_id.total_area,
                    }
                )

    @api.constrains("soil_ph", "organic_matter_percent", "slope_percent")
    def _check_soil_measurements(self):
        for plot in self:
            if plot.soil_ph and not 0 <= plot.soil_ph <= 14:
                raise ValidationError(_("Le pH du sol doit être compris entre 0 et 14."))
            if not 0 <= plot.organic_matter_percent <= 100:
                raise ValidationError(_("Le taux de matière organique doit être compris entre 0 et 100 %."))
            if not 0 <= plot.slope_percent <= 100:
                raise ValidationError(_("La pente doit être comprise entre 0 et 100 %."))

    @api.constrains("latitude", "longitude", "has_coordinates")
    def _check_coordinates(self):
        for plot in self:
            if plot.has_coordinates:
                if not -90 <= plot.latitude <= 90:
                    raise ValidationError(_("Latitude invalide."))
                if not -180 <= plot.longitude <= 180:
                    raise ValidationError(_("Longitude invalide."))

    @api.constrains("site_id", "farm_id")
    def _check_site_farm(self):
        for plot in self:
            if plot.site_id and plot.site_id.farm_id != plot.farm_id:
                raise ValidationError(
                    _("Le site doit appartenir à la même exploitation.")
                )
