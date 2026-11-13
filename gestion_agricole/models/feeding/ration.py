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
    # Optional for database upgrades: existing company-level rations need an
    # explicit farm assignment by an agricultural administrator.
    farm_id = fields.Many2one("gest_agri.farm", string="Exploitation", ondelete="restrict", check_company=True, index=True)
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
        defaults = self.default_get(["farm_id"])
        for vals in vals_list:
            farm_id = vals.get("farm_id", defaults.get("farm_id"))
            farm = self.env["gest_agri.farm"].browse(farm_id).exists()
            if not farm:
                raise ValidationError(self.env._("Une ration doit être rattachée à une exploitation."))
            farm.check_access("write")
            vals["farm_id"] = farm.id
            if vals.get("company_id") and vals["company_id"] != farm.company_id.id:
                raise ValidationError(self.env._("La société de la ration doit correspondre à celle de l'exploitation."))
            vals["company_id"] = farm.company_id.id
            if not vals.get("reference"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.feed.ration")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.feed.ration » est introuvable."))
                vals["reference"] = ref
            if not vals.get("name"):
                vals["name"] = vals["reference"]
        return super().create(vals_list)

    def write(self, vals):
        if "farm_id" in vals or "company_id" in vals:
            vals = dict(vals)
            for ration in self:
                farm = self.env["gest_agri.farm"].browse(vals.get("farm_id", ration.farm_id.id))
                if not farm:
                    raise ValidationError(self.env._("Une ration doit être rattachée à une exploitation."))
                farm.check_access("write")
                if vals.get("company_id") and vals["company_id"] != farm.company_id.id:
                    raise ValidationError(self.env._("La société de la ration doit correspondre à celle de l'exploitation."))
                if "farm_id" in vals and "company_id" not in vals:
                    vals["company_id"] = farm.company_id.id
        return super().write(vals)

    @api.constrains("farm_id", "company_id")
    def _check_farm_company(self):
        for ration in self:
            if ration.farm_id and ration.company_id != ration.farm_id.company_id:
                raise ValidationError(self.env._("La société de la ration doit correspondre à celle de l'exploitation."))

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
    _check_company_auto = True

    ration_id = fields.Many2one(
        "gest_agri.feed.ration", string="Ration", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    company_id = fields.Many2one(
        related="ration_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    farm_id = fields.Many2one(related="ration_id.farm_id", string="Exploitation", store=True, readonly=True, index=True)
    feed_id = fields.Many2one(
        "gest_agri.feed", string="Aliment", required=True, ondelete="restrict",
        check_company=True, index=True,
    )
    quantity = fields.Float(string="Quantité", required=True, digits=(16, 3))
    uom_id = fields.Many2one("uom.uom", string="Unité", required=True, ondelete="restrict")
    frequency = fields.Selection(
        selection=[("daily", "Quotidienne"), ("weekly", "Hebdomadaire"), ("monthly", "Mensuelle")],
        string="Fréquence", default="daily",
    )
    sequence = fields.Integer(string="Séquence", default=10)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            ration = self.env["gest_agri.feed.ration"].browse(vals.get("ration_id"))
            if not ration.farm_id:
                raise ValidationError(self.env._("La ration doit être rattachée à une exploitation avant modification."))
            ration.check_access("write")
            feed = self.env["gest_agri.feed"].browse(vals.get("feed_id"))
            feed.check_access("read")
        return super().create(vals_list)

    def write(self, vals):
        if any(not ration.farm_id for ration in self.mapped("ration_id")):
            raise ValidationError(self.env._("La ration doit être rattachée à une exploitation avant modification."))
        ration_ids = {vals.get("ration_id")} if vals.get("ration_id") else set(self.mapped("ration_id").ids)
        feed_ids = {vals.get("feed_id")} if vals.get("feed_id") else set(self.mapped("feed_id").ids)
        self.env["gest_agri.feed.ration"].browse(list(ration_ids)).check_access("write")
        self.env["gest_agri.feed"].browse(list(feed_ids)).check_access("read")
        return super().write(vals)

    @api.constrains("feed_id", "ration_id")
    def _check_feed_species(self):
        for line in self:
            if line.feed_id.species_id and line.ration_id.species_id and line.feed_id.species_id != line.ration_id.species_id:
                raise ValidationError(
                    self.env._("L'aliment « %s » n'est pas compatible avec l'espèce de la ration.", line.feed_id.display_name)
                )

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(self.env._("La quantité doit être strictement positive."))
