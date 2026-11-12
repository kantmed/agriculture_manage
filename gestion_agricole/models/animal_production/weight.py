# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimalWeight(models.Model):
    """Pesée d'un animal ou d'un lot.

    Deux modes exclusifs :
    * **individuel** : poids mesuré d'un animal (calcul du GMQ) ;
    * **collectif** : poids moyen réellement mesuré d'un lot.

    Un poids moyen n'est jamais enregistré comme poids individuel de chaque
    animal. Le GMQ n'est calculé que pour les pesées individuelles dont
    l'unité est comparable à celle de la pesée précédente.
    """

    _name = "gest_agri.animal.weight"
    _description = "Pesée d'animaux"
    _inherit = ["mail.thread"]
    _order = "weighing_datetime desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    animal_id = fields.Many2one("gest_agri.animal", string="Animal", ondelete="restrict", index=True)
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot", ondelete="restrict", index=True)
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

    weighing_mode = fields.Selection(
        selection=[("individual", "Individuel"), ("collective", "Collectif")],
        string="Mode de pesée", required=True, default="individual", index=True,
    )
    weighing_type = fields.Selection(
        selection=[
            ("birth", "Naissance"), ("growth", "Croissance"), ("periodic", "Contrôle périodique"),
            ("before_fattening", "Avant engraissement"), ("after_fattening", "Après engraissement"),
            ("before_sale", "Avant vente"), ("exceptional", "Pesée exceptionnelle"),
        ],
        string="Type de pesée", required=True, default="periodic", index=True,
    )
    weighing_datetime = fields.Datetime(string="Date et heure", required=True, default=fields.Datetime.now, index=True)
    weight = fields.Float(string="Poids mesuré", digits=(16, 3))
    average_weight = fields.Float(string="Poids moyen (lot)", digits=(16, 3))
    animal_count = fields.Integer(string="Nombre d'animaux pesés")
    uom_id = fields.Many2one("uom.uom", string="Unité de mesure", ondelete="restrict")
    equipment = fields.Char(string="Matériel de pesée")
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Croissance (GMQ)
    # ------------------------------------------------------------------
    previous_weight = fields.Float(string="Poids précédent", compute="_compute_growth", store=True, digits=(16, 3))
    weight_gain = fields.Float(string="Gain de poids", compute="_compute_growth", store=True, digits=(16, 3))
    days_interval = fields.Integer(string="Jours depuis la pesée précédente", compute="_compute_growth", store=True)
    average_daily_gain = fields.Float(string="GMQ (unité/jour)", compute="_compute_growth", store=True, digits=(16, 4))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal.weight")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal.weight » est introuvable."))
                vals["name"] = ref
            if not vals.get("animal_id") and not vals.get("lot_id"):
                raise ValidationError(self.env._("Une pesée doit concerner un animal ou un lot."))
            if vals.get("animal_id") and vals.get("lot_id"):
                raise ValidationError(self.env._("Une pesée ne peut concerner à la fois un animal et un lot."))
        return super().create(vals_list)

    @api.depends("animal_id", "lot_id")
    def _compute_farm_id(self):
        for rec in self:
            rec.farm_id = rec.animal_id.farm_id or rec.lot_id.farm_id

    @api.depends("animal_id")
    def _compute_species_breed(self):
        for rec in self:
            rec.species_id = rec.animal_id.species_id

    @api.depends("animal_id", "weighing_datetime", "weight", "weighing_mode", "uom_id", "state")
    def _compute_growth(self):
        for rec in self:
            rec.previous_weight = 0.0
            rec.weight_gain = 0.0
            rec.days_interval = 0
            rec.average_daily_gain = 0.0
            if rec.weighing_mode != "individual" or not rec.animal_id or not rec.weighing_datetime:
                continue
            if rec.weight <= 0:
                continue
            previous = self.search(
                [
                    ("id", "!=", rec.id),
                    ("animal_id", "=", rec.animal_id.id),
                    ("weighing_mode", "=", "individual"),
                    ("state", "!=", "cancelled"),
                    ("weighing_datetime", "<", rec.weighing_datetime),
                ],
                order="weighing_datetime desc, id desc",
                limit=1,
            )
            if not previous or previous.weight <= 0:
                continue
            # Ne jamais comparer des unités différentes.
            if rec.uom_id and previous.uom_id and rec.uom_id != previous.uom_id:
                continue
            interval = (rec.weighing_datetime - previous.weighing_datetime).days
            if interval <= 0:
                continue
            rec.previous_weight = previous.weight
            rec.weight_gain = rec.weight - previous.weight
            rec.days_interval = interval
            rec.average_daily_gain = rec.weight_gain / interval

    def _recompute_following_growth(self):
        """Recalcule le GMQ des pesées postérieures du même animal."""
        for rec in self:
            if rec.weighing_mode != "individual" or not rec.animal_id or not rec.weighing_datetime:
                continue
            following = self.search([
                ("animal_id", "=", rec.animal_id.id),
                ("weighing_mode", "=", "individual"),
                ("weighing_datetime", ">", rec.weighing_datetime),
            ])
            for field_name in ("previous_weight", "weight_gain", "days_interval", "average_daily_gain"):
                self.env.add_to_compute(self._fields[field_name], following)

    @api.constrains("animal_id", "lot_id")
    def _check_target(self):
        for rec in self:
            if bool(rec.animal_id) == bool(rec.lot_id):
                raise ValidationError(self.env._("Une pesée doit concerner soit un animal, soit un lot."))

    @api.constrains("weighing_mode", "animal_id", "lot_id")
    def _check_mode_target(self):
        for rec in self:
            if rec.weighing_mode == "individual" and not rec.animal_id:
                raise ValidationError(self.env._("Une pesée individuelle doit concerner un animal."))
            if rec.weighing_mode == "collective" and not rec.lot_id:
                raise ValidationError(self.env._("Une pesée collective doit concerner un lot."))

    @api.constrains("weighing_mode", "weight", "average_weight")
    def _check_weights(self):
        for rec in self:
            if rec.weighing_mode == "individual":
                if rec.weight <= 0:
                    raise ValidationError(self.env._("Le poids mesuré doit être strictement positif."))
                if rec.average_weight:
                    raise ValidationError(self.env._("Un poids moyen ne peut être saisi qu'en mode collectif."))
            else:
                if rec.average_weight <= 0:
                    raise ValidationError(self.env._("Le poids moyen du lot doit être strictement positif."))
                if rec.weight:
                    raise ValidationError(self.env._("Un poids individuel ne peut être saisi qu'en mode individuel."))

    @api.constrains("animal_count", "weighing_mode")
    def _check_animal_count(self):
        for rec in self:
            if rec.animal_count < 0:
                raise ValidationError(self.env._("Le nombre d'animaux pesés ne peut pas être négatif."))
            if rec.weighing_mode == "collective" and rec.animal_count < 1:
                raise ValidationError(self.env._("Une pesée collective doit indiquer le nombre d'animaux pesés."))

    @api.constrains("animal_id", "farm_id", "weighing_datetime")
    def _check_animal(self):
        for rec in self:
            if not rec.animal_id:
                continue
            if rec.animal_id.farm_id != rec.farm_id:
                raise ValidationError(self.env._("L'animal n'appartient pas à l'exploitation."))
            date = rec.weighing_datetime.date() if rec.weighing_datetime else False
            if date and rec.animal_id.birth_date and date < rec.animal_id.birth_date:
                raise ValidationError(self.env._("La date de pesée ne peut pas précéder la naissance de l'animal."))
            death_date = rec.animal_id.death_date
            if death_date and date and date > death_date:
                raise ValidationError(self.env._(
                    "La pesée ne peut pas être postérieure au décès de l'animal (« %s »).",
                    rec.animal_id.display_name,
                ))

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

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_animal_weight_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_animal_weight_state_transition=True).write({"state": target})

    def action_validate(self):
        self._check_allowed({"draft"})
        self._apply_state("validated")
        self._recompute_following_growth()

    def action_cancel(self):
        self._check_allowed({"draft", "validated"})
        self._apply_state("cancelled")
        self._recompute_following_growth()

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "validated": "Validée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._(
                    "Transition impossible : la pesée « %(r)s » est à l'état « %(s)s ».",
                    r=rec.display_name, s=labels.get(rec.state, rec.state),
                ))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La pesée « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()
