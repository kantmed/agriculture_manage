# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GestAgriAnimalProductionHistory(models.Model):
    """Extension de l'animal : engraissement et historique de production."""

    _inherit = "gest_agri.animal"

    # ------------------------------------------------------------------
    # Engraissement / production de viande
    # ------------------------------------------------------------------
    meat_destined = fields.Boolean(
        string="Destiné à la production de viande",
        help="Marque l'animal comme destiné à l'engraissement / à la production de viande.",
    )
    fattening_start_date = fields.Date(string="Date d'entrée en engraissement")
    fattening_end_date = fields.Date(string="Date de sortie d'engraissement")
    fattening_lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot d'engraissement", ondelete="set null")
    fattening_responsible_id = fields.Many2one("res.users", string="Responsable de l'engraissement", ondelete="set null")
    fattening_notes = fields.Text(string="Observations d'engraissement")

    # ------------------------------------------------------------------
    # Historique de production
    # ------------------------------------------------------------------
    milk_production_ids = fields.One2many("gest_agri.milk.production", "animal_id", string="Productions laitières")
    milk_production_count = fields.Integer(string="Nb productions laitières", compute="_compute_production_indicators", store=True)
    milk_total_quantity = fields.Float(string="Lait produit", compute="_compute_production_indicators", store=True, digits=(16, 3))

    weight_ids = fields.One2many("gest_agri.animal.weight", "animal_id", string="Pesées")
    weight_count = fields.Integer(string="Nb pesées", compute="_compute_production_indicators", store=True)
    last_weight = fields.Float(string="Dernier poids", compute="_compute_production_indicators", store=True, digits=(16, 3))
    last_weight_date = fields.Date(string="Date du dernier poids", compute="_compute_production_indicators", store=True)

    meat_production_ids = fields.One2many("gest_agri.meat.production", "animal_id", string="Productions de viande")
    meat_production_count = fields.Integer(string="Nb productions de viande", compute="_compute_production_indicators", store=True)
    meat_carcass_total = fields.Float(string="Carcasse totale", compute="_compute_production_indicators", store=True, digits=(16, 3))

    @api.depends(
        "milk_production_ids.state", "milk_production_ids.quantity",
        "weight_ids.state", "weight_ids.weight", "weight_ids.weighing_mode",
        "weight_ids.weighing_datetime",
        "meat_production_ids.state", "meat_production_ids.carcass_weight",
    )
    def _compute_production_indicators(self):
        for animal in self:
            milk = animal.milk_production_ids.filtered(lambda m: m.state == "validated")
            animal.milk_production_count = len(milk)
            animal.milk_total_quantity = sum(milk.mapped("quantity"))

            weights = animal.weight_ids.filtered(
                lambda w: w.state == "validated" and w.weighing_mode == "individual"
            )
            animal.weight_count = len(weights)
            last = weights.sorted("weighing_datetime")[-1:] if weights else weights
            animal.last_weight = last.weight if last else 0.0
            animal.last_weight_date = last.weighing_datetime.date() if last and last.weighing_datetime else False

            meat = animal.meat_production_ids.filtered(lambda m: m.state == "validated")
            animal.meat_production_count = len(meat)
            animal.meat_carcass_total = sum(meat.mapped("carcass_weight"))

    @api.constrains("fattening_start_date", "fattening_end_date")
    def _check_fattening_dates(self):
        for animal in self:
            if animal.fattening_start_date and animal.fattening_end_date and animal.fattening_end_date < animal.fattening_start_date:
                raise ValidationError(self.env._("La date de sortie d'engraissement ne peut pas précéder l'entrée."))

    @api.constrains("fattening_lot_id", "farm_id")
    def _check_fattening_lot(self):
        for animal in self:
            if animal.fattening_lot_id and animal.fattening_lot_id.farm_id != animal.farm_id:
                raise ValidationError(self.env._("Le lot d'engraissement n'appartient pas à l'exploitation."))

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_view_milk_productions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Productions laitières",
            "res_model": "gest_agri.milk.production",
            "view_mode": "list,form",
            "domain": [("animal_id", "=", self.id)],
            "context": {"default_animal_id": self.id, "default_farm_id": self.farm_id.id},
        }

    def action_view_weights(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Pesées",
            "res_model": "gest_agri.animal.weight",
            "view_mode": "list,form",
            "domain": [("animal_id", "=", self.id)],
            "context": {"default_animal_id": self.id, "default_weighing_mode": "individual"},
        }

    def action_view_meat_productions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Productions de viande",
            "res_model": "gest_agri.meat.production",
            "view_mode": "list,form",
            "domain": [("animal_id", "=", self.id)],
            "context": {"default_animal_id": self.id},
        }


class GestAgriAnimalLotProductionHistory(models.Model):
    """Extension du lot : historique de production et indicateurs."""

    _inherit = "gest_agri.animal.lot"

    milk_production_ids = fields.One2many("gest_agri.milk.production", "lot_id", string="Productions laitières")
    milk_production_count = fields.Integer(string="Nb productions laitières", compute="_compute_production_indicators", store=True)
    milk_total_quantity = fields.Float(string="Lait collecté", compute="_compute_production_indicators", store=True, digits=(16, 3))

    egg_production_ids = fields.One2many("gest_agri.egg.production", "lot_id", string="Collectes d'œufs")
    egg_production_count = fields.Integer(string="Nb collectes d'œufs", compute="_compute_production_indicators", store=True)
    egg_total_count = fields.Integer(string="Œufs collectés", compute="_compute_production_indicators", store=True)

    weight_ids = fields.One2many("gest_agri.animal.weight", "lot_id", string="Pesées collectives")
    weight_count = fields.Integer(string="Nb pesées", compute="_compute_production_indicators", store=True)

    meat_production_ids = fields.One2many("gest_agri.meat.production", "lot_id", string="Productions de viande")
    meat_production_count = fields.Integer(string="Nb productions de viande", compute="_compute_production_indicators", store=True)

    @api.depends(
        "milk_production_ids.state", "milk_production_ids.quantity",
        "egg_production_ids.state", "egg_production_ids.egg_count",
        "weight_ids.state",
        "meat_production_ids.state",
    )
    def _compute_production_indicators(self):
        for lot in self:
            milk = lot.milk_production_ids.filtered(lambda m: m.state == "validated")
            lot.milk_production_count = len(milk)
            lot.milk_total_quantity = sum(milk.mapped("quantity"))

            eggs = lot.egg_production_ids.filtered(lambda e: e.state == "validated")
            lot.egg_production_count = len(eggs)
            lot.egg_total_count = sum(eggs.mapped("egg_count"))

            lot.weight_count = len(lot.weight_ids.filtered(lambda w: w.state == "validated"))
            lot.meat_production_count = len(lot.meat_production_ids.filtered(lambda m: m.state == "validated"))

    def action_view_milk_productions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Productions laitières",
            "res_model": "gest_agri.milk.production",
            "view_mode": "list,form",
            "domain": [("lot_id", "=", self.id)],
            "context": {"default_lot_id": self.id, "default_farm_id": self.farm_id.id},
        }

    def action_view_egg_productions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Collectes d'œufs",
            "res_model": "gest_agri.egg.production",
            "view_mode": "list,form",
            "domain": [("lot_id", "=", self.id)],
            "context": {"default_lot_id": self.id},
        }

    def action_view_weights(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Pesées",
            "res_model": "gest_agri.animal.weight",
            "view_mode": "list,form",
            "domain": [("lot_id", "=", self.id)],
            "context": {"default_lot_id": self.id, "default_weighing_mode": "collective"},
        }

    def action_view_meat_productions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Productions de viande",
            "res_model": "gest_agri.meat.production",
            "view_mode": "list,form",
            "domain": [("lot_id", "=", self.id)],
            "context": {"default_lot_id": self.id},
        }
