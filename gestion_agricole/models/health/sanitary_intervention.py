# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriSanitaryIntervention(models.Model):
    _name = "gest_agri.sanitary.intervention"
    _description = "Intervention sanitaire"
    _inherit = ["mail.thread"]
    _order = "intervention_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot concerné", required=True, ondelete="restrict", index=True)
    farm_id = fields.Many2one(related="lot_id.farm_id", string="Exploitation", store=True, readonly=True, precompute=True, index=True)
    company_id = fields.Many2one(related="farm_id.company_id", string="Société", store=True, readonly=True, precompute=True, index=True)

    intervention_type = fields.Selection(
        selection=[("vaccination", "Vaccination"), ("treatment", "Traitement"), ("control", "Contrôle"),
                   ("inspection", "Inspection"), ("other", "Autre")],
        string="Type d'intervention", required=True, default="control",
    )
    intervention_date = fields.Date(string="Date de l'intervention", required=True, index=True)
    animal_count = fields.Integer(string="Nombre d'animaux concernés", default=0)
    veterinarian_id = fields.Many2one("res.partner", string="Vétérinaire / responsable", ondelete="set null")
    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    products_used = fields.Text(string="Produits utilisés")
    result = fields.Text(string="Résultats constatés")
    notes = fields.Text(string="Observations")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("done", "Terminée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.sanitary.intervention")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.sanitary.intervention » est introuvable."))
                vals["name"] = ref
            if vals.get("animal_count", 0) < 0:
                raise ValidationError(self.env._("Le nombre d'animaux ne peut pas être négatif."))
        return super().create(vals_list)

    @api.constrains("animal_count")
    def _check_animal_count(self):
        for rec in self:
            if rec.animal_count < 0:
                raise ValidationError(self.env._("Le nombre d'animaux ne peut pas être négatif."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_sanitary_intervention_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_sanitary_intervention_state_transition=True).write({"state": target})

    def action_done(self):
        self._check_allowed({"draft"})
        self._apply_state("done")

    def action_cancel(self):
        self._check_allowed({"draft", "done"})
        self._apply_state("cancelled")

    def _check_allowed(self, allowed):
        labels = {"draft": "Brouillon", "done": "Terminée", "cancelled": "Annulée"}
        for rec in self:
            if rec.state not in allowed:
                raise UserError(self.env._("Transition impossible : l'intervention « %(i)s » est à l'état « %(s)s ».", i=rec.display_name, s=labels.get(rec.state, rec.state)))

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("L'intervention « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()
