# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriMilkProduction(models.Model):
    """Production / collecte de lait.

    Deux modes exclusifs :
    * **individuel** : une quantité produite par un animal précis ;
    * **collectif** : une quantité totale collectée pour un lot.

    L'exclusivité (animal OU lot) garantit qu'une même production n'est jamais
    comptabilisée deux fois (individuelle et collective) dans les statistiques.
    """

    _name = "gest_agri.milk.production"
    _description = "Production laitière"
    _inherit = ["mail.thread"]
    _order = "production_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    animal_id = fields.Many2one("gest_agri.animal", string="Animal producteur", ondelete="restrict", index=True)
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot concerné", ondelete="restrict", index=True)
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", compute="_compute_farm_id",
        store=True, readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", index=True)
    species_id = fields.Many2one(
        "gest_agri.livestock.species", string="Espèce", compute="_compute_species_breed",
        store=True, readonly=True, index=True,
    )
    breed_id = fields.Many2one(
        "gest_agri.livestock.breed", string="Race", compute="_compute_species_breed",
        store=True, readonly=True, index=True,
    )
    production_mode = fields.Selection(
        selection=[("individual", "Individuel"), ("collective", "Collectif")],
        string="Mode de saisie", required=True, default="individual", index=True,
    )
    animal_count = fields.Integer(
        string="Nombre d'animaux concernés",
        help="Renseigné uniquement pour une production collective, si l'information est disponible.",
    )

    production_date = fields.Date(string="Date de production", required=True, index=True)
    milking_period = fields.Selection(
        selection=[
            ("morning", "Matin"), ("noon", "Midi"), ("evening", "Soir"),
            ("other", "Autre période"),
        ],
        string="Période de traite", required=True, default="morning", index=True,
    )
    quantity = fields.Float(string="Quantité de lait", required=True, digits=(16, 3))
    uom_id = fields.Many2one("uom.uom", string="Unité de mesure", ondelete="restrict")
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    quality_ids = fields.One2many("gest_agri.milk.quality", "production_id", string="Contrôles de qualité")
    quality_count = fields.Integer(string="Nb contrôles", compute="_compute_quality_indicators", store=True)
    has_non_conformity = fields.Boolean(string="Non-conformité", compute="_compute_quality_indicators", store=True)

    _milk_animal_unique = models.UniqueIndex(
        "(animal_id, production_date, milking_period) "
        "WHERE state != 'cancelled' AND animal_id IS NOT NULL",
        "Une production laitière existe déjà pour cet animal à cette date et période.",
    )
    _milk_lot_unique = models.UniqueIndex(
        "(lot_id, production_date, milking_period) "
        "WHERE state != 'cancelled' AND lot_id IS NOT NULL",
        "Une production laitière collective existe déjà pour ce lot à cette date et période.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.milk.production")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.milk.production » est introuvable."))
                vals["name"] = ref
        return super().create(vals_list)

    @api.depends("animal_id", "lot_id")
    def _compute_farm_id(self):
        for rec in self:
            rec.farm_id = rec.animal_id.farm_id or rec.lot_id.farm_id

    @api.depends("animal_id", "lot_id")
    def _compute_species_breed(self):
        for rec in self:
            source = rec.animal_id or rec.lot_id
            rec.species_id = source.species_id
            rec.breed_id = source.breed_id

    @api.depends("quality_ids.conformity")
    def _compute_quality_indicators(self):
        for rec in self:
            rec.quality_count = len(rec.quality_ids)
            rec.has_non_conformity = any(q.conformity == "non_conforme" for q in rec.quality_ids)

    @api.constrains("animal_id", "lot_id", "production_mode")
    def _check_target(self):
        for rec in self:
            if rec.production_mode == "individual":
                if not rec.animal_id:
                    raise ValidationError(self.env._("Une production individuelle doit concerner un animal."))
                if rec.lot_id:
                    raise ValidationError(self.env._("Une production individuelle ne peut pas concerner un lot."))
            elif rec.production_mode == "collective":
                if not rec.lot_id:
                    raise ValidationError(self.env._("Une production collective doit concerner un lot."))
                if rec.animal_id:
                    raise ValidationError(self.env._("Une production collective ne peut pas concerner un animal."))
            else:
                raise ValidationError(self.env._("Le mode de saisie est obligatoire."))

    @api.constrains("animal_id", "farm_id")
    def _check_animal(self):
        for rec in self:
            if not rec.animal_id:
                continue
            if rec.animal_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("L'animal n'appartient pas à l'exploitation."))
            if rec.animal_id.state in ("dead", "sold", "retired"):
                raise ValidationError(self.env._(
                    "L'animal « %s » n'est plus en production : aucune production laitière ne peut être enregistrée.",
                    rec.animal_id.display_name,
                ))
            if rec.animal_id.birth_date and rec.production_date and rec.production_date < rec.animal_id.birth_date:
                raise ValidationError(self.env._("La date de production ne peut pas précéder la naissance de l'animal."))

    @api.constrains("lot_id", "farm_id")
    def _check_lot(self):
        for rec in self:
            if rec.lot_id and rec.lot_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le lot n'appartient pas à l'exploitation."))

    @api.constrains("farm_id", "site_id")
    def _check_site_farm(self):
        for rec in self:
            if rec.site_id and rec.site_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("Le site n'appartient pas à l'exploitation."))

    @api.constrains("quantity")
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError(self.env._("La quantité de lait doit être strictement positive."))

    @api.constrains("animal_count")
    def _check_animal_count(self):
        for rec in self:
            if rec.animal_count < 0:
                raise ValidationError(self.env._("Le nombre d'animaux concernés ne peut pas être négatif."))

    @api.constrains("animal_id", "lot_id", "production_date", "milking_period", "state")
    def _check_duplicate(self):
        for rec in self:
            if rec.state == "cancelled":
                continue
            domain = [
                ("id", "!=", rec.id),
                ("state", "!=", "cancelled"),
                ("production_date", "=", rec.production_date),
                ("milking_period", "=", rec.milking_period),
            ]
            if rec.animal_id:
                domain.append(("animal_id", "=", rec.animal_id.id))
            elif rec.lot_id:
                domain.append(("lot_id", "=", rec.lot_id.id))
            if self.search_count(domain):
                raise ValidationError(self.env._(
                    "Une production laitière existe déjà pour cette cible à cette date et période."
                ))

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_milk_production_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_milk_production_state_transition=True).write({"state": target})

    def action_validate(self):
        self._check_allowed({"draft"})
        self._apply_state("validated")

    def action_cancel(self):
        self._check_allowed({"draft", "validated"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "validated": "Validée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : la production « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La production laitière « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()


class GestAgriMilkQuality(models.Model):
    """Contrôle de qualité du lait.

    Aucun seuil réglementaire n'est codé en dur : les valeurs sont
    enregistrées telles que mesurées et le résultat de conformité est saisi
    explicitement. Un résultat absent reste « En attente » et n'est jamais
    interprété comme conforme.
    """

    _name = "gest_agri.milk.quality"
    _description = "Contrôle de qualité du lait"
    _inherit = ["mail.thread"]
    _order = "control_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    production_id = fields.Many2one(
        "gest_agri.milk.production", string="Production associée", required=True,
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
    laboratory = fields.Char(string="Laboratoire / organisme")

    temperature = fields.Float(string="Température (°C)", digits=(16, 2))
    fat_rate = fields.Float(string="Matière grasse (%)", digits=(16, 3))
    protein_rate = fields.Float(string="Protéines (%)", digits=(16, 3))
    density = fields.Float(string="Densité", digits=(16, 4))
    ph = fields.Float(string="pH", digits=(16, 2))
    microbiological_result = fields.Text(string="Résultat microbiologique")

    conformity = fields.Selection(
        selection=[
            ("pending", "En attente"), ("to_control", "À contrôler"),
            ("conforme", "Conforme"), ("non_conforme", "Non conforme"),
        ],
        string="Conformité", required=True, default="pending", index=True,
    )
    health_record_id = fields.Many2one(
        "gest_agri.animal.health", string="Dossier sanitaire associé", ondelete="set null",
    )
    notes = fields.Text(string="Observations")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.milk.quality")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.milk.quality » est introuvable."))
                vals["name"] = ref
        return super().create(vals_list)

    @api.constrains("fat_rate", "protein_rate", "density")
    def _check_rates(self):
        for rec in self:
            if rec.fat_rate < 0 or rec.protein_rate < 0 or rec.density < 0:
                raise ValidationError(self.env._("Les taux et la densité ne peuvent pas être négatifs."))

    @api.constrains("ph")
    def _check_ph(self):
        for rec in self:
            if rec.ph and not (0.0 <= rec.ph <= 14.0):
                raise ValidationError(self.env._("Le pH doit être compris entre 0 et 14."))

    @api.constrains("health_record_id", "production_id")
    def _check_health_animal(self):
        for rec in self:
            if rec.health_record_id and rec.production_id.animal_id:
                if rec.health_record_id.animal_id != rec.production_id.animal_id:
                    raise ValidationError(self.env._(
                        "Le dossier sanitaire ne concerne pas l'animal de la production."
                    ))

    def unlink(self):
        return super().unlink()
