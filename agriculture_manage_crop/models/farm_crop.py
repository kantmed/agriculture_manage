from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import SQL


class AgricultureFarmCrop(models.Model):
    _name = "agriculture.farm.crop"
    _description = "Culture agricole"
    _order = "name"

    name = fields.Char(
        string="Culture",
        required=True,
    )
    code = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default="Nouveau",
    )
    abbreviation = fields.Char(
        string="Abréviation",
        size=16,
        copy=False,
        help="Abréviation utilisée pour générer la référence de la culture.",
    )
    crop_type_id = fields.Many2one(
        "agriculture.farm.crop.type",
        string="Type de culture",
        required=True,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        default=lambda self: self.env.company,
    )

    variety_ids = fields.One2many(
        "agriculture.farm.crop.variety",
        "crop_id",
        string="Variétés",
    )

    @api.model_create_multi
    def create(self, vals_list):
        sequence_model = self.env["ir.sequence"].sudo()
        for vals in vals_list:
            if vals.get("code", "Nouveau") == "Nouveau":
                abbreviation = (vals.get("abbreviation") or "").strip().upper()
                if (
                    not abbreviation
                    or len(abbreviation) > 16
                    or not abbreviation.isalnum()
                ):
                    raise ValidationError(
                        _(
                            "Saisissez une abréviation de 1 à 16 lettres ou "
                            "chiffres pour générer la référence."
                        )
                    )
                vals["abbreviation"] = abbreviation

                anchor_sequence = sequence_model.search(
                    [("code", "=", "farm.crop")],
                    limit=1,
                )
                if not anchor_sequence:
                    raise ValidationError(
                        _("La séquence de référence des cultures est introuvable.")
                    )
                self.env.cr.execute(
                    SQL(
                        "SELECT id FROM %s WHERE id = %s FOR UPDATE",
                        SQL.identifier(anchor_sequence._table),
                        anchor_sequence.id,
                    )
                )

                sequence_code = f"farm.crop.abbreviation.{abbreviation}"
                sequence = sequence_model.search(
                    [
                        ("code", "=", sequence_code),
                        ("company_id", "=", False),
                    ],
                    limit=1,
                )
                if not sequence:
                    sequence = sequence_model.create(
                        {
                            "name": _("Référence culture %s") % abbreviation,
                            "code": sequence_code,
                            "prefix": f"{abbreviation}-",
                            "padding": 2,
                            "company_id": False,
                        }
                    )
                vals["code"] = sequence.next_by_id()
        return super().create(vals_list)

    def write(self, vals):
        if "abbreviation" in vals:
            abbreviation = (vals["abbreviation"] or "").strip().upper()
            if abbreviation and (
                len(abbreviation) > 16 or not abbreviation.isalnum()
            ):
                raise ValidationError(
                    _("L'abréviation doit contenir au plus 16 lettres ou chiffres.")
                )
            if any(crop.abbreviation != abbreviation for crop in self):
                raise ValidationError(
                    _("L'abréviation ne peut pas être modifiée après la création.")
                )
            vals = {**vals, "abbreviation": abbreviation}
        return super().write(vals)
