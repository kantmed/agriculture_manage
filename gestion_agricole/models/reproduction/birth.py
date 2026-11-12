# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class GestAgriAnimalBirth(models.Model):
    _name = "gest_agri.animal.birth"
    _description = "Mise bas et naissance"
    _inherit = ["mail.thread"]
    _order = "birth_datetime desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="Référence", required=True, copy=False, index=True, readonly=True)
    active = fields.Boolean(string="Actif", default=True)

    gestation_id = fields.Many2one(
        "gest_agri.animal.gestation", string="Gestation associée", required=True,
        ondelete="restrict", index=True,
    )
    mother_id = fields.Many2one(
        "gest_agri.animal", string="Mère", related="gestation_id.female_id",
        store=True, readonly=True, index=True,
    )
    father_id = fields.Many2one("gest_agri.animal", string="Père", ondelete="set null", index=True)
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", related="gestation_id.farm_id",
        store=True, readonly=True, precompute=True, index=True,
    )
    company_id = fields.Many2one(
        related="farm_id.company_id", string="Société", store=True, readonly=True,
        precompute=True, index=True,
    )
    site_id = fields.Many2one("gest_agri.site", string="Site", ondelete="set null", index=True)

    birth_datetime = fields.Datetime(string="Date et heure de mise bas", required=True, default=fields.Datetime.now)
    birth_type = fields.Selection(
        selection=[
            ("normal", "Normale"),
            ("assisted", "Assistée"),
            ("difficult", "Difficile"),
            ("cesarean", "Césarienne"),
            ("other", "Autre"),
        ],
        string="Type de mise bas", required=True, default="normal",
    )
    total_count = fields.Integer(string="Nombre total de petits", default=0)
    alive_count = fields.Integer(string="Petits vivants", default=0)
    stillborn_count = fields.Integer(string="Mort-nés", default=0)

    responsible_id = fields.Many2one("res.users", string="Responsable", ondelete="set null")
    veterinarian_id = fields.Many2one("res.partner", string="Vétérinaire", ondelete="set null")
    notes = fields.Text(string="Observations")

    newborn_ids = fields.One2many("gest_agri.animal.birth.newborn", "birth_id", string="Nouveau-nés")
    newborn_count = fields.Integer(string="Nb lignes nouveau-nés", compute="_compute_newborn_count")

    state = fields.Selection(
        selection=[("draft", "Brouillon"), ("validated", "Validée"), ("cancelled", "Annulée")],
        string="État", default="draft", required=True, index=True, tracking=True, copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                ref = self.env["ir.sequence"].next_by_code("gest_agri.animal.birth")
                if not ref:
                    raise UserError(self.env._("La séquence « gest_agri.animal.birth » est introuvable."))
                vals["name"] = ref
            if not vals.get("father_id") and vals.get("gestation_id"):
                gestation = self.env["gest_agri.animal.gestation"].browse(vals["gestation_id"])
                if gestation.male_id:
                    vals["father_id"] = gestation.male_id.id
        return super().create(vals_list)

    @api.depends("newborn_ids")
    def _compute_newborn_count(self):
        for rec in self:
            rec.newborn_count = len(rec.newborn_ids)

    @api.constrains("total_count", "alive_count", "stillborn_count")
    def _check_counts(self):
        for rec in self:
            if min(rec.total_count, rec.alive_count, rec.stillborn_count) < 0:
                raise ValidationError(self.env._("Les nombres de petits ne peuvent pas être négatifs."))
            if rec.alive_count + rec.stillborn_count != rec.total_count:
                raise ValidationError(self.env._(
                    "Le nombre total de petits doit être égal à la somme des vivants et des mort-nés."
                ))

    @api.constrains("mother_id", "father_id")
    def _check_parents(self):
        for rec in self:
            if rec.father_id and rec.father_id.sex != "male":
                raise ValidationError(self.env._("Le père doit être de sexe masculin."))
            if rec.father_id and rec.mother_id and rec.father_id.species_id != rec.mother_id.species_id:
                raise ValidationError(self.env._("Le père et la mère doivent appartenir à la même espèce."))

    @api.constrains("birth_datetime", "gestation_id")
    def _check_dates(self):
        for rec in self:
            if rec.gestation_id.start_date and rec.birth_datetime and rec.birth_datetime.date() < rec.gestation_id.start_date:
                raise ValidationError(self.env._("La date de mise bas ne peut pas précéder le début de la gestation."))

    # Workflow
    def write(self, vals):
        if "state" in vals and not self.env.context.get("gest_agri_birth_state_transition"):
            for rec in self:
                if rec.state != vals["state"]:
                    raise AccessError(self.env._("Le statut ne peut être modifié qu'à travers les actions métier."))
        return super().write(vals)

    def _apply_state(self, target):
        self.with_context(gest_agri_birth_state_transition=True).write({"state": target})

    def action_validate(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("Seule une mise bas en brouillon peut être validée."))
            if rec.gestation_id.state not in ("confirmed", "terminated"):
                raise UserError(self.env._(
                    "La gestation associée à la mise bas « %s » doit être confirmée (ou déjà terminée) "
                    "avant de pouvoir valider la mise bas.",
                    rec.display_name,
                ))
            rec._check_counts()
        self._apply_state("validated")
        for rec in self:
            if rec.gestation_id.state == "confirmed":
                rec.gestation_id.action_terminate()

    def action_cancel(self):
        for rec in self:
            if rec.state == "cancelled":
                raise UserError(self.env._("La mise bas est déjà annulée."))
            if rec.state == "validated":
                # Les effets d'une mise bas validée (clôture de gestation, animaux
                # nouveau-nés, filiation) ne sont pas réversibles sans risque
                # d'incohérence : l'annulation est interdite.
                raise UserError(self.env._(
                    "La mise bas « %s » est validée : son annulation est interdite car elle a clôturé "
                    "la gestation et peut avoir créé des animaux. Utilisez une procédure corrective traçable.",
                    rec.display_name,
                ))
        self._apply_state("cancelled")

    def action_create_newborn_animals(self):
        self.ensure_one()
        if self.state != "validated":
            raise UserError(self.env._(
                "La mise bas doit être validée avant de créer les animaux nouveau-nés."
            ))
        lines = self.newborn_ids.filtered(lambda line: not line.animal_id)
        # Pré-validation atomique : on valide toutes les lignes avant toute création,
        # afin de ne jamais laisser une création partielle incohérente.
        for line in lines:
            if not line.sex:
                raise UserError(self.env._(
                    "Le sexe doit être renseigné pour créer l'animal « %s ».", line.name or "?"
                ))
        if len(lines) > self.alive_count:
            raise UserError(self.env._(
                "Le nombre de nouveau-nés à créer (%(n)s) dépasse le nombre de petits vivants déclarés (%(a)s).",
                n=len(lines), a=self.alive_count,
            ))
        Animal = self.env["gest_agri.animal"]
        created = Animal
        for line in lines:
            animal = Animal.create({
                "name": line.name or False,
                "species_id": self.mother_id.species_id.id,
                "breed_id": line.breed_id.id or self.mother_id.breed_id.id,
                "sex": line.sex,
                "birth_date": self.birth_datetime.date(),
                "farm_id": self.farm_id.id,
                "site_id": self.site_id.id,
                "lot_id": line.lot_id.id,
                "mother_id": self.mother_id.id,
                "father_id": self.father_id.id,
                "birth_id": self.id,
                "origin": self.env._("Né de la mise bas %s", self.name),
            })
            line.animal_id = animal.id
            created |= animal
        return {
            "type": "ir.actions.act_window",
            "name": "Nouveaux animaux",
            "res_model": "gest_agri.animal",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(self.env._("La mise bas « %s » ne peut être supprimée qu'en brouillon.", rec.display_name))
        return super().unlink()


class GestAgriAnimalBirthNewborn(models.Model):
    _name = "gest_agri.animal.birth.newborn"
    _description = "Nouveau-né d'une mise bas"
    _order = "id"
    _check_company_auto = True

    birth_id = fields.Many2one(
        "gest_agri.animal.birth", string="Mise bas", required=True, ondelete="cascade", index=True,
    )
    farm_id = fields.Many2one(
        "gest_agri.farm", string="Exploitation", related="birth_id.farm_id",
        store=True, readonly=True, index=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Société", related="birth_id.company_id", store=True, readonly=True, index=True,
    )
    animal_id = fields.Many2one(
        "gest_agri.animal", string="Animal enregistré", ondelete="set null", index=True,
    )
    name = fields.Char(string="Identification / désignation")
    sex = fields.Selection(selection=[("male", "Mâle"), ("female", "Femelle")], string="Sexe")
    breed_id = fields.Many2one("gest_agri.livestock.breed", string="Race", ondelete="set null")
    lot_id = fields.Many2one("gest_agri.animal.lot", string="Lot", ondelete="set null")
    notes = fields.Text(string="Observations")

    @api.constrains("animal_id", "birth_id")
    def _check_animal_scope(self):
        for line in self:
            if line.animal_id and line.birth_id.farm_id and line.animal_id.farm_id != line.birth_id.farm_id:
                raise ValidationError(self.env._("L'animal associé n'appartient pas à l'exploitation de la mise bas."))
