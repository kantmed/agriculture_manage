# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class GestAgriFeedRation(models.Model):
    _name = "gest_agri.feed.ration"
    _description = "Ration alimentaire"
    _inherit = ["mail.thread"]
    _order = "name"
    _check_company_auto = True

    name = fields.Char(string="Désignation", required=True, index=True)
    reference = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    species_id = fields.Many2one("gest_agri.livestock.species", string="Espèce", required=True, ondelete="restrict", check_company=True, index=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)
    company_id = fields.Many2one("res.company", string="Société", index=True, default=lambda self: self.env.company)

    # Lines
    line_ids = fields.One2many("gest_agri.feed.ration.line", "ration_id", string="Composition")

    # Validity
    valid_from = fields.Date(string="Valide à partir du")
    valid_to = fields.Date(string="Valide jusqu'au")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.feed.ration")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.feed.ration » est introuvable."))
                vals["reference"] = ref
            if not vals.get("name"):
                vals["name"] = vals["reference"]
        return super().create(vals_list)

    @api.constrains("valid_from", "valid_to")
    def _check_validity(self):
        for ration in self:
            if ration.valid_from and ration.valid_to and ration.valid_to < ration.valid_from:
                raise ValidationError(self.env._("La date de fin de validité doit être postérieure à la date de début."))

    @api.constrains("species_id", "line_ids")
    def _check_species_compatibility(self):
        for ration in self:
            for line in ration.line_ids:
                if line.feed_id.species_id and line.feed_id.species_id != ration.species_id:
                    raise ValidationError(
                        self.env._("L'aliment « %s » n'est pas compatible avec l'espèce de la ration.", line.feed_id.display_name)
                    )


class GestAgriFeedRationLine(models.Model):
    _name = "gest_agri.feed.ration.line"
    _description = "Ligne de ration"
    _order = "sequence, id"

    ration_id = fields.Many2one("gest_agri.feed.ration", string="Ration", required=True, ondelete="cascade", index=True)
    feed_id = fields.Many2one("gest_agri.feed", string="Aliment", required=True, ondelete="restrict", index=True)
    quantity = fields.Float(string="Quantité", required=True, digits=(16, 3))
    uom_id = fields.Many2one("uom.uom", string="Unité", required=True, ondelete="restrict")
    frequency = fields.Selection(
        selection=[("daily", "Quotidienne"), ("weekly", "Hebdomadaire"), ("monthly", "Mensuelle")],
        string="Fréquence", default="daily",
    )
    sequence = fields.Integer(string="Séquence", default=10)

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(self.env._("La quantité doit être strictement positive."))
