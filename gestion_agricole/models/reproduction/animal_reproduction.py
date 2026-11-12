# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GestAgriAnimalReproductionHistory(models.Model):
    """Extension de l'animal : filiation, historique reproductif et mortalité."""

    _inherit = "gest_agri.animal"

    mother_id = fields.Many2one("gest_agri.animal", string="Mère", ondelete="set null", index=True)
    father_id = fields.Many2one("gest_agri.animal", string="Père", ondelete="set null", index=True)
    birth_id = fields.Many2one("gest_agri.animal.birth", string="Mise bas d'origine", ondelete="set null", index=True)

    reproduction_ids = fields.One2many(
        "gest_agri.animal.reproduction", "female_id", string="Événements reproductifs",
    )
    reproduction_count = fields.Integer(string="Nb événements reproductifs", compute="_compute_reproduction_indicators", store=True)
    gestation_ids = fields.One2many(
        "gest_agri.animal.gestation", "female_id", string="Gestations",
    )
    gestation_count = fields.Integer(string="Nb gestations", compute="_compute_reproduction_indicators", store=True)
    gestation_terminated_count = fields.Integer(string="Gestations terminées", compute="_compute_reproduction_indicators", store=True)
    gestation_failed_count = fields.Integer(string="Gestations avortées/interrompues", compute="_compute_reproduction_indicators", store=True)
    birth_ids = fields.One2many(
        "gest_agri.animal.birth", "mother_id", string="Mises bas",
    )
    birth_count = fields.Integer(string="Nb mises bas", compute="_compute_reproduction_indicators", store=True)
    alive_newborn_count = fields.Integer(string="Petits nés vivants", compute="_compute_reproduction_indicators", store=True)
    stillborn_count = fields.Integer(string="Mort-nés", compute="_compute_reproduction_indicators", store=True)
    last_birth_date = fields.Date(string="Dernière mise bas", compute="_compute_reproduction_indicators", store=True)
    next_expected_birth_date = fields.Date(string="Prochaine mise bas prévue", compute="_compute_reproduction_indicators", store=True)

    mortality_ids = fields.One2many(
        "gest_agri.animal.mortality", "animal_id", string="Mortalités",
    )
    mortality_count = fields.Integer(string="Nb mortalités", compute="_compute_mortality_indicators", store=True)
    death_date = fields.Date(string="Date de décès", compute="_compute_mortality_indicators", store=True)
    is_dead = fields.Boolean(string="Décédé", compute="_compute_mortality_indicators", store=True)

    @api.depends(
        "reproduction_ids.state", "gestation_ids.state", "birth_ids.state",
        "birth_ids.alive_count", "birth_ids.stillborn_count", "birth_ids.birth_datetime",
        "gestation_ids.expected_birth_date",
    )
    def _compute_reproduction_indicators(self):
        for animal in self:
            reproductions = animal.reproduction_ids.filtered(lambda r: r.state != "cancelled")
            animal.reproduction_count = len(reproductions)
            animal.gestation_count = len(animal.gestation_ids)
            animal.gestation_terminated_count = len(animal.gestation_ids.filtered(lambda g: g.state == "terminated"))
            animal.gestation_failed_count = len(animal.gestation_ids.filtered(lambda g: g.state in ("aborted", "interrupted")))
            births = animal.birth_ids.filtered(lambda b: b.state != "cancelled")
            animal.birth_count = len(births)
            animal.alive_newborn_count = sum(births.mapped("alive_count"))
            animal.stillborn_count = sum(births.mapped("stillborn_count"))
            birth_dates = births.mapped("birth_datetime")
            animal.last_birth_date = max(birth_dates).date() if birth_dates else False
            upcoming = animal.gestation_ids.filtered(
                lambda g: g.state in ("to_confirm", "confirmed") and g.expected_birth_date
            ).mapped("expected_birth_date")
            animal.next_expected_birth_date = min(upcoming) if upcoming else False

    @api.depends("mortality_ids.state", "mortality_ids.death_datetime", "state")
    def _compute_mortality_indicators(self):
        for animal in self:
            validated = animal.mortality_ids.filtered(lambda m: m.state == "validated")
            animal.mortality_count = len(validated)
            animal.death_date = max(validated.mapped("death_datetime")).date() if validated else False
            animal.is_dead = animal.state == "dead"

    @api.constrains("mother_id", "father_id")
    def _check_parents(self):
        for animal in self:
            if animal.mother_id and animal.mother_id.sex != "female":
                raise ValidationError(self.env._("La mère doit être de sexe féminin."))
            if animal.father_id and animal.father_id.sex != "male":
                raise ValidationError(self.env._("Le père doit être de sexe masculin."))
            if animal.mother_id and animal.mother_id.species_id != animal.species_id:
                raise ValidationError(self.env._("La mère et l'animal doivent appartenir à la même espèce."))
            if animal.father_id and animal.father_id.species_id != animal.species_id:
                raise ValidationError(self.env._("Le père et l'animal doivent appartenir à la même espèce."))

    def action_view_reproduction(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Événements reproductifs",
            "res_model": "gest_agri.animal.reproduction",
            "view_mode": "list,form",
            "domain": [("female_id", "=", self.id)],
            "context": {"default_female_id": self.id},
        }

    def action_view_gestations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Gestations",
            "res_model": "gest_agri.animal.gestation",
            "view_mode": "list,form",
            "domain": [("female_id", "=", self.id)],
            "context": {"default_female_id": self.id},
        }

    def action_view_births(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Mises bas",
            "res_model": "gest_agri.animal.birth",
            "view_mode": "list,form",
            "domain": [("mother_id", "=", self.id)],
            "context": {"default_gestation_id": False},
        }

    def action_view_mortalities(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Mortalités",
            "res_model": "gest_agri.animal.mortality",
            "view_mode": "list,form",
            "domain": [("animal_id", "=", self.id)],
            "context": {"default_animal_id": self.id},
        }


class GestAgriAnimalLotReproductionHistory(models.Model):
    _inherit = "gest_agri.animal.lot"

    mortality_ids = fields.One2many("gest_agri.animal.mortality", "lot_id", string="Mortalités")
    mortality_count = fields.Integer(string="Nb mortalités", compute="_compute_lot_mortality_count")

    @api.depends("mortality_ids.state")
    def _compute_lot_mortality_count(self):
        for lot in self:
            lot.mortality_count = len(lot.mortality_ids.filtered(lambda m: m.state == "validated"))

    def action_view_mortalities(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Mortalités du lot",
            "res_model": "gest_agri.animal.mortality",
            "view_mode": "list,form",
            "domain": [("lot_id", "=", self.id)],
            "context": {"default_lot_id": self.id},
        }
