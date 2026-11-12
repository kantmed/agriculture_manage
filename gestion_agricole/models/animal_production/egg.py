# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriEggProduction(models.Model):
    """Collecte d'œufs.

    La collecte est rattachée à un lot de pondeuses et à une date : aucune
    identification individuelle des poules n'est imposée. Le classement par
    catégorie est porté par des lignes ; les pertes (cassés, déclassés, sales)
    restent traçables et ne sont pas confondues avec les quantités
    commercialisables.
    """

    _name = "gest_agri.egg.production"
    _description = "Collecte d'œufs"
    _inherit = ["mail.thread"]
    _order = "collection_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    lot_id = fields.Many2one(
        "gest_agri.animal.lot", string="Lot de pondeuses", required=True, ondelete="restrict", index=True,
    )
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", related="lot_id.farm_id",
        store=True, readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", index=True)
    species_id = fields.Many2one(
        "gest_agri.livestock.species", string="Espèce", related="lot_id.species_id",
        store=True, readonly=True, index=True,
    )
    breed_id = fields.Many2one(
        "gest_agri.livestock.breed", string="Race", related="lot_id.breed_id",
        store=True, readonly=True, index=True,
    )

    collection_date = fields.Date(string="Date de collecte", required=True, default=fields.Date.today, index=True)
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    egg_count = fields.Integer(string="Nombre total d'œufs collectés", required=True, default=0)
    total_quantity = fields.Float(string="Quantité totale", digits=(16, 3))
    uom_id = fields.Many2one("uom.uom", string="Unité", ondelete="restrict")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    line_ids = fields.One2many("gest_agri.egg.production.line", "production_id", string="Classement")
    quality_ids = fields.One2many("gest_agri.egg.quality", "production_id", string="Contrôles de qualité")

    line_egg_count = fields.Integer(string="Œufs classés", compute="_compute_indicators", store=True)
    loss_egg_count = fields.Integer(string="Œufs perdus / déclassés", compute="_compute_indicators", store=True)
    quality_count = fields.Integer(string="Nb contrôles", compute="_compute_indicators", store=True)
    has_non_conformity = fields.Boolean(string="Non-conformité", compute="_compute_indicators", store=True)

    _egg_lot_date_unique = models.UniqueIndex(
        "(lot_id, collection_date) WHERE state != 'cancelled' AND lot_id IS NOT NULL",
        "Une collecte d'œufs existe déjà pour ce lot à cette date.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.egg.production")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.egg.production » est introuvable."))
                vals["name"] = ref
        return super().create(vals_list)

    @api.depends("line_ids.egg_count", "line_ids.category_id.is_loss", "quality_ids.conformity")
    def _compute_indicators(self):
        for rec in self:
            rec.line_egg_count = sum(rec.line_ids.mapped("egg_count"))
            rec.loss_egg_count = sum(rec.line_ids.filtered(lambda line: line.category_id.is_loss).mapped("egg_count"))
            rec.quality_count = len(rec.quality_ids)
            rec.has_non_conformity = any(q.conformity == "non_conforme" for q in rec.quality_ids)

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    @api.constrains("egg_count")
    def _check_egg_count(self):
        for rec in self:
            if rec.egg_count < 0:
                raise ValidationError(self.env._("Le nombre d'œufs ne peut pas être négatif."))

    @api.constrains("total_quantity")
    def _check_total_quantity(self):
        for rec in self:
            if rec.total_quantity < 0:
                raise ValidationError(self.env._("La quantité totale ne peut pas être négative."))

    @api.constrains("line_ids", "egg_count")
    def _check_lines_not_exceed(self):
        for rec in self:
            if rec.line_ids and sum(rec.line_ids.mapped("egg_count")) > rec.egg_count:
                raise ValidationError(self.env._(
                    "La somme des œufs classés dépasse le nombre total d'œufs collectés."
                ))

    @api.constrains("lot_id", "collection_date", "state")
    def _check_duplicate(self):
        for rec in self:
            if rec.state == "cancelled" or not rec.lot_id:
                continue
            duplicates = self.search([
                ("id", "!=", rec.id),
                ("state", "!=", "cancelled"),
                ("lot_id", "=", rec.lot_id.id),
                ("collection_date", "=", rec.collection_date),
            ])
            if duplicates:
                raise ValidationError(self.env._("Une collecte d'œufs existe déjà pour ce lot à cette date."))

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_egg_production_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_egg_production_state_transition=True).write({"state": target})

    def action_validate(self):
        self._check_allowed({"draft"})
        for rec in self:
            if rec.line_ids and sum(rec.line_ids.mapped("egg_count")) != rec.egg_count:
                raise UserError(self.env._(
                    "La somme des œufs classés (%(s)s) doit être égale au nombre total d'œufs collectés (%(t)s).",
                    s=sum(rec.line_ids.mapped("egg_count")), t=rec.egg_count,
                ))
        self._apply_state("validated")

    def action_cancel(self):
        self._check_allowed({"draft", "validated"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "validated": "Validée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : la collecte « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La collecte d'œufs « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()


class GestAgriEggProductionLine(models.Model):
    _name = "gest_agri.egg.production.line"
    _description = "Ligne de classement des œufs"
    _order = "sequence, id"

    production_id = fields.Many2one(
        "gest_agri.egg.production", string="Collecte", required=True, ondelete="cascade", index=True,
    )
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", related="production_id.farm_id",
        store=True, readonly=True, index=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Société", related="production_id.company_id",
        store=True, readonly=True, index=True,
    )
    category_id = fields.Many2one(
        "gest_agri.egg.category", string="Catégorie", required=True, ondelete="restrict", index=True,
    )
    egg_count = fields.Integer(string="Nombre d'œufs", required=True, default=0)
    total_weight = fields.Float(string="Poids total", digits=(16, 3))
    average_weight = fields.Float(string="Poids moyen", compute="_compute_average_weight", store=True, digits=(16, 4))
    notes = fields.Text(string="Observations")
    sequence = fields.Integer(string="Séquence", default=10)

    @api.depends("total_weight", "egg_count")
    def _compute_average_weight(self):
        for line in self:
            line.average_weight = line.total_weight / line.egg_count if line.egg_count else 0.0

    @api.constrains("egg_count")
    def _check_egg_count(self):
        for line in self:
            if line.egg_count < 0:
                raise ValidationError(self.env._("Le nombre d'œufs ne peut pas être négatif."))

    @api.constrains("egg_count", "production_id")
    def _check_total_not_exceeded(self):
        for line in self:
            production = line.production_id
            if not production:
                continue
            if sum(production.line_ids.mapped("egg_count")) > production.egg_count:
                raise ValidationError(self.env._(
                    "La somme des œufs classés dépasse le nombre total d'œufs collectés."
                ))

    @api.constrains("total_weight")
    def _check_total_weight(self):
        for line in self:
            if line.total_weight < 0:
                raise ValidationError(self.env._("Le poids total ne peut pas être négatif."))


class GestAgriEggQuality(models.Model):
    """Contrôle de qualité des œufs.

    Un œuf dont les données de contrôle sont insuffisantes n'est jamais
    déclaré conforme : le résultat par défaut reste « En attente ».
    """

    _name = "gest_agri.egg.quality"
    _description = "Contrôle de qualité des œufs"
    _inherit = ["mail.thread"]
    _order = "control_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    production_id = fields.Many2one(
        "gest_agri.egg.production", string="Collecte associée", required=True,
        ondelete="cascade", index=True,
    )
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", related="production_id.farm_id",
        store=True, readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True, index=True,
    )
    control_date = fields.Date(string="Date du contrôle", required=True, default=fields.Date.today, index=True)
    responsible_id = fields.Many2one("res.users", string="Responsable du contrôle", ondelete="set null")

    conformity = fields.Selection(
        selection=[
            ("pending", "En attente"), ("to_control", "À contrôler"),
            ("conforme", "Conforme"), ("non_conforme", "Non conforme"),
        ],
        string="Conformité", required=True, default="pending", index=True,
    )
    cleanliness = fields.Selection(
        selection=[("clean", "Propre"), ("dirty", "Sale")],
        string="Propreté", default="clean",
    )
    shell_integrity = fields.Selection(
        selection=[("intact", "Coquille intacte"), ("cracked", "Fêlée"), ("broken", "Cassée")],
        string="Intégrité de la coquille", default="intact",
    )
    weight = fields.Float(string="Poids", digits=(16, 3))
    freshness_days = fields.Integer(string="Fraîcheur (jours depuis la ponte)")
    result = fields.Text(string="Résultat du contrôle")
    notes = fields.Text(string="Observations")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.egg.quality")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.egg.quality » est introuvable."))
                vals["name"] = ref
        return super().create(vals_list)

    @api.constrains("weight")
    def _check_weight(self):
        for rec in self:
            if rec.weight < 0:
                raise ValidationError(self.env._("Le poids ne peut pas être négatif."))

    @api.constrains("freshness_days")
    def _check_freshness(self):
        for rec in self:
            if rec.freshness_days < 0:
                raise ValidationError(self.env._("La fraîcheur ne peut pas être négative."))
