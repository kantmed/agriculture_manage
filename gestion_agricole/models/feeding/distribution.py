# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriFeedDistribution(models.Model):
    _name = "gest_agri.feed.distribution"
    _description = "Distribution alimentaire"
    _inherit = ["mail.thread"]
    _order = "distribution_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    # ------------------------------------------------------------------
    # Rattachement
    # ------------------------------------------------------------------
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", required=True, ondelete="cascade",
        check_company=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", check_company=True, index=True)
    animal_id = fields.Many2one("gest_agri.animal", string="Animal", ondelete="set null", index=True)
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot", ondelete="set null", index=True)
    ration_id = fields.Many2one("gest_agri.feed.ration", string="Ration", ondelete="set null", index=True)

    # ------------------------------------------------------------------
    # Distribution
    # ------------------------------------------------------------------
    distribution_date = fields.Date(string="Date de distribution", required=True, index=True)
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    notes = fields.Text(string="Observations")

    # ------------------------------------------------------------------
    # Lignes
    # ------------------------------------------------------------------
    line_ids = fields.One2many("gest_agri.feed.distribution.line", "distribution_id", string="Aliments distribués")

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("done", "Terminée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------
    total_quantity = fields.Float(string="Quantité totale", compute="_compute_total_quantity", digits=(16, 3))

    # ------------------------------------------------------------------
    # Création
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.feed.distribution")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.feed.distribution » est introuvable."))
                vals["name"] = ref
            # animal ou lot
            if not vals.get("animal_id") and not vals.get("lot_id"):
                raise ValidationError(self.env._("Une distribution doit concerner un animal ou un lot."))
            if vals.get("animal_id") and vals.get("lot_id"):
                raise ValidationError(self.env._("Une distribution ne peut concerner à la fois un animal et un lot."))
            self._check_coherence(vals)
        return super().create(vals_list)

    @api.model
    def _check_coherence(self, vals):
        farm_id = vals.get("farm_id")
        if vals.get("animal_id") and farm_id:
            animal = self.env["gest_agri.animal"].browse(vals["animal_id"])
            if animal.farm_id.id != farm_id:
                raise ValidationError(self.env._("L'animal n'appartient pas à l'exploitation."))
            if vals.get("ration_id"):
                ration = self.env["gest_agri.feed.ration"].browse(vals["ration_id"])
                if ration.species_id and animal.species_id and ration.species_id != animal.species_id:
                    raise ValidationError(self.env._("La ration n'est pas compatible avec l'espèce de l'animal."))
        if vals.get("lot_id") and farm_id:
            lot = self.env["gest_agri.animal.lot"].browse(vals["lot_id"])
            if lot.farm_id.id != farm_id:
                raise ValidationError(self.env._("Le lot n'appartient pas à l'exploitation."))
            if vals.get("ration_id"):
                ration = self.env["gest_agri.feed.ration"].browse(vals["ration_id"])
                if ration.species_id and lot.species_id and ration.species_id != lot.species_id:
                    raise ValidationError(self.env._("La ration n'est pas compatible avec l'espèce du lot."))
        if vals.get("site_id") and farm_id:
            site = self.env["gest_agri.site"].browse(vals["site_id"])
            if site.farm_id.id != farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    # ------------------------------------------------------------------
    # Calculs
    # ------------------------------------------------------------------
    @api.depends("line_ids", "line_ids.quantity")
    def _compute_total_quantity(self):
        for dist in self:
            dist.total_quantity = sum(l.quantity for l in dist.line_ids)

    # ------------------------------------------------------------------
    # Write / workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        protected = {"farm_id", "animal_id", "lot_id", "ration_id"}
        for dist in self:
            if dist.state in ("done", "cancelled") and (protected & set(vals)):
                raise UserError(self.env._("La distribution « %s » est terminée ou annulée.", dist.display_name))
            if dist.state in ("done", "cancelled") and (set(vals) - {"notes", "active"}):
                raise UserError(self.env._("La distribution « %s » est terminée ou annulée.", dist.display_name))
        if "state" in vals and not self.env.context.get("gest_agri_feed_distribution_state_transition"):
            for dist in self:
                if dist.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_feed_distribution_state_transition=True).write({"state": target})

    def action_done(self):
        self._check_allowed({"draft"})
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "done"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "done": "Terminée", "cancelled": "Annulée"}
        for dist in self:
            if dist.state not in allowed:
                raise UserError(self.env._("Transition impossible : la distribution « %(d)s » est à l'état « %(s)s ».", d=dist.display_name, s=labels.get(dist.state, dist.state)))

    def unlink(self):
        for dist in self:
            if dist.state != "draft":
                raise UserError(self.env._("La distribution « %s » ne peut être supprimée qu'en brouillon.", dist.display_name))
        return super().unlink()


class GestAgriFeedDistributionLine(models.Model):
    _name = "gest_agri.feed.distribution.line"
    _description = "Ligne de distribution alimentaire"
    _order = "sequence, id"

    distribution_id = fields.Many2one("gest_agri.feed.distribution", string="Distribution", required=True, ondelete="cascade", index=True)
    feed_id = fields.Many2one("gest_agri.feed", string="Aliment", required=True, ondelete="restrict", index=True)
    quantity = fields.Float(string="Quantité", required=True, digits=(16, 3))
    uom_id = fields.Many2one("uom.uom", string="Unité", required=True, ondelete="restrict")
    sequence = fields.Integer(string="Séquence", default=10)

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(self.env._("La quantité doit être strictement positive."))
