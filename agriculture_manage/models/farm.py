from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AgricultureFarm(models.Model):
    _name = "agriculture.farm"
    _description = "Exploitation agricole"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(
        string="Nom de l'exploitation",
        required=True,
        tracking=True,
    )

    code = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default="Nouveau",
        tracking=True,
    )

    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        string="Société",
        required=True,
        default=lambda self: self.env.company,
    )

    manager_id = fields.Many2one(
        "res.users",
        string="Responsable",
        tracking=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
    )

    phone = fields.Char(string="Téléphone")
    email = fields.Char(string="E-mail")

    street = fields.Char(string="Adresse")
    city = fields.Char(string="Ville")
    state_id = fields.Many2one("res.country.state", string="Wilaya")
    country_id = fields.Many2one(
        "res.country",
        string="Pays",
        default=lambda self: self.env.ref(
            "base.dz", raise_if_not_found=False
        ),
    )

    activity_type_ids = fields.Many2many(
        "agriculture.farm.activity.type",
        string="Activités agricoles",
    )

    site_ids = fields.One2many(
        "agriculture.farm.site",
        "farm_id",
        string="Sites",
    )

    plot_ids = fields.One2many(
        "agriculture.farm.plot",
        "farm_id",
        string="Parcelles",
    )

    total_area = fields.Float(
        string="Superficie totale (ha)",
        required=True,
        tracking=True,
        help="Superficie globale de l'exploitation. Le cumul des parcelles ne peut pas la dépasser.",
    )

    allocated_area = fields.Float(
        string="Superficie des parcelles (ha)",
        compute="_compute_allocated_area",
        store=True,
    )

    site_sequence = fields.Integer(
        default=0,
        copy=False,
        readonly=True,
    )
    plot_sequence = fields.Integer(
        default=0,
        copy=False,
        readonly=True,
    )

    notes = fields.Html(string="Observations")

    @api.depends("plot_ids.area_ha")
    def _compute_allocated_area(self):
        for farm in self:
            farm.allocated_area = sum(farm.plot_ids.mapped("area_ha"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("farm.farm.yearly")
                    or "Nouveau"
                )
        return super().create(vals_list)

    @api.constrains("total_area")
    def _check_total_area(self):
        for farm in self:
            if farm.total_area <= 0:
                raise ValidationError(
                    _("La superficie globale doit être supérieure à zéro.")
                )
            allocated_area = sum(farm.plot_ids.mapped("area_ha"))
            if float_compare(
                allocated_area, farm.total_area, precision_digits=2
            ) > 0:
                raise ValidationError(
                    _(
                        "La superficie globale de l'exploitation ne peut pas "
                        "être inférieure au cumul de ses parcelles "
                        "(%(allocated).2f ha)."
                    )
                    % {"allocated": allocated_area}
                )

    @api.constrains("manager_id", "company_id")
    def _check_manager_company(self):
        for farm in self:
            if (
                farm.manager_id
                and farm.company_id not in farm.manager_id.company_ids
            ):
                raise ValidationError(
                    _("Le responsable doit avoir accès à la société.")
                )