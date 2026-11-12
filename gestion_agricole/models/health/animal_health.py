# -*- coding: utf-8 -*-
from odoo import api, fields, models


class GestAgriAnimalHealthHistory(models.Model):
    """Extension de l'animal : historique sanitaire et échéances."""

    _inherit = "gest_agri.animal"

    health_record_ids = fields.One2many("gest_agri.animal.health", "animal_id", string="Dossiers sanitaires")
    health_record_count = fields.Integer(string="Nb dossiers sanitaires", compute="_compute_health_counts")
    consultation_ids = fields.One2many("gest_agri.veterinary.consultation", "animal_id", string="Consultations")
    consultation_count = fields.Integer(string="Nb consultations", compute="_compute_health_counts")
    vaccination_ids = fields.One2many("gest_agri.vaccination", "animal_id", string="Vaccinations")
    vaccination_count = fields.Integer(string="Nb vaccinations", compute="_compute_health_counts")
    treatment_ids = fields.One2many("gest_agri.animal.treatment", "animal_id", string="Traitements")
    treatment_count = fields.Integer(string="Nb traitements", compute="_compute_health_counts")

    next_vaccination_due_date = fields.Date(string="Prochain rappel vaccinal", compute="_compute_next_deadlines")
    next_control_date = fields.Date(string="Prochain contrôle vétérinaire", compute="_compute_next_deadlines")
    has_overdue_sanitary_deadline = fields.Boolean(
        string="Échéance sanitaire dépassée", compute="_compute_next_deadlines",
    )

    @api.depends("health_record_ids", "consultation_ids", "vaccination_ids", "treatment_ids")
    def _compute_health_counts(self):
        for animal in self:
            animal.health_record_count = len(animal.health_record_ids)
            animal.consultation_count = len(animal.consultation_ids)
            animal.vaccination_count = len(animal.vaccination_ids)
            animal.treatment_count = len(animal.treatment_ids)

    @api.depends(
        "vaccination_ids.next_due_date", "vaccination_ids.state",
        "consultation_ids.next_control_date", "consultation_ids.state",
    )
    def _compute_next_deadlines(self):
        today = fields.Date.today()
        for animal in self:
            due_dates = animal.vaccination_ids.filtered(
                lambda v: v.state == "done" and v.next_due_date
            ).mapped("next_due_date")
            control_dates = animal.consultation_ids.filtered(
                lambda c: c.state == "done" and c.next_control_date
            ).mapped("next_control_date")
            all_dates = due_dates + control_dates
            animal.next_vaccination_due_date = min(due_dates) if due_dates else False
            animal.next_control_date = min(control_dates) if control_dates else False
            animal.has_overdue_sanitary_deadline = bool(all_dates) and min(all_dates) < today

    def action_view_health_records(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Dossiers sanitaires",
            "res_model": "gest_agri.animal.health",
            "view_mode": "list,form",
            "domain": [("animal_id", "=", self.id)],
            "context": {"default_animal_id": self.id},
        }

    def action_view_consultations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Consultations vétérinaires",
            "res_model": "gest_agri.veterinary.consultation",
            "view_mode": "list,form",
            "domain": [("animal_id", "=", self.id)],
            "context": {"default_animal_id": self.id},
        }

    def action_view_vaccinations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Vaccinations",
            "res_model": "gest_agri.vaccination",
            "view_mode": "list,form",
            "domain": [("animal_id", "=", self.id)],
            "context": {"default_animal_id": self.id},
        }

    def action_view_treatments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Traitements",
            "res_model": "gest_agri.animal.treatment",
            "view_mode": "list,form",
            "domain": [("animal_id", "=", self.id)],
            "context": {"default_animal_id": self.id},
        }


class GestAgriAnimalLotHealthHistory(models.Model):
    """Extension du lot : historique sanitaire."""

    _inherit = "gest_agri.animal.lot"

    consultation_ids = fields.One2many("gest_agri.veterinary.consultation", "lot_id", string="Consultations")
    consultation_count = fields.Integer(string="Nb consultations", compute="_compute_lot_health_counts")
    vaccination_ids = fields.One2many("gest_agri.vaccination", "lot_id", string="Vaccinations")
    vaccination_count = fields.Integer(string="Nb vaccinations", compute="_compute_lot_health_counts")
    treatment_ids = fields.One2many("gest_agri.animal.treatment", "lot_id", string="Traitements")
    treatment_count = fields.Integer(string="Nb traitements", compute="_compute_lot_health_counts")
    sanitary_intervention_ids = fields.One2many("gest_agri.sanitary.intervention", "lot_id", string="Interventions sanitaires")
    sanitary_intervention_count = fields.Integer(string="Nb interventions", compute="_compute_lot_health_counts")

    @api.depends("consultation_ids", "vaccination_ids", "treatment_ids", "sanitary_intervention_ids")
    def _compute_lot_health_counts(self):
        for lot in self:
            lot.consultation_count = len(lot.consultation_ids)
            lot.vaccination_count = len(lot.vaccination_ids)
            lot.treatment_count = len(lot.treatment_ids)
            lot.sanitary_intervention_count = len(lot.sanitary_intervention_ids)

    def action_view_sanitary_interventions(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Interventions sanitaires",
            "res_model": "gest_agri.sanitary.intervention",
            "view_mode": "list,form",
            "domain": [("lot_id", "=", self.id)],
            "context": {"default_lot_id": self.id},
        }
